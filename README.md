# Raspberry Pi AI Photo Booth Camera

A web-based application to operate a Raspberry Pi camera with AI background removal capabilities.

## Features

- Live camera preview
- Photo capture
- Background removal
- Auto-upload to Google Drive
- Web-based control interface

## Project Structure

```
.
├── operate-camera/       # Web interface to control the camera
│   └── index.html       # Control panel UI
└── rasp-camera/         # Raspberry Pi camera application
    ├── main.py         # FastAPI server implementation
    ├── config.ini      # Configuration settings
    ├── credentials.json # Google Drive API credentials
    └── background-image/ # Background images for photo booth
```

## Setup & Installation

### Run camera application

Run the Camera application `rasp-camera` on Raspberry-pi. This application used UV package manager.

1. Create the Virtual Environment
```bash
uv venv
```

2. Activate virutal Environment.
```bash
source .venv/bin/activate
```

3. Run the application locally.
```bash
uv run main.py
```

4. Stop the Virutal Environment
```bash
deactivate
```



### Camera Control Interface

1. Navigate to the operate-camera directory:
```bash
cd operate-camera
```

2. Start the web server:
```bash
python3 -m http.server 8080
```

3. Access the control panel at `http://localhost:8080`

### Camera Operations

The web interface provides four main operations:

1. **Health Check**: Verify if the camera application is running
2. **Preview**: Start the USB camera feed
3. **Capture**: Take a photo
4. **Stop Preview**: Close the camera feed

## Requirements

- Python 3.12+
- Raspberry Pi with camera module
- Web browser for control interface

## Dependencies

- FastAPI
- OpenCV
- Google Drive API
- Rembg (for background removal)
- Additional dependencies listed in `rasp-camera/pyproject.toml`

## License

[Add your license information here]
