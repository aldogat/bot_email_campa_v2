import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

with open('config_user.json', 'r') as f:
    config = json.load(f)

msg = MIMEMultipart()
msg["From"] = f"{config['default_sender_name']} <{config['default_sender_email']}>"
msg["To"] = "avcusa686@gmail.com"
msg["Subject"] = "Prueba de envío - Dashboard INSPOL AI"

body = """
Hola,

Este es un correo de prueba enviado desde el sistema INSPOL AI Sales Intelligence.

El sistema funciona correctamente y está listo para usar.

Saludos,
INSPOL AI Sales Intelligence
"""
msg.attach(MIMEText(body, "plain"))

server = smtplib.SMTP(config['smtp_host'], config['smtp_port'])
server.starttls()
server.login(config['smtp_user'], config['smtp_password'])
server.sendmail(config['default_sender_email'], "avcusa686@gmail.com", msg.as_string())
server.quit()

print("✅ Correo enviado a avcusa686@gmail.com")
