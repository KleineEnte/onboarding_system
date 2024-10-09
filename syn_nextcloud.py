import os
import requests
import time
import json
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import unquote

# Load environment variables from .env file securely
env_path = Path(__file__).parent / 'env' / '.env'
load_dotenv(dotenv_path=env_path)

# Load Nextcloud credentials and base information from the .env file
NEXTCLOUD_BASE_URL = os.getenv('NEXTCLOUD_BASE_URL').rstrip('/')
NEXTCLOUD_USERNAME = os.getenv('NEXTCLOUD_USERNAME')
NEXTCLOUD_PASSWORD = os.getenv('NEXTCLOUD_PASSWORD')
NEXTCLOUD_DIRECTORY = os.getenv('NEXTCLOUD_DIRECTORY').strip('/')

# Load the sync interval from the environment or set a default (in seconds)
SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL', 60))  # Default is 60 seconds

# Local folders to sync
local_folders = {
    'attachments': 'attachments',
    'onboarded_person': 'onboarded_person'
}

# Local file tracking for uploads
TRACKING_FILE = 'file_tracking.json'

def load_tracking_data():
    """Load the file tracking data from the tracking file."""
    if os.path.exists(TRACKING_FILE):
        with open(TRACKING_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_tracking_data(data):
    """Save the file tracking data to the tracking file."""
    with open(TRACKING_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_nextcloud_files(session, folder_name):
    """
    Get a list of files from a specific Nextcloud folder using a persistent session.

    Args:
        session (requests.Session): The persistent session object.
        folder_name (str): The subfolder name under the group folder on Nextcloud.
        
    Returns:
        list: A list of filenames from the Nextcloud folder.
    """
    try:
        nextcloud_url = f"{NEXTCLOUD_BASE_URL}/{NEXTCLOUD_DIRECTORY}/{folder_name}/"
        print(f"Connecting to Nextcloud folder: {nextcloud_url}")

        # Make a PROPFIND request to list files in the Nextcloud directory
        headers = {'Depth': '1'}
        response = session.request("PROPFIND", nextcloud_url, headers=headers)

        if response.status_code != 207:
            raise Exception(f"Failed to list Nextcloud files in {folder_name}. Status code: {response.status_code}")

        print(f"Successfully retrieved file list from Nextcloud folder: {folder_name}.")

        files = []
        for line in response.text.split('\n'):
            if '<d:href>' in line:
                filename = line.split('<d:href>')[1].split('</d:href>')[0].split('/')[-1]
                filename = unquote(filename).strip()
                if filename:
                    files.append(filename)

        print(f"Nextcloud '{folder_name}' contains {len(files)} files: {files}")
        return files

    except Exception as e:
        print(f"Error retrieving files from Nextcloud folder {folder_name}: {e}")
        return []

def upload_file_to_nextcloud(session, file_path, filename, folder_name):
    """
    Upload a file to a specific Nextcloud folder using a persistent session.
    
    Args:
        session (requests.Session): The persistent session object.
        file_path (str): The full path to the file to upload.
        filename (str): The name of the file being uploaded.
        folder_name (str): The Nextcloud subfolder where the file should be uploaded.
    """
    try:
        nextcloud_url = f"{NEXTCLOUD_BASE_URL}/{NEXTCLOUD_DIRECTORY}/{folder_name}/{filename}"
        print(f"Uploading file: {filename} to Nextcloud folder: {folder_name}...")

        with open(file_path, 'rb') as f:
            response = session.put(nextcloud_url, data=f)

        if response.status_code not in [200, 201, 204]:  # 204 is a valid status code for success
            raise Exception(f"Failed to upload {filename}. Status code: {response.status_code}")
        else:
            print(f"Successfully uploaded {filename} to Nextcloud folder: {folder_name}.")
            return True

    except Exception as e:
        print(f"Error uploading file {filename} to Nextcloud folder {folder_name}: {e}")
    return False

def check_for_new_files(session, local_folder, nextcloud_files, nextcloud_folder, tracking_data):
    """
    Check for new files in the local folder and upload them to Nextcloud using a persistent session.
    
    Args:
        session (requests.Session): The persistent session object.
        local_folder (str): The local folder to check for new files.
        nextcloud_files (list): The list of files already present in the Nextcloud folder.
        nextcloud_folder (str): The corresponding Nextcloud folder to upload new files to.
        tracking_data (dict): The dictionary containing tracked files and their modification times.
    """
    try:
        local_files = os.listdir(local_folder)
        print(f"Files found in local folder '{local_folder}': {local_files}")

        for file in local_files:
            file_path = os.path.join(local_folder, file)
            file_mtime = os.path.getmtime(file_path)

            # Check if the file is new or modified
            if file not in nextcloud_files and (file not in tracking_data or tracking_data[file] != file_mtime):
                print(f"New or modified file detected: {file} (from {local_folder})")
                if upload_file_to_nextcloud(session, file_path, file, nextcloud_folder):
                    # Update tracking data after successful upload
                    tracking_data[file] = file_mtime
            else:
                print(f"File {file} already exists in Nextcloud folder {nextcloud_folder} or has not been modified. Skipping...")
    except Exception as e:
        print(f"Error checking for new files in {local_folder}: {e}")

def sync_folders(session):
    """
    Check local folders for new files and upload them to the corresponding Nextcloud folders using a persistent session.
    
    Args:
        session (requests.Session): The persistent session object.
    """
    tracking_data = load_tracking_data()

    try:
        for local_folder, nextcloud_folder in local_folders.items():
            print(f"Checking local folder: {local_folder} for new files...")
            folder_path = os.path.abspath(local_folder)
            print(f"Local folder path: {folder_path}")

            if not os.path.exists(local_folder):
                print(f"Local folder {local_folder} does not exist. Skipping...")
                continue

            # Get a list of files in the corresponding Nextcloud folder
            nextcloud_files = get_nextcloud_files(session, nextcloud_folder)

            # Check for new files in the local folder and upload them
            check_for_new_files(session, local_folder, nextcloud_files, nextcloud_folder, tracking_data)

        # Save updated tracking data
        save_tracking_data(tracking_data)

    except Exception as e:
        print(f"Error during folder synchronization: {e}")

def countdown_timer(seconds):
    """
    Countdown timer that displays the remaining time before the next sync.
    
    Args:
        seconds (int): The number of seconds to count down.
    """
    for i in range(seconds, 0, -1):
        print(f"Next sync in {i} seconds...", end='\r')
        time.sleep(1)
    print("Starting sync now...")

def start_periodic_sync():
    """
    Start the periodic synchronization of local folders to Nextcloud.
    The synchronization interval is specified in the .env file or defaults to 60 seconds.
    """
    # Use a persistent session for Nextcloud requests
    with requests.Session() as session:
        # Set up authentication for the session
        session.auth = HTTPBasicAuth(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD)

        while True:
            print("Starting folder synchronization...")
            sync_folders(session)
            print("Synchronization complete.")
            countdown_timer(SYNC_INTERVAL)  # Wait for the specified sync interval

if __name__ == "__main__":
    print("Starting periodic folder synchronization service with a persistent session...")
    start_periodic_sync()
