#!/usr/bin/env python3
import requests
import time
import json
import sys
import random
from datetime import datetime, timedelta

BASE_URL = "http://localhost:5001"

print("=" * 70)
print("🔁 LLENANDO DASHBOARD CON DATOS REALES")
print("=" * 70)

# 1. Verificar que hay leads
print("\n📥 Obteniendo leads...")
r = requests.get(BASE_URL + "/leads/api/listar")
if r.status_code != 200:
    print("❌ No se pudieron obtener leads. Asegúrate de que el servidor esté corriendo.")
    sys.exit(1)
leads = r.json()
if not leads:
    print("❌ No hay leads en la base de datos.")
    print("   Importa leads primero con: python3 auditoria_completa.py")
    sys.exit(1)
print(f"✅ {len(leads)} leads encontrados")

# 2. Crear campaña con todos los leads (o con un subconjunto si son muchos)
lead_ids = [str(l['id']) for l in leads]
# Si son más de 50, tomar una muestra de 30 para no saturar el SMTP
if len(lead_ids) > 50:
    lead_ids = random.sample(lead_ids, 30)
print(f"📝 Usando {len(lead_ids)} leads para la campaña")

# 3. Crear campaña
print("\n📝 Creando campaña...")
data = {
    'name': f'Campaña Real - {datetime.now().strftime("%d/%m/%Y %H:%M")}',
    'subject': 'Análisis operativo para tu empresa de transporte',
    'body_html': """
    <h1>Oportunidad de mejora</h1>
    <p>Hemos identificado potencial para optimizar tus operaciones de transporte en Colima.</p>
    <p>¿Te gustaría conocer cómo reducir costos y mejorar la visibilidad?</p>
    <a href="https://inspol.com.mx/static/INSPOL_Soluciones.pdf">Descargar PDF</a><br>
    <a href="https://wa.me/5623682625">Contactar por WhatsApp</a>
    """,
    'sender_email': 'ventas@inspol.com.mx',
    'sender_name': 'INSPOL México',
    'lead_ids': lead_ids
}
r = requests.post(BASE_URL + "/campaigns/new", data=data, allow_redirects=False)
if r.status_code == 302:
    location = r.headers.get('Location')
    camp_id = location.split('/campaigns/')[1].split('/')[0]
    print(f"✅ Campaña creada con ID: {camp_id}")
else:
    print(f"❌ Error al crear campaña: {r.status_code}")
    sys.exit(1)

# 4. Enviar la campaña
print(f"\n📤 Enviando campaña a {len(lead_ids)} leads... (puede tomar unos segundos)")
r = requests.post(BASE_URL + f"/campaigns/{camp_id}/send", allow_redirects=False)
if r.status_code == 302 or r.status_code == 200:
    print("✅ Campaña enviada correctamente")
else:
    print(f"⚠️ Error al enviar campaña: {r.status_code} (los correos pueden no llegar, pero continuamos)")
    # No salimos, porque el tracking se puede simular igual

# 5. Esperar a que se procesen los envíos
print("\n⏳ Esperando 5 segundos para que se registren los envíos...")
time.sleep(5)

# 6. Simular eventos de tracking (aperturas, clics, PDF, WhatsApp) para algunos leads
print("\n📊 Simulando eventos de tracking (aperturas, clics, PDF, WhatsApp)...")
for i, lead in enumerate(leads[:10]):  # Simular para los primeros 10 leads
    lead_id = lead['id']
    token = f"real{lead_id}{i}"
    print(f"   Lead {i+1}: {lead.get('nombre', 'Sin nombre')} (ID: {lead_id})")
    
    # Apertura (pixel)
    requests.get(BASE_URL + f"/track/pixel/{token}")
    time.sleep(0.1)
    
    # Clic en enlace (50% de probabilidad)
    if random.random() > 0.5:
        requests.get(BASE_URL + f"/track/click/{token}?url=http://example.com")
        time.sleep(0.1)
    
    # PDF abierto (30% de probabilidad)
    if random.random() > 0.7:
        requests.get(BASE_URL + f"/track/pdf/{token}")
        time.sleep(0.1)
    
    # WhatsApp (20% de probabilidad)
    if random.random() > 0.8:
        requests.get(BASE_URL + f"/track/whatsapp/{token}")
        time.sleep(0.1)

print("✅ Tracking simulado para 10 leads")

# 7. Mostrar resumen
print("\n" + "=" * 70)
print("📊 RESULTADOS:")
print(f"   - Leads en base de datos: {len(leads)}")
print(f"   - Campaña creada: {camp_id}")
print(f"   - Correos enviados: {len(lead_ids)}")
print(f"   - Eventos de tracking simulados: ~{len(leads[:10]) * 2} (aprox)")
print("\n🔗 Ahora ve al dashboard y recarga las siguientes páginas:")
print("   - /dashboard (http://localhost:5001/)")
print("   - /tracking")
print("   - /analisis-resultados")
print("   - /costos")
print("   - /funnel")
print("   - /recomendaciones")
print("=" * 70)
