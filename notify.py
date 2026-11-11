import smtplib
from email.mime.text import MIMEText
import yaml
import os
from typing import Dict, Any
from load_config import lire_config_yaml


def send_email(
    subject: str,
    body: str,
    config_path: str = 'config.yaml',
    receiver_email: str = None
):
    """
    Sends an email using settings loaded from a YAML configuration file.
    Args:
        subject: The subject line of the email.
        body: The plain text body of the email.
        config_path: Path to the YAML configuration file.
        receiver_email: The email address of the recipient. If None, uses default from config.
    """
    try:
        config = lire_config_yaml(config_path)
        email_settings = config.get('email_config', {})
        if receiver_email is None:
            receiver_email = email_settings.get('default_receiver', '')


        required_keys = ['smtp_server', 'smtp_port', 'sender_email', 'sender_password']
        if not all(key in email_settings for key in required_keys):
            raise ValueError("Missing essential SMTP configuration settings in YAML file.")

        SMTP_SERVER = email_settings['smtp_server']
        SMTP_PORT = email_settings['smtp_port']
        SENDER_EMAIL = email_settings['sender_email']
        SENDER_PASSWORD = email_settings['sender_password']

        # 1. Create the message object
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email

        # 2. Connect and send
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())

        print(f"Email successfully sent to {receiver_email} !")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except ValueError as e:
        print(f"Configuration Error: {e}")
    except smtplib.SMTPAuthenticationError:
        print("Authentication failed. Check your sender email and password (or app password).")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
