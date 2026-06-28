import csv, smtplib, time, os, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import openai
from config import Config

client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

PROMPT = """
Eres un Gerente de Ventas B2B Senior y Consultor de Operaciones de INSPOL México.

Debes generar un correo de prospección B2B siguiendo EXACTAMENTE el siguiente formato (el mismo que se usó para VENTA DE ROPA y que fue aprobado):

---

Estimado equipo de {nombre},

INSIGHT: [1 párrafo con contexto del sector y ubicación. Ejemplo: "En el sector de comercio al por menor de ropa en Aguascalientes, la gestión eficiente de inventario y la optimización de rutas de distribución son desafíos críticos que pueden impactar la rentabilidad de las empresas. La falta de visibilidad sobre la ubicación de la mercancía y la eficacia de las entregas puede llevar a pérdidas operativas significativas."]

PROBLEMAS:
- [Problema 1 específico del giro]
- [Problema 2 específico del giro]
- [Problema 3 específico del giro]

SOLUCION: [Explicación de cómo INSPOL resuelve estos problemas con GPS, telemetría, videotelemática e INSPOL TRACK. Ejemplo: "INSPOL ofrece soluciones de rastreo GPS en tiempo real y telemetría para monitorear la ubicación de la mercancía y optimizar las rutas de distribución. Además, con la videotelemática, es posible tener evidencia de incidentes en puntos de venta o durante el transporte. La plataforma INSPOL TRACK permite una gestión centralizada de la flotilla de vehículos y la mercancía, mejorando la eficiencia operativa y reduciendo costos asociados a la logística."]

En empresas con operación basada en rutas y traslados constantes, esto normalmente se traduce en costos que no siempre se detectan de forma inmediata, como:
- Falta de visibilidad operativa
- Costos ocultos no detectados
- Falta de evidencia ante incidentes

Para este tipo de escenarios, en INSPOL implementamos soluciones de telemetría y monitoreo en tiempo real que permiten tener control completo de la operación, sin importar si se trata de una unidad o una flotilla completa. A través de nuestra plataforma INSPOL TRACK, es posible centralizar la información de cada vehículo, generar alertas automáticas, analizar recorridos históricos y contar con evidencia en caso de incidentes, todo desde un mismo sistema.

Más que rastreo, el objetivo es convertir la operación diaria en información útil para reducir pérdidas, mejorar el control y tomar decisiones basadas en datos reales.

Si lo considera adecuado, con gusto podemos agendar una breve conversación de 15 minutos para revisar su operación y detectar posibles áreas de mejora, sin ningún compromiso.

Para más información, puede consultar nuestro documento completo:
<a href="https://inspol.com.mx/static/INSPOL_Soluciones.pdf">Descargar PDF</a>

<p style="text-align:center; margin-top:30px;">
    <a href="https://wa.me/5623682625?text=Hola%20INSPOL%2C%20vi%20su%20correo%20y%20estoy%20interesado"
       style="background-color:#25D366; color:white; padding:12px 25px; border-radius:30px; text-decoration:none; font-weight:bold; display:inline-block;">
       📱 Contáctanos por WhatsApp
    </a>
</p>

Saludos cordiales,
<strong>Equipo INSPOL México</strong>
ventas@inspol.com.mx

<p style="font-size:12px; color:#888; margin-top:40px;">
    Este correo fue enviado por INSPOL México. Si no deseas recibir más comunicaciones, responde a este mensaje con "BAJA".
</p>

---

REGLAS ESTRICTAS:
1. El INSIGHT debe ser específico del giro (SCIAN) y ubicación.
2. Los 3 problemas deben ser reales y específicos del sector.
3. NO uses frases genéricas como "en el sector es común".
4. NO añadas ningún texto fuera de esta estructura.
5. NO incluyas "ASUNTO:", ni "INTENCIÓN:", ni "PROBABILIDAD:".
6. El correo debe parecer un análisis operativo real, como el de VENTA DE ROPA.

DATOS DE LA EMPRESA:
- Nombre: {nombre}
- Actividad: {actividad}
- Personal: {personal}
- Ubicación: {municipio}, {estado}

AHORA, GENERA EL CORREO COMPLETO PARA ESTA EMPRESA.
"""

def generar_correo(lead):
    prompt = PROMPT.format(
        nombre=lead["nombre"],
        actividad=lead["actividad"],
        personal=lead["personal"],
        municipio=lead["municipio"],
        estado=lead["estado"]
    )
    try:
        r = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un Gerente de Ventas B2B Senior y Consultor de Operaciones de INSPOL México. Generas correos profesionales como el de VENTA DE ROPA."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=650,
            temperature=0.7
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ IA: {e}")
        return None

def enviar(dest, asunto, html):
    try:
        s = smtplib.SMTP("mail.inspol.com.mx", 587)
        s.starttls()
        s.login("ventas@inspol.com.mx", "Inspol2.0@2026")
        msg = MIMEMultipart()
        msg["From"] = "ventas@inspol.com.mx"
        msg["To"] = dest
        msg["Subject"] = asunto
        msg.attach(MIMEText(html, "html"))
        s.sendmail("ventas@inspol.com.mx", dest, msg.as_string())
        s.quit()
        return True
    except Exception as e:
        print(f"❌ SMTP: {e}")
        return False

leads = []
with open("leads_10.csv", "r", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        leads.append(row)

print("=" * 70)
print("📧 ENVIANDO CORREOS MODELO VENTA DE ROPA")
print("=" * 70)
print(f"📌 Enviando {len(leads)} correos a avcusa686@gmail.com")
print("=" * 70)

for i, lead in enumerate(leads, 1):
    nombre = lead['nombre']
    print(f"\n[{i}/{len(leads)}] {nombre}")
    
    print("   🤖 Generando correo modelo...", end=" ")
    texto = generar_correo(lead)
    if not texto:
        print("❌")
        continue
    print("✅")
    
    # Convertir a HTML con saltos de línea
    html = f"<p>{texto.replace(chr(10), '<br>')}</p>"
    asunto = f"Análisis operativo para {nombre}"
    
    print(f"   📨 Enviando correo...", end=" ")
    if enviar("avcusa686@gmail.com", asunto, html):
        print("✅")
    else:
        print("❌")
    
    if i < len(leads):
        print("   ⏳ Esperando 8 segundos...")
        time.sleep(8)

print("\n" + "=" * 70)
print("✅ ENVÍO COMPLETADO")
print("📌 Revisa avcusa686@gmail.com")
print("=" * 70)
