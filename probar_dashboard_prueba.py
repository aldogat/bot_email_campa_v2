import requests
import time

BASE_URL = "http://localhost:5001"

# 1. Obtener PRIMERA PLUS
r = requests.get(BASE_URL + "/leads/api/listar")
if r.status_code != 200:
    print("❌ No se pudieron obtener leads")
    exit()
leads = r.json()
lead = None
for l in leads:
    if "PRIMERA PLUS" in l.get('nombre', ''):
        lead = l
        break

if not lead:
    print("❌ No se encontró PRIMERA PLUS")
    print("Primero importa leads con el script de auditoría")
    exit()

print(f"✅ Lead encontrado: {lead['nombre']} (ID: {lead['id']})")

# 2. Crear campaña solo para este lead
data = {
    'name': 'Prueba PRIMERA PLUS - Dashboard',
    'subject': 'Análisis operativo para PRIMERA PLUS',
    'body_html': '<h1>Oportunidad de mejora</h1><p>Hemos identificado potencial para optimizar tus operaciones de transporte en Colima.</p><p>¿Te gustaría conocer cómo reducir costos y mejorar la visibilidad?</p><a href="https://inspol.com.mx/static/INSPOL_Soluciones.pdf">Descargar PDF</a><br><a href="https://wa.me/5623682625">Contactar por WhatsApp</a>',
    'sender_email': 'ventas@inspol.com.mx',
    'sender_name': 'INSPOL México',
    'lead_ids': [str(lead['id'])]
}

r = requests.post(BASE_URL + "/campaigns/new", data=data, allow_redirects=False)
if r.status_code == 302:
    location = r.headers.get('Location')
    camp_id = location.split('/campaigns/')[1].split('/')[0]
    print(f"✅ Campaña creada con ID: {camp_id}")

    # 3. Enviar la campaña
    r2 = requests.post(BASE_URL + f"/campaigns/{camp_id}/send", allow_redirects=False)
    if r2.status_code == 302 or r2.status_code == 200:
        print("✅ Campaña enviada a avcusa686@gmail.com (PRIMERA PLUS)")
        print("   Revisa tu bandeja de entrada (y spam).")
    else:
        print(f"❌ Error al enviar campaña: {r2.status_code}")
else:
    print(f"❌ Error creando campaña: {r.status_code}")
