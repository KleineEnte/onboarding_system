import imaplib
import email
import os
import pandas as pd
import pdfkit
from jinja2 import Template
from PyPDF2 import PdfWriter, PdfReader, PageObject
from datetime import datetime
from email.header import decode_header
import time
from pathlib import Path
from dotenv import load_dotenv
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

# Load environment variables from .env file
load_dotenv(dotenv_path=Path(__file__).parent / 'env' / '.env')

# Retrieve secret credentials and directories from environment variables
IMAP_SERVER = os.getenv('IMAP_SERVER')
SMTP_SERVER = os.getenv('SMTP_SERVER')
EMAIL_PORT = int(os.getenv('EMAIL_PORT'))
EMAIL_ACCOUNT = os.getenv('EMAIL_ACCOUNT')
PASSWORD = os.getenv('PASSWORD')
MAILBOX = os.getenv('MAILBOX')

# Recipients from .env file
MINUTH_EMAIL = os.getenv('MINUTH_EMAIL')
DRITICH_EMAIL = os.getenv('DRITICH_EMAIL')

# Retrieve directory paths from environment variables
TEMPLATES_DIR = Path(os.getenv('TEMPLATES_DIR'))
ATTACHMENTS_DIR = Path(os.getenv('ATTACHMENTS_DIR'))
ONBOARDED_DIR = Path(os.getenv('ONBOARDED_DIR'))
TEMP_PDF_DIR = Path(os.getenv('TEMP_PDF_DIR'))
EMAIL_TEXT_DIR = Path(os.getenv('EMAIL_TEXT_DIR'))

# Ensure directories exist
for directory in [ATTACHMENTS_DIR, TEMPLATES_DIR, ONBOARDED_DIR, TEMP_PDF_DIR, EMAIL_TEXT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Configure path to wkhtmltopdf
path_to_wkhtmltopdf = Path(r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
config = pdfkit.configuration(wkhtmltopdf=str(path_to_wkhtmltopdf))
options = {
    'enable-local-file-access': None,
    'page-size': 'A4',
    'margin-top': '50mm',
    'margin-bottom': '20mm',
    'margin-left': '20mm',
    'margin-right': '20mm'
}

# Function to send an email with dynamic content
def send_email_notification(to_email, subject, template_file, context):
    try:
        # Load the email content from the text file and render the template
        with open(template_file, 'r', encoding='utf-8') as file:
            template_content = file.read()

        # Render the email content with the context (employee data)
        template = Template(template_content)
        rendered_content = template.render(context)

        msg = MIMEMultipart()
        msg['From'] = EMAIL_ACCOUNT
        msg['To'] = to_email
        msg['Subject'] = subject

        # Attach the rendered email body
        msg.attach(MIMEText(rendered_content, 'plain'))

        # Send the email via SMTP over SSL
        print(f"Attempting to connect to SMTP server {SMTP_SERVER} on port {EMAIL_PORT} using SSL...")
        with smtplib.SMTP_SSL(SMTP_SERVER, EMAIL_PORT) as server:
            print(f"Connected to SMTP server {SMTP_SERVER}, attempting to login...")
            server.login(EMAIL_ACCOUNT, PASSWORD)
            print(f"Logged in successfully, sending email to {to_email}...")
            server.send_message(msg)
            print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
    finally:
        # Introduce a small delay between emails to avoid potential throttling issues
        time.sleep(5)

# Helper function to split a list into chunks of a specified size and format it in title case
def chunk_list(data_list, chunk_size=4):
    title_case_list = [item.title() for item in data_list]
    for i in range(0, len(title_case_list), chunk_size):
        yield title_case_list[i:i + chunk_size]

# Function to generate PDF from HTML
def generate_pdf_from_html(html_content, output_pdf):
    try:
        pdfkit.from_string(html_content, output_pdf, configuration=config, options=options)
        print(f"Generated PDF: {output_pdf}")
    except Exception as e:
        print(f"Error generating PDF {output_pdf}: {e}")

# Overlay generated PDF content onto the letterhead
def overlay_content_on_letterhead(content_pdf, letterhead_pdf, output_pdf):
    try:
        letterhead_reader = PdfReader(letterhead_pdf)
        content_reader = PdfReader(content_pdf)

        writer = PdfWriter()
        letterhead_page = letterhead_reader.pages[0]

        for page_num in range(len(content_reader.pages)):
            content_page = content_reader.pages[page_num]
            overlay_page = PageObject.create_blank_page(width=letterhead_page.mediabox.width, height=letterhead_page.mediabox.height)
            overlay_page.merge_page(letterhead_page)
            overlay_page.merge_page(content_page)
            writer.add_page(overlay_page)

        with open(output_pdf, 'wb') as output_file:
            writer.write(output_file)
        print(f"Final PDF saved to: {output_pdf}")

    except Exception as e:
        print(f"Error overlaying content on letterhead: {e}")

# Function to process CSV and generate PDF with email feature
def process_csv_and_generate_pdf(csv_file):
    try:
        print(f"Processing CSV file: {csv_file}")

        # Load CSV data
        data = pd.read_csv(csv_file)
        print(f"CSV Data loaded successfully for {csv_file}")

        # Load the HTML template from the templates directory
        with open(TEMPLATES_DIR / 'onboarding_template.html', 'r', encoding='utf-8') as file:
            html_template = file.read()
        print("HTML template loaded successfully")

        for index, row in data.iterrows():
            try:
                print(f"Processing row {index}")
                
                # Split "Vorname und Nachname" into first and last name
                name_parts = row['Vorname und Nachname'].split()
                vorname = name_parts[0]
                nachname = " ".join(name_parts[1:])

                # Chunk the multiline fields into formatted lists
                arbeitsegeraete_list = list(chunk_list(row.get('Der Mitarbeiter Benötigt Folgende Arbeitsgeräte', '').split('\n')))
                zugaenge_list = list(chunk_list(row.get('Die Folgenden Zugänge und Rollen Sollen Zu Workspace Eingerichtet Werden', '').split('\n')))
                software_list = list(chunk_list(row.get('Darüber Hinaus Benötigt Er Folgende Software', '').split('\n')))
                account_list = list(chunk_list(row.get('Zugänge, Die Standardmäßig Eingerichtet Werden Sollen, Bitte Benennen', '').split('\n')))
                standard_zugaenge_list = row.get('Zugänge, Die Standardmäßig Eingerichtet Werden Sollen, Bitte Benennen', '').split('\n')
                printer_list = list(chunk_list(row.get('Ressourcen, Die Standardmäßig Eingerichtet Werden Sollen, Bitte Benennen', '').split('\n')))
                telephone = row.get('TUBS-Telefon-Direktwahl-Nr. 030 447202 (10-89)', None)



                # Prepare the context with employee data
                context = {
                    'VORNAME': vorname,
                    'NACHNAME': nachname,
                    'BERUFSBEZEICHNUNG': row.get('Berufsbezeichnung', 'N/A'),
                    'ABTEILUNG': row.get('Abteilung', 'N/A'),
                    'EMAIL': row.get('Gewünschte Dienstliche E-Mail-Adresse', 'N/A'),
                    'VERTRAGSBEGINN': row.get('Vertragsbeginn', 'N/A'),
                    'UEBERGABEDATUM': row.get('Gewünschtes Übergabedatum der Geräte', 'N/A'),
                    'GRUPPENPOSTFAECHER_ERFORDERLICH': row.get('Gruppenpostfächer Erforderlich?', 'N/A'),
                    'ZUGAENGE_LIST': zugaenge_list,
                    'ARBEITSGERÄTE_LIST': arbeitsegeraete_list,
                    'SOFTWARE_LIST': software_list,
                    'ACCOUNT_LIST': account_list,  # Pass Standard-Zugänge data
                    'STANDARD_ZUGAENGE': row.get('Zugänge, Die Standardmäßig Eingerichtet Werden Sollen, Bitte Benennen', ''),
                    'SOFTWAREWUNSCH': row.get('Haben Sie Einen Zusätzlichen Softwarewunsch?', ''),
                    'STANDARD_RESSOURCEN': printer_list,
                    'TELEFONNUMMER': telephone,
                    'BEMERKUNGEN': row.get('Haben Wir Irgendetwas Übersehen? Schreiben Sie Uns Hier.', 'nan'),
                    'VEREINBARUNG': row.get('Vereinbarung', ''),
                    'UNTERSCHRIFT': row.get('Unterschrift', ''),
                }

                # Fill the template with data
                html_content = Template(html_template).render(context)

                # Generate content PDF and save to temp_pdf directory
                content_pdf_path = TEMP_PDF_DIR / f'temp_content_{vorname}_{nachname}.pdf'
                print(f"Generating content PDF at: {content_pdf_path}")
                generate_pdf_from_html(html_content, str(content_pdf_path))

                # Define output PDF filename and save to onboarded_person directory
                output_pdf_path = ONBOARDED_DIR / f'onboarding_letter_{vorname}_{nachname}.pdf'.replace(" ", "_")

                # Overlay content on letterhead and save final PDF
                letterhead_pdf = TEMPLATES_DIR / 'templates.pdf'
                print(f"Overlaying content on letterhead: {letterhead_pdf}")
                overlay_content_on_letterhead(str(content_pdf_path), letterhead_pdf, output_pdf_path)

                print(f"Final PDF generated and saved at: {output_pdf_path}")

                # Email notifications based on conditions
                # Check for "Schlüssel" in ARBEITSGERÄTE_LIST and send email
                if any("Schlüssel".lower() in s.lower() for sublist in arbeitsegeraete_list for s in sublist if isinstance(s, str)):
                    print(f"'Schlüssel' found for {vorname} {nachname}")
                    send_email_notification(MINUTH_EMAIL, 'Schlüssel Required', EMAIL_TEXT_DIR / 'minuth_email.txt', context)

                # Check for "HR Works" in STANDARD_ZUGAENGE_LIST and send email
                if any("HR Works".lower() in s.lower() for s in standard_zugaenge_list if isinstance(s, str)):
                    print(f"'HR Works' found for {vorname} {nachname}")
                    send_email_notification(DRITICH_EMAIL, 'HR Works Access Required', EMAIL_TEXT_DIR / 'dritich_email.txt', context)

            except Exception as e:
                print(f"Error processing row {index}: {e}")

    except Exception as e:
        print(f"Error processing CSV {csv_file}: {e}")


# Function to check email for CSV attachments
def check_email_for_csv():
    try:
        # Connect to the email server
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, PASSWORD)
        mail.select(MAILBOX)

        # Search for all unread emails
        status, messages = mail.search(None, '(UNSEEN)')
        email_ids = messages[0].split()

        for e_id in email_ids:
            res, msg = mail.fetch(e_id, "(RFC822)")
            for response_part in msg:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]

                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")

                    print(f"Processing email: {subject}")

                    # Loop through email parts to find attachments
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_disposition = str(part.get("Content-Disposition"))
                            if "attachment" in content_disposition:
                                filename = part.get_filename()

                                if filename.endswith(".csv"):
                                    # Save the CSV attachment with a unique name
                                    unique_filename = f"{filename.split('.')[0]}_{uuid.uuid4().hex}.csv"
                                    filepath = ATTACHMENTS_DIR / unique_filename
                                    with open(filepath, "wb") as f:
                                        f.write(part.get_payload(decode=True))
                                    print(f"CSV file saved as {filepath}")

                                    # Process CSV and generate PDF
                                    process_csv_and_generate_pdf(filepath)

        mail.logout()
    except Exception as e:
        print(f"Failed to check email: {e}")

# Countdown timer for 30 seconds before checking again
def countdown_timer(seconds):
    for i in range(seconds, 0, -1):
        print(f"Waiting {i} seconds...", end="\r")
        time.sleep(1)
    print("Checking emails now...")

# Continuously check for new emails every 30 seconds
while True:
    check_email_for_csv()
    countdown_timer(30)
