
# onboarding_system

This project automates the synchronization of local folders (`attachments` and `onboarded_person`) with corresponding directories in a Nextcloud instance. It checks for new or modified files in local folders and uploads them to the designated Nextcloud directories, using a persistent session for efficient authentication. Additionally, it includes features for email notification and PDF generation from HTML templates and CSV files.

## Features
- Generate pdf from the dynamic CSV file.
- Send email to to the recipient when it is necessary.
- Automatically syncs files between local folders and Nextcloud.
- Uploads only new or modified files to Nextcloud.
- Processes CSV attachments from emails to generate PDFs.
- Sends email notifications based on specific CSV content.
- Configurable synchronization interval (default is 60 seconds).
- Uses a persistent HTTP session for efficient communication with Nextcloud.
- Tracks files locally to prevent re-uploading of unchanged files.

## Requirements

- Python 3.8+
- Required Python libraries:
  - `requests`
  - `python-dotenv`
  - `HTTPBasicAuth` (from `requests`)
  - `pandas`
  - `jinja2`
  - `pdfkit`
  - `PyPDF2`
  - `imaplib`
  - `email`
  - `smtplib`

## Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/Bostame/onboarding_system.git
cd onboarding_system
```

### Step 2: Install Dependencies

Make sure you have Python 3.8+ installed. Use the following command to install dependencies:

```bash
pip install -r requirements.yml
```

### Step 3: Configure Environment Variables

Create an `.env` file inside the `env/` directory with the following content:

```env
# Nextcloud credentials and URLs
NEXTCLOUD_BASE_URL=https://your-nextcloud-url/remote.php/dav/files/your-user
NEXTCLOUD_USERNAME=your-username
NEXTCLOUD_PASSWORD=your-password
NEXTCLOUD_DIRECTORY=Group-on-off-boarding

# Sync interval in seconds (default: 60 seconds)
SYNC_INTERVAL=60

# Local folder paths
TEMPLATES_DIR=templates
ATTACHMENTS_DIR=attachments
ONBOARDED_DIR=onboarded_person
TEMP_PDF_DIR=temp_pdf
EMAIL_TEXT_DIR=email_text

# Email details (if applicable)
IMAP_SERVER=imap.example.com
SMTP_SERVER=smtp.example.com
EMAIL_PORT=465
EMAIL_ACCOUNT=your-email@example.com
PASSWORD=your-email-password
MINUTH_EMAIL=minuth@example.com
DRITICH_EMAIL=dritich@example.com
```

### Step 4: Create Local Folders

Ensure the following local directories exist:

- `attachments/`
- `onboarded_person/`
- `templates/`
- `temp_pdf/`
- `email_text/`

You can modify these folder paths via the `.env` file as needed.

### Step 5: Run the Script

To manually run the synchronization and CSV processing:

```bash
python sync_script.py
python main.py
```

### Creating Systemd Service Units

To continuously run the synchronization and processing in the background, create systemd service units.

#### Step 1: Create the `onboarding-system.service` and `nextcloud-sync.service` Unit

1. Create a service file:

```bash
sudo nano /etc/systemd/system/onboarding-system.service
sudo nano /etc/systemd/system/nextcloud-sync.service
```

2. Add the following content to the file:

```ini
[Unit]
Description=Nextcloud Folder Sync Service
After=network.target

[Service]
User=root
Environment="PATH=/root/miniconda3/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
WorkingDirectory=/path/to/your/project
ExecStart=/bin/bash -lc 'source /root/miniconda3/etc/profile.d/conda.sh && conda activate csv_pdf && /root/miniconda3/envs/csv_pdf/bin/python main.py'
Restart=always

[Install]
WantedBy=multi-user.target
```
and

```ini
[Unit]
Description=Nextcloud Folder Sync Service
After=network.target

[Service]
User=root
Environment="PATH=/root/miniconda3/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
WorkingDirectory=/path/to/your/project
ExecStart=/bin/bash -lc 'source /root/miniconda3/etc/profile.d/conda.sh && conda activate csv_pdf && /root/miniconda3/envs/csv_pdf/bin/python sync_script.py'
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Save the file and close it.

#### Step 2: Reload Systemd Daemon

```bash
sudo systemctl daemon-reload
```

#### Step 3: Enable the Service

```bash
sudo systemctl enable onboarding-system.service
sudo systemctl enable nextcloud-sync.service
```

#### Step 4: Start the Service

```bash
sudo systemctl start onboarding-system.service
sudo systemctl start nextcloud-sync.service
```

#### Step 5: Check the Service Status

```bash
sudo systemctl status onboarding-system.service
sudo systemctl status nextcloud-sync.service
```

### Logging

To view logs for the `nextcloud-sync` service, use the following command:

```bash
journalctl -u nextcloud-sync.service
```

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
