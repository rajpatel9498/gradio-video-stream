import gradio as gr
import numpy as np
import logging
import threading
import time
import os
import sys
from dataclasses import dataclass
from typing import Optional, Tuple
import mmap
import struct
from contextlib import contextmanager
import cv2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class VideoConfig:
    """Configuration for video streaming"""
    width: int = 640
    height: int = 480
    fps: int = 30
    format: str = "RGB"
    socket_path: str = "/tmp/shared_memory/video_stream"
    meta_path: str = "/tmp/shared_memory/video_stream.meta"

class SharedMemoryManager:
    """Manages shared memory operations for video streaming"""
    
    def __init__(self, config: VideoConfig):
        self.config = config
        self._shm_name = f"shmpipe.{os.path.basename(config.socket_path)}"
        self._shm = None
        self._mmap = None
        self._max_retries = 30
        self._retry_delay = 0.5
        self.frame_size = self.config.height * self.config.width * 3
        
    def _find_shm_file(self):
        """Find the actual shared memory file name"""
        try:
            # List all files in /dev/shm that start with 'shmpipe.'
            shm_files = [f for f in os.listdir('/dev/shm') if f.startswith('shmpipe.')]
            if not shm_files:
                return None
                
            # If we find multiple files, try to match by the socket path
            socket_name = os.path.basename(self.config.socket_path)
            for shm_file in shm_files:
                if socket_name in shm_file:
                    return shm_file
                    
            # If no exact match, use the most recently created file
            return max(shm_files, key=lambda x: os.path.getctime(os.path.join('/dev/shm', x)))
        except Exception as e:
            logger.error(f"Error finding shared memory file: {e}")
            return None
            
    @contextmanager
    def connect(self):
        """Context manager for shared memory connection"""
        try:
            self._connect()
            yield self
        finally:
            self.disconnect()
            
    def _connect(self):
        """Establish connection to shared memory"""
        retry_count = 0
        last_error = None
        
        while retry_count < self._max_retries:
            try:
                # First check if the socket file exists
                if not os.path.exists(self.config.socket_path):
                    logger.info(f"Waiting for socket file at {self.config.socket_path}... (attempt {retry_count + 1}/{self._max_retries})")
                    time.sleep(self._retry_delay)
                    retry_count += 1
                    continue
                
                # Try to find the actual shared memory file
                shm_file = self._find_shm_file()
                if not shm_file:
                    logger.info(f"Waiting for shared memory file... (attempt {retry_count + 1}/{self._max_retries})")
                    time.sleep(self._retry_delay)
                    retry_count += 1
                    continue
                
                # Try to connect to shared memory
                shm_path = os.path.join('/dev/shm', shm_file)
                logger.info(f"Attempting to connect to shared memory at {shm_path}")
                
                # Try to open the shared memory file
                fd = os.open(shm_path, os.O_RDWR)
                self._mmap = mmap.mmap(fd, 0, mmap.MAP_SHARED, mmap.PROT_READ)
                os.close(fd)
                
                logger.info(f"Successfully connected to shared memory: {shm_file} ({self.config.width}x{self.config.height})")
                return
                
            except FileNotFoundError as e:
                last_error = e
                logger.info(f"Shared memory not found yet, retrying... (attempt {retry_count + 1}/{self._max_retries})")
                time.sleep(self._retry_delay)
                retry_count += 1
            except Exception as e:
                last_error = e
                logger.error(f"Error connecting to shared memory: {e}")
                self.disconnect()
                raise
        
        # If we get here, we've exhausted all retries
        error_msg = f"Failed to connect to shared memory after {self._max_retries} attempts"
        if last_error:
            error_msg += f": {last_error}"
        logger.error(error_msg)
        raise TimeoutError(error_msg)
            
    def disconnect(self):
        """Clean up shared memory resources"""
        if self._mmap:
            try:
                self._mmap.close()
            except Exception as e:
                logger.warning(f"Error closing memory map: {e}")
            finally:
                self._mmap = None
                
    def read_frame(self) -> Optional[np.ndarray]:
        """Read a frame from shared memory"""
        if not self._mmap:
            return None
        try:
            # Skip metadata and read frame data
            frame_data = self._mmap[:self.frame_size]
            print("Frame buffer length:", len(frame_data))
            print("Expected:", self.config.height * self.config.width * 3)
            # Save the first frame for inspection
            if not hasattr(self, '_frame_saved'):
                with open("debug_frame.raw", "wb") as f:
                    f.write(frame_data)
                print("Saved first raw frame to debug_frame.raw")
                self._frame_saved = True
            # Convert to numpy array
            frame = np.ndarray(
                shape=(self.config.height, self.config.width, 3),
                dtype=np.uint8,
                buffer=frame_data
            ).copy()  # Make a copy to ensure we own the memory
            return frame
        except Exception as e:
            logger.error(f"Error reading frame: {e}")
            return None

def read_metadata_from_file(meta_path):
    with open(meta_path, 'rb') as f:
        return struct.unpack('III', f.read(12))

class VideoStreamer:
    """Handles video streaming from shared memory"""
    
    def __init__(self, config: VideoConfig):
        self.config = config
        self.shm_manager = SharedMemoryManager(config)
        self._running = False
        self._current_frame = None
        self._frame_lock = threading.Lock()
        self._thread = None
        
    def start(self):
        """Start the video streamer"""
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._thread.start()
        
    def stop(self):
        """Stop the video streamer"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self.shm_manager.disconnect()
        
    def _stream_loop(self):
        """Main streaming loop"""
        with self.shm_manager.connect():
            while self._running:
                frame = self.shm_manager.read_frame()
                if frame is not None:
                    with self._frame_lock:
                        self._current_frame = frame
                time.sleep(1.0 / self.config.fps)  # Maintain frame rate
                
    def get_frame(self) -> Optional[np.ndarray]:
        """Get the current frame"""
        with self._frame_lock:
            return self._current_frame.copy() if self._current_frame is not None else None

def create_gradio_interface(config: VideoConfig):
    """Create the Gradio interface"""
    
    streamer = VideoStreamer(config)
    
    def process_video():
        """Process video frames and yield them to Gradio"""
        try:
            streamer.start()
            frame_count = 0
            yield None, "Starting video processing..."
            while True:
                frame = streamer.get_frame()
                if frame is not None:
                    frame_count += 1
                    # Annotate frame with frame number
                    cv2_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    cv2.putText(
                        cv2_frame,
                        f"Frame: {frame_count}",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (255, 255, 255),
                        2
                    )
                    # Convert back to RGB for Gradio
                    frame_rgb = cv2.cvtColor(cv2_frame, cv2.COLOR_BGR2RGB)
                    # Downscale for display
                    display_width, display_height = 960, 540
                    frame_resized = cv2.resize(frame_rgb, (display_width, display_height), interpolation=cv2.INTER_AREA)
                    if frame_count % 30 == 0:
                        logger.info(f"Processed {frame_count} frames")
                    yield frame_resized, f"Processing frame {frame_count}"
                else:
                    yield None, f"Waiting for frame..."
                time.sleep(1.0 / config.fps)
        except Exception as e:
            logger.error(f"Error in video processing: {e}")
            yield None, f"Error: {str(e)}"
        finally:
            streamer.stop()
            
    with gr.Blocks() as demo:
        gr.Markdown("# GStreamer Shared Memory Video Stream")
        gr.Markdown("Streaming video from GStreamer's shared memory sink")
        
        with gr.Row():
            socket_path = gr.Textbox(
                label="Socket Path",
                value=config.socket_path,
                interactive=False
            )
            output_image = gr.Image(label="Live Stream", type="numpy")
            
        status = gr.Textbox(label="Stream Status", interactive=False)
        
        start_btn = gr.Button("Start Streaming")
        start_btn.click(
            fn=process_video,
            inputs=[],
            outputs=[output_image, status],
            api_name="stream"
        )
        
    return demo

def main():
    """Main entry point"""
    config = VideoConfig()
    
    # Read metadata from file before starting
    height, width, dtype_size = read_metadata_from_file(config.meta_path)
    config.height = height
    config.width = width
    # dtype_size is always 1 for uint8/RGB
    
    # Create and launch the Gradio interface
    demo = create_gradio_interface(config)
    demo.queue()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )

if __name__ == "__main__":
    main() 