# Gradio Video Stream Test

A real-time video processing application built with Gradio that demonstrates efficient frame streaming without disk I/O.

## Features

- Real-time video processing with frame-by-frame streaming
- Memory-efficient implementation (no disk I/O)
- Docker containerization
- Live frame display with processing status

## Project Structure

- `app.py`: Main application code
- `Dockerfile`: Container configuration
- `requirements.txt`: Python dependencies
- `docker-compose.yml`: Docker Compose configuration

## Setup and Running

### Using Docker

1. Build the Docker image:
```bash
docker build -t gradio-stream-app .
```

2. Run the container:
```bash
docker run -p 7860:7860 --rm gradio-stream-app
```

The application will be available at `http://localhost:7860`

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

## Implementation Details

- Uses Gradio for the web interface
- OpenCV for video processing
- Direct frame streaming without temporary files
- Memory-efficient processing pipeline

## Dependencies

- gradio==3.50.2
- opencv-python>=4.8.0
- numpy>=1.24.0 