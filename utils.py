import csv
import io
import smtplib
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import url_for
from models import db, Contact, Campaign, Event
from datetime import datetime
import re

def reemplazar_variables(texto, datos):
    for clave, valor in datos.items():
        texto = texto.replace("{{" + clave + "}}", str(valor))
    return texto

def generar_pixel_url(contact_id):
    # En producción, usar dominio real
    return f"/track/pixel?contact_id={contact_id}"

def generar_click_url(contact_id, url_destino):
    # Codificar la URL para pasarla como parámetro
    return f"/track/click?contact_id={contact_id}&url={url_destino}"

def insertar_tracking(html, contact_id):
    # Insertar pixel de apertura
    pixel = f'<img src="{generar_pixel_url(contact_id)}" width="1" height="1" style="display:none;" />'
    # Insertar antes de </body>
    if '</body>' in html:
        html = html.replace('</body>', pixel + '</body>')
    else:
        html += pixel

    # Convertir enlaces normales a enlaces con tracking
    # Usamos regex para encontrar todos los <a href="...">
    def reemplazar_enlace(match):
        url = match.group(1)
        if not url.startswith('http'):
            return match.group(0)  # no tocamos enlaces relativos
        nueva_url = generar_click_url(contact_id, url)
        return f'<a href="{nueva_url}"{match.group(2) or ""}>'

    pattern = re.compile(r'<a\s+href="([^"]+)"([^>]*)>', re.IGNORECASE)
    html = pattern.sub(reemplazar_enlace, html)

    return html

def enviar_correo(remitente, destinatario, asunto, cuerpo_html, smtp_host, smtp_puerto, password):
    msg = MIMEMultipart('alternative')
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = asunto
    parte_html = MIMEText(cuerpo_html, 'html', 'utf-8')
    msg.attach(parte_html)
    try:
        servidor = smtplib.SMTP(smtp_host, smtp_puerto)
        servidor.starttls()
        servidor.login(remitente, password)
        servidor.sendmail(remitente, destinatario, msg.as_string())
        servidor.quit()
        return True
    except Exception as e:
        print(f"❌ Error enviando a {destinatario}: {e}")
        return False

def send_campaign_thread(campaign_id, password, smtp_host, smtp_port):
    from app import app  # importamos aquí para evitar circular
    with app.app_context():
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return
        contacts = Contact.query.filter_by(campaign_id=campaign_id, status='pending').all()
        total = len(contacts)
        campaign.total_contacts = total
        campaign.status = 'sending'
        db.session.commit()

        for idx, contact in enumerate(contacts, start=1):
            # Reemplazar variables en asunto y cuerpo
            lead_data = {
                'Correo electrónico': contact.email,
                'Nombre de la Unidad Económica': contact.name or 'Cliente'
            }
            # Si tenemos más campos, podríamos almacenarlos en JSON en Contact
            asunto_personalizado = reemplazar_variables(campaign.subject, lead_data)
            cuerpo_personalizado = reemplazar_variables(campaign.body_html, lead_data)

            # Insertar tracking
            cuerpo_con_tracking = insertar_tracking(cuerpo_personalizado, contact.id)

            # Enviar
            ok = enviar_correo(
                campaign.sender_email,
                contact.email,
                asunto_personalizado,
                cuerpo_con_tracking,
                smtp_host,
                smtp_port,
                password
            )
            if ok:
                contact.status = 'sent'
                contact.sent_at = datetime.utcnow()
            else:
                contact.status = 'failed'
            db.session.commit()

            # Pequeña pausa para no sobrecargar
            if idx % 10 == 0:
                time.sleep(1)

        campaign.status = 'sent'
        campaign.sent_at = datetime.utcnow()
        db.session.commit()
