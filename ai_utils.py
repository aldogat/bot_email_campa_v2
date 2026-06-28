import openai
import os
from config import Config

client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

PROMPT = """
Eres un Gerente de Ventas B2B Senior y Consultor de Operaciones de INSPOL México.

Debes generar un correo de prospección B2B siguiendo EXACTAMENTE el siguiente formato (el mismo que se usó para VENTA DE ROPA y que fue aprobado, pero con un tono más provocador y consultivo):

---

Estimado equipo de {nombre},

INSIGHT: [1 párrafo que menciona una pérdida concreta del sector y hace una pregunta provocadora. Ejemplo: "En el sector de minería de piedra caliza en Pabellón de Arteaga, las pérdidas por ineficiencias en rutas y consumo de combustible no reportado pueden representar hasta un 15% del costo operativo. ¿Cuánto podría estar perdiendo su empresa sin que nadie lo sepa?"]

PROBLEMAS (redactados como preguntas que duelen):
- [Problema 1] ¿[Pregunta que provoca reflexión sobre el problema]?
- [Problema 2] ¿[Pregunta que provoca reflexión sobre el problema]?
- [Problema 3] ¿[Pregunta que provoca reflexión sobre el problema]?

SOLUCION: [Explicación breve enfocada en resultados medibles. Ejemplo: "En INSPOL no vendemos GPS. Detectamos dónde está perdiendo dinero su operación y le damos herramientas para que eso deje de pasar. Empresas mineras similares han reducido pérdidas por combustible en un 20% en los primeros 3 meses."]

Si le interesa saber cuánto podría estar perdiendo su operación, conversemos 15 minutos. Sin compromiso.

---

REGLAS ESTRICTAS:
1. El INSIGHT debe ser provocador y mencionar una pérdida o riesgo concreto.
2. Los 3 problemas deben ser preguntas que hagan sentir al cliente que eso le pasa a él.
3. La SOLUCION debe enfocarse en resultados, no en características técnicas.
4. NO uses frases genéricas como "en el sector es común".
5. NO añadas ningún texto fuera de esta estructura.
6. NO incluyas "ASUNTO:", ni "INTENCIÓN:", ni "PROBABILIDAD:".
7. NO uses "[Tu nombre]" en la firma. Usa "Equipo INSPOL México".
8. El correo debe parecer un análisis operativo real que genera curiosidad y ganas de responder.

DATOS DE LA EMPRESA:
- Nombre: {nombre}
- Actividad: {actividad}
- Personal: {personal}
- Ubicación: {municipio}, {estado}

AHORA, GENERA EL CORREO COMPLETO PARA ESTA EMPRESA.
"""

def generar_correo_personalizado(lead_data):
    prompt = PROMPT.format(
        nombre=lead_data.get('nombre', 'Cliente'),
        actividad=lead_data.get('actividad', 'su sector'),
        personal=lead_data.get('personal', 'No especificado'),
        municipio=lead_data.get('municipio', ''),
        estado=lead_data.get('estado', '')
    )
    try:
        r = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un Gerente de Ventas B2B Senior y Consultor de Operaciones de INSPOL México. Generas correos profesionales que provocan curiosidad y generan respuestas."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=650,
            temperature=0.7
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error IA: {e}")
        return f"""Estimado equipo de {lead_data.get('nombre', 'Cliente')},

INSIGHT: En el sector {lead_data.get('actividad', 'su sector')}, muchas empresas pierden hasta un 15% de su rentabilidad por falta de control en rutas y consumo de combustible. ¿Está seguro de que no le está pasando a usted?

PROBLEMAS:
- ¿Sabe exactamente cuánto combustible consume cada unidad y si hay desviaciones?
- ¿Tiene visibilidad en tiempo real de dónde están sus vehículos y si cumplen las rutas planeadas?
- ¿Cómo reacciona ante un incidente en carretera sin evidencia en video?

SOLUCION: En INSPOL no vendemos GPS, detectamos dónde está perdiendo dinero su operación y le damos herramientas para que eso deje de pasar. Empresas similares han reducido costos operativos hasta un 20% en 3 meses.

Si le interesa saber cuánto podría estar perdiendo, conversemos 15 minutos. Sin compromiso."""

def construir_html(correo):
    correo = correo.replace("[Tu nombre]", "Equipo INSPOL México")
    if "¿Actualmente" not in correo and "¿Cómo" not in correo:
        correo += "\n\n¿Actualmente cómo gestionan el control de sus rutas? Nos interesa conocer su experiencia para ver si podemos aportar valor."
    
    texto_html = correo.replace('\n', '<br>')
    html = f"<p>{texto_html}</p>"
    
    if "Descargar PDF" not in correo:
        html += """
<p style="margin-top:20px;">
    <a href="https://inspol.com.mx/static/INSPOL_Soluciones.pdf">Descargar PDF</a>
</p>
"""
    if "wa.me/5623682625" not in correo:
        html += """
<p style="text-align:center; margin-top:30px;">
    <a href="https://wa.me/5623682625?text=Hola%20INSPOL%2C%20vi%20su%20correo%20y%20estoy%20interesado"
       style="background-color:#25D366; color:white; padding:12px 25px; border-radius:30px; text-decoration:none; font-weight:bold; display:inline-block;">
       📱 Contáctanos por WhatsApp
    </a>
</p>
"""
    if "Equipo INSPOL México" not in correo or "ventas@inspol.com.mx" not in correo:
        html += """
<p>
    Saludos cordiales,<br>
    <strong>Equipo INSPOL México</strong><br>
    ventas@inspol.com.mx
</p>
"""
    if "BAJA" not in correo:
        html += """
<p style="font-size:12px; color:#888; margin-top:40px;">
    Este correo fue enviado por INSPOL México. Si no deseas recibir más comunicaciones, responde a este mensaje con "BAJA".
</p>
"""
    return html

def generar_correo_completo(nombre, actividad, personal, municipio, estado):
    lead_data = {
        'nombre': nombre,
        'actividad': actividad,
        'personal': personal,
        'municipio': municipio,
        'estado': estado
    }
    texto_correo = generar_correo_personalizado(lead_data)
    html = construir_html(texto_correo)
    asunto = f"Análisis operativo para {nombre}"
    return asunto, html, texto_correo
