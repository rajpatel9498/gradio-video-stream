import gradio as gr
import cv2
import numpy as np
from time import sleep
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_video(video_path):
    """Process video and yield frames in real-time"""
    if video_path is None:
        logger.info("No video provided")
        yield None, "No video provided"
        return
        
    logger.info(f"Processing video: {video_path}")
    yield None, "Starting video processing..."
    
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    logger.info(f"Total frames to process: {total_frames}")
    
    frame_count = 0
    
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Add frame number to the frame
            cv2.putText(
                frame,
                f"Frame: {frame_count}/{total_frames}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2
            )
            
            # Convert BGR to RGB for Gradio
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            frame_count += 1
            if frame_count % 10 == 0:  # Log every 10 frames
                logger.info(f"Processed {frame_count}/{total_frames} frames")
            
            yield frame_rgb, f"Processing frame {frame_count}/{total_frames}"
            sleep(0.1)  # Simulate processing delay
            
    finally:
        cap.release()
        
    logger.info(f"Finished processing video. Processed {frame_count} frames")
    yield None, "Processing complete!"

# Create the interface
with gr.Blocks() as demo:
    gr.Markdown("# Real-time Video Processing")
    gr.Markdown("Upload a video to see it process in real-time")
    
    with gr.Row():
        input_video = gr.Video(label="Input Video")
        output_image = gr.Image(label="Live Processing", type="numpy")
    
    status = gr.Textbox(label="Processing Status", interactive=False)
    
    process_btn = gr.Button("Start Processing")
    process_btn.click(
        fn=process_video,
        inputs=input_video,
        outputs=[output_image, status],
        api_name="process"
    )

if __name__ == "__main__":
    demo.queue()  # Enable queue for streaming
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True  # This creates a public URL
    ) 