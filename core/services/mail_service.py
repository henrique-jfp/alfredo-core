import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger("alfredo.mail")

def send_email(subject: str, html_body: str) -> bool:
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    target_email = os.getenv("USER_EMAIL")

    if not smtp_user or not smtp_pass or not target_email:
        logger.error("Credenciais SMTP ou USER_EMAIL ausentes no .env")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Alfredo Assistente <{smtp_user}>"
    msg["To"] = target_email

    part = MIMEText(html_body, "html")
    msg.attach(part)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, target_email, msg.as_string())
        logger.info(f"E-mail '{subject}' enviado com sucesso para {target_email}!")
        return True
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail: {e}")
        return False
