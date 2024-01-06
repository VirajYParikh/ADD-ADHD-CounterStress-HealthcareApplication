import smtplib
import ssl
import sys
from configparser import ConfigParser
from email.message import EmailMessage
import logging
import os

DEBUG = True
COMPETITION_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # ../RobothonCompetition/ directory
EMAIL_CONFIG_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'config/email_config.ini') 

class EmailSender:
    logger = None
    SMTP_server = None
    SMTP_port = None
    sender_email = None
    sender_password = None

    def __init__(self):
        # Configure logging
        self.configureLogging()

        # Get email configuration
        self.readConfigFile()

    def configureLogging(self):
        LOG_FILE_PATH = os.path.join(COMPETITION_ROOT_DIR, 'logs/robothon_healthcare.log')
        LOG_LEVEL = logging.DEBUG
        self.logger = logging.getLogger(LOG_FILE_PATH)
        self.logger.setLevel(LOG_LEVEL)
        fh = logging.FileHandler(LOG_FILE_PATH)
        fh.setLevel(LOG_LEVEL)
        ch = logging.StreamHandler()
        ch.setLevel(LOG_LEVEL)
        #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def readConfigFile(self):
        configparse = ConfigParser()
        configparse.read(EMAIL_CONFIG_FILE_PATH)
        #configparse.read('../config/email_config.ini')
        self.SMTP_server = configparse.get('EMAIL', 'SMTP_server')
        self.SMTP_port = configparse.get('EMAIL', 'SMTP_port')
        self.sender_email = configparse.get('EMAIL', 'sender_email')
        self.sender_password = configparse.get('EMAIL', 'sender_password')
        self.debug_receiver_email = configparse.get('EMAIL', 'debug_receiver_email')

    def sendEmail(self, to_email, subject, message):
        if self.debug_receiver_email:
            to_email = self.debug_receiver_email

        if DEBUG:
            self.logger.info("Sending email...")
            self.logger.info(f"SMTP_server: {self.SMTP_server}")
            self.logger.info(f"SMTP_port: {self.SMTP_port}")
            self.logger.info(f"sender_email: {self.sender_email}")
            self.logger.info(f"sender_password: {self.sender_password}")
            self.logger.info("------------------------------------")
            self.logger.info(f"to_email: {to_email}")
            self.logger.info(f"subject: {subject}")
            self.logger.info(f"message: {message}")

        email_msg = EmailMessage()
        email_msg.set_content(message)
        email_msg['Subject'] = subject
        email_msg['From'] = self.sender_email
        email_msg['To'] = to_email

        s = None

        try:
            s = smtplib.SMTP_SSL(self.SMTP_server, self.SMTP_port)
            # s.starttls(context=ssl.create_default_context())
            # s.ehlo()
            s.login(self.sender_email, self.sender_password)
            s.send_message(email_msg)
        except Exception as e:
            self.logger.error(f"Cannot send email - an error occurred: {e}")
        finally:
            if s:
                s.quit()


if __name__ == "__main__":
    if DEBUG:
        emailer = EmailSender()
        to_email = 'joanna.gilberti@gmail.com'
        subject = "Test Subject"
        message = "This is a test email message body."
        emailer.sendEmail(to_email, subject, message)
