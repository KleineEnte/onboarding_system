import os
import requests
import time
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file securely
env_path = Path(__file__).parent / 'env' / '.env'
load_dotenv(dotenv_path=env_path)

# Load Nextcloud credentials and base information from the .env file
NEXTCLOUD_BASE_URL = os.getenv('NEXTCLOUD_BASE_URL').rstrip('/')  # Remove trailing slash if any
NEXTCLOUD_USERNAME = os.getenv('NEXTCLOUD_USERNAME')
NEXTCLOUD_PASSWORD = os.getenv('NEXTCLOUD_PASSWORD')
NEXTCLOUD_DIRECTORY = os.getenv('NEXTCLOUD_DIRECTORY').strip('/')  # Ensure no leading/trailing slashes

# Load the sync interval from the environment or set a default (in seconds)
SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL', 60))  # Default is 60 seconds

# Local folders to sync
local_folders = {
    'attachments': 'attachments',
    'onboarded_person': 'onboarded_person'
}

def get_nextcloud_files(folder_name):
    """
    Get a list of files from a specific Nextcloud folder (e.g., 'attachments' or 'onboarded_person').
    
    Args:
        folder_name (str): The subfolder name under the group folder on Nextcloud.
        
    Returns:
        list: A list of filenames from the Nextcloud folder.
    """
    try:
        nextcloud_url = f"{NEXTCLOUD_BASE_URL}/{NEXTCLOUD_DIRECTORY}/{folder_name}/"
        print(f"Connecting to Nextcloud folder: {nextcloud_url}")

        # Make a PROPFIND request to list files in the Nextcloud directory
        headers = {
            'Depth': '1',  # Depth header to get all files in the directory
        }
        response = requests.request("PROPFIND", nextcloud_url, auth=HTTPBasicAuth(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD), headers=headers)

        if response.status_code != 207:
            raise Exception(f"Failed to list Nextcloud files in {folder_name}. Status code: {response.status_code}")

        print(f"Successfully retrieved file list from Nextcloud folder: {folder_name}.")

        # Extract filenames from the XML response
        files = []
        for line in response.text.split('\n'):
            if '<d:href>' in line:
                filename = line.split('<d:href>')[1].split('</d:href>')[0].split('/')[-1]
                if filename:  # Avoid empty strings
                    files.append(filename)

        print(f"Nextcloud '{folder_name}' contains {len(files)} files: {files}")
        return files

    except Exception as e:
        print(f"Error retrieving files from Nextcloud folder {folder_name}: {e}")
        return []

def upload_file_to_nextcloud(file_path, filename, folder_name):
    """
    Upload a file to a specific Nextcloud folder (e.g., 'attachments' or 'onboarded_person').
    
    Args:
        file_path (str): The full path to the file to upload.
        filename (str): The name of the file being uploaded.
        folder_name (str): The Nextcloud subfolder where the file should be uploaded.
    """
    try:
        nextcloud_url = f"{NEXTCLOUD_BASE_URL}/{NEXTCLOUD_DIRECTORY}/{folder_name}/{filename}"
        print(f"Uploading file: {filename} to Nextcloud folder: {folder_name}...")

        with open(file_path, 'rb') as f:
            response = requests.put(nextcloud_url, data=f, auth=HTTPBasicAuth(NEXTCLOUD_USERNAME, NEXTCLOUD_PASSWORD))

        if response.status_code not in [200, 201, 204]:  # 204 is a valid status code for success
            raise Exception(f"Failed to upload {filename}. Status code: {response.status_code}")
        else:
            print(f"Successfully uploaded {filename} to Nextcloud folder: {folder_name}.")

    except Exception as e:
        print(f"Error uploading file {filename} to Nextcloud folder {folder_name}: {e}")

def check_for_new_files(local_folder, nextcloud_files, nextcloud_folder):
    """
    Check for new files in the local folder and upload them to Nextcloud.
    
    Args:
        local_folder (str): The local folder to check for new files.
        nextcloud_files (list): The list of files already present in the Nextcloud folder.
        nextcloud_folder (str): The corresponding Nextcloud folder to upload new files to.
    """
    try:
        local_files = os.listdir(local_folder)
        print(f"Files found in local folder '{local_folder}': {local_files}")

        for file in local_files:
            if file not in nextcloud_files:
                file_path = os.path.join(local_folder, file)
                print(f"New file detected: {file} (from {local_folder})")
                upload_file_to_nextcloud(file_path, file, nextcloud_folder)
            else:
                print(f"File {file} already exists in Nextcloud folder {nextcloud_folder}. Skipping...")
    except Exception as e:
        print(f"Error checking for new files in {local_folder}: {e}")

def sync_folders():
    """
    Check local folders for new files and upload them to the corresponding Nextcloud folders.
    """
    try:
        for local_folder, nextcloud_folder in local_folders.items():
            print(f"Checking local folder: {local_folder} for new files...")
            folder_path = os.path.abspath(local_folder)
            print(f"Local folder path: {folder_path}")

            if not os.path.exists(local_folder):
                print(f"Local folder {local_folder} does not exist. Skipping...")
                continue

            # Get a list of files in the corresponding Nextcloud folder
            nextcloud_files = get_nextcloud_files(nextcloud_folder)

            # Check for new files in the local folder and upload them
            check_for_new_files(local_folder, nextcloud_files, nextcloud_folder)

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
    while True:
        print("Starting folder synchronization...")
        sync_folders()
        print("Synchronization complete.")
        countdown_timer(SYNC_INTERVAL)  # Wait for the specified sync interval

if __name__ == "__main__":
    print("Starting periodic folder synchronization service...")
    start_periodic_sync()
