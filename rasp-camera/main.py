from fastapi import FastAPI, BackgroundTasks, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
import cv2
import threading
import os
import numpy as np
from PIL import Image
import time
import pygame
from datetime import datetime
import configparser
from pathlib import Path
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to ["http://192.168.1.109:8080"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to manage camera feed
camera_active = False
cam = None
frame = None

# Configuration settings
# SCOPES = ['https://www.googleapis.com/auth/drive']
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CONFIG_FILE = 'config.ini'
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'
CAPTURED_FOLDER = 'captured_images'
UPLOAD_FOLDER = 'processed_images'
BACKGROUNDS_FOLDER = 'backgrounds'
SOUNDS_FOLDER = 'sounds'

# Create necessary directories
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)
Path(CAPTURED_FOLDER).mkdir(exist_ok=True)




def load_config():
    """Load configuration from the config file."""    
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config

def get_drive_service():
    """Set up and return Google Drive service."""
    creds = None

    # Load token if it exists
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If no (valid) credentials available, do login flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Start OAuth flow to get new token
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the new token
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def start_camera():
    global cam, frame, camera_active
    
    # Load configuration
    config = load_config()
    device_id = int(config['CAMERA']['device_id'])
    width = int(config['CAMERA']['width'])
    height = int(config['CAMERA']['height'])
    
    cam = cv2.VideoCapture(device_id)
    
    # Set resolution
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    
    camera_active = True

    while camera_active and cam.isOpened():
        ret, frame = cam.read()
        if not ret:
            break

        # Display the camera feed in a window
        cv2.imshow("Camera Preview - Press 'q' on keyboard to quit preview", frame)

        # Allow quitting preview with 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            camera_active = False

    cam.release()
    cv2.destroyAllWindows()


# Play camera shutter sound synchronously
def play_shutter_sound(sound_file):
    pygame.init()
    pygame.mixer.init()
    sound = pygame.mixer.Sound(sound_file)
    sound.play()
    
    # Wait for sound to finish playing
    while pygame.mixer.get_busy():
        time.sleep(0.1)

def upload_to_google_drive(file_path):
    """Upload a file to Google Drive and return the file ID."""
    try:
        # Get Drive service
        drive_service = get_drive_service()
        
        # If service couldn't be created, return None
        if drive_service is None:
            print("Failed to authenticate with Google Drive")
            return None
        
        # Load folder ID from config 
        config = load_config()
        folder_id = config['GOOGLE_DRIVE']['folder_id']
        
        file_name = os.path.basename(file_path)
        file_metadata = {'name': file_name}
        
        if folder_id and folder_id != 'your_folder_id_here':
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(file_path, resumable=True)
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        return file.get('id')
    except Exception as e:
        print(f"Failed to upload to Google Drive: {str(e)}")
        return None

def process_and_upload_image(original_image_path):
    """Process image, upscale, and upload to Google Drive."""
    try:
        # Create output paths
        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # bg_removed_path = os.path.join(UPLOAD_FOLDER, f"bg_removed_{timestamp}.jpg")
        # final_path = os.path.join(UPLOAD_FOLDER, f"final_{timestamp}.jpg")
        
        # 1. Remove background
        # print(f"Removing background from {original_image_path}...")
        # remove_background(original_image_path, bg_removed_path)

      

        # 2. Upscale image        
        #upscale_factor = float(config['PROCESSING']['upscale_factor'])
        #print(f"Upscaling image with factor {upscale_factor}...")
        #upscale_image(bg_removed_path, final_path, upscale_factor)
        
        config = load_config()

        # 3. Upload to Google Drive if enabled
        drive_enabled = config['GOOGLE_DRIVE'].get('enabled', 'true').lower() == 'true'
        if drive_enabled:
            print("Uploading to Google Drive...")
            file_id = upload_to_google_drive(original_image_path)
            if file_id:
                print(f"Upload successful. File ID: {file_id}")
            else:
                print("Upload to Google Drive failed")
        else:
            print("Google Drive upload disabled in config")
        
        # 4. Clean up intermediate file
        #if os.path.exists(bg_removed_path):
        #    os.remove(bg_removed_path)
        
        print(f"Processing complete. Final image saved to {original_image_path}")
        return original_image_path
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return None

@app.get("/")
def read_root():
    return {"message": "Raspberry Pi Camera API is running!"}

@app.get("/preview")
def preview_camera():
    global cam, camera_active

    if camera_active:
        return {"message": "Camera preview is already running!"}

    # Start camera preview in a separate thread so API remains responsive
    threading.Thread(target=start_camera, daemon=True).start()
    return {"message": "Camera preview started successfully! Visit your Pi's monitor to see the preview."}

@app.get("/capture")
def capture_image(background_tasks: BackgroundTasks):
    global frame, cam, camera_active

    if not camera_active or cam is None or frame is None:
        return {"error": "Camera is not active. Start the preview first by calling /preview."}

    # Save the current frame
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(CAPTURED_FOLDER, f"captured_image_{timestamp}.jpg")
    cv2.imwrite(filename, frame)
    
    play_shutter_sound(os.path.join(SOUNDS_FOLDER, f"camera.mp3"))
    play_shutter_sound(os.path.join(SOUNDS_FOLDER, f"captured.mp3"))
    # Start background processing
    background_tasks.add_task(process_and_upload_image, filename)
    
    return {
        "message": "Image captured successfully! Processing in background.",
        "filename": filename
    }

@app.get("/stop_preview")
def stop_preview():
    global camera_active
    camera_active = False
    return {"message": "Camera preview stopped successfully."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
