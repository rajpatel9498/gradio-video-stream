# GStreamer Shared Memory Video Stream with Gradio

## How to Use This App

### 1. Install Requirements
- **Python 3.8+** (with `pip`)
- **GStreamer** (with plugins):
  ```bash
  sudo apt-get install gstreamer1.0-tools gstreamer1.0-plugins-good gstreamer1.0-plugins-bad
  ```
- **Python packages:**
  ```bash
  pip install -r requirements.txt
  ```

---

### 2. Prepare the Metadata File
This file tells the app the video frame shape. For 768x432 RGB:
```bash
python3 write_metadata.py
```
*(This script is already set up for 768x432. If you want a different resolution, edit `write_metadata.py` accordingly.)*

---

### 3. Start the GStreamer Pipeline
Open a new terminal and run:
```bash
while true; do
  gst-launch-1.0 -v \
    filesrc location=file.mp4 ! \
    decodebin ! \
    videoconvert ! \
    videoscale ! \
    video/x-raw,format=RGB,width=768,height=432 ! \
    shmsink socket-path=/tmp/shared_memory/video_stream sync=true wait-for-connection=false shm-size=10000000;
done
```
- Replace `file.mp4` with your video file.
- This will keep the shared memory stream alive.

---

### 4. Start the Gradio App
In another terminal:
```bash
cd gradio-stream-test
python3 app.py
```
- The app will launch a web server (default: http://localhost:7860).

---

### 5. View the Stream
- Open your browser and go to [http://localhost:7860](http://localhost:7860).
- Click **Start Streaming**.
- You should see the live video stream, downscaled for browser display.

---

## Running with Docker (Recommended)

### 1. Prepare the Metadata File
First, create the shared memory directory and metadata file:
```bash
mkdir -p /tmp/shared_memory
python3 write_metadata.py
```

### 2. Build the Docker Image
```bash
docker build -t gradio-shm-app .
```

### 3. Run with Docker Compose
```bash
docker-compose up
```

This will:
- Start a GStreamer container that streams your video file to shared memory
- Start a Gradio app container that displays the stream at http://localhost:7860
- Both containers use `ipc: host` to share the shared memory segment

### 4. View the Stream
- Open [http://localhost:7860](http://localhost:7860) in your browser
- Click **Start Streaming**

### 5. Stop Everything
```bash
docker-compose down
```

---

## Troubleshooting

- **Stripes, black frames, or "replica" images:**
  - Make sure the metadata file and GStreamer pipeline use the same resolution and format.
  - For 768x432, the metadata should be `(432, 768, 1)`.
  - Restart both the pipeline and the app after changes.
- **No video or "Waiting for frame…":**
  - Ensure the GStreamer pipeline is running and the shared memory file exists.
  - Check logs for errors.
- **Multiple GStreamer processes:**
  - Only one pipeline should write to the shared memory at a time.
- **Docker: Can't find shared memory file:**
  - Make sure both containers have `ipc: host` in the docker-compose file.
  - The shared memory file is created in `/dev/shm` and must be shared between containers.

---

## Customizing Resolution

- Change both the GStreamer pipeline and the metadata file to match your desired resolution.
- Example for 1920x1080:
  - GStreamer: `video/x-raw,format=RGB,width=1920,height=1080`
  - Metadata: `f.write(struct.pack('III', 1080, 1920, 1))`

---

## How It Works

- **GStreamer** writes raw RGB frames to a shared memory segment using `shmsink`.
- **A metadata file** (`/tmp/shared_memory/video_stream.meta`) stores the frame height, width, and dtype size (always 1 for uint8/RGB).
- **Python/Gradio** reads the metadata, then reads and displays frames from shared memory.
- **Reconnection Logic** automatically detects when the shared memory file changes (e.g., when the video restarts) and reconnects.

---

## Requirements
- Python 3.8+
- GStreamer (with plugins)
- Python packages: see `requirements.txt`
- Docker & Docker Compose (for containerized use)

---

## License
MIT 