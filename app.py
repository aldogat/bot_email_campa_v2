from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func
import os
import json
import smtplib
import hashlib
import base64
import re
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave-secreta-cambiar-en-produccion'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dashboard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ===== MODELOS =====
class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body_html = db.Column(db.Text, nullable=False)
    sender_email = db.Column(db.String(100), nullable=False)
    sender_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='draft')
    total_contacts = db.Column(db.Integer, default=0)
    contacts = db.relationship('Contact', backref='campaign', lazy=True)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(200), nullable=True)
    giro = db.Column(db.String(200), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    sent_at = db.Column(db.DateTime, nullable=True)
    opened_at = db.Column(db.DateTime, nullable=True)
    clicked_at = db.Column(db.DateTime, nullable=True)
    bounced = db.Column(db.Boolean, default=False)
    spam = db.Column(db.Boolean, default=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    type = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_agent = db.Column(db.String(200), nullable=True)
    ip = db.Column(db.String(50), nullable=True)

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200))
    razon_social = db.Column(db.String(200))
    actividad = db.Column(db.String(200))
    scian = db.Column(db.String(20))
    personal = db.Column(db.String(50))
    municipio = db.Column(db.String(100))
    estado = db.Column(db.String(100))
    telefono = db.Column(db.String(50))
    correo = db.Column(db.String(100))
    sitio_web = db.Column(db.String(200))
    fecha_denue = db.Column(db.String(50))
    scoring = db.Column(db.String(1))
    score_puntaje = db.Column(db.Integer)
    insight = db.Column(db.Text)
    riesgos = db.Column(db.Text)
    oportunidades = db.Column(db.Text)
    soluciones = db.Column(db.Text)
    prioridad = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    analyzed_at = db.Column(db.DateTime, nullable=True)

class CostLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=True)
    tokens_in = db.Column(db.Integer, default=0)
    tokens_out = db.Column(db.Integer, default=0)
    cost = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TrackingToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(32), unique=True, nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id'), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EmailLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=True)
    email_to = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body_html = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

# ===== FUNCIONES AUXILIARES =====
def get_smtp_config():
    try:
        with open('config_user.json', 'r') as f:
            return json.load(f)
    except:
        return {
            'smtp_host': 'mail.inspol.com.mx',
            'smtp_port': 587,
            'smtp_user': 'ventas@inspol.com.mx',
            'smtp_password': 'Inspol2.0@2026',
            'default_sender_name': 'INSPOL México',
            'default_sender_email': 'ventas@inspol.com.mx'
        }

def generar_token(contact_id, campaign_id):
    data = f"{contact_id}-{campaign_id}-{datetime.utcnow().timestamp()}"
    token = hashlib.md5(data.encode()).hexdigest()[:16]
    # Guardar en base de datos
    t = TrackingToken(token=token, contact_id=contact_id, campaign_id=campaign_id)
    db.session.add(t)
    db.session.commit()
    return token

def enviar_correo_campaign(contact, campaign, html_content, subject):
    config = get_smtp_config()
    try:
        token = generar_token(contact.id, campaign.id)
        pixel_url = f"http://localhost:5001/track/pixel/{token}"
        click_url = f"http://localhost:5001/track/click/{token}?url={{url}}"
        pdf_url = f"http://localhost:5001/track/pdf/{token}"
        whatsapp_url = f"http://localhost:5001/track/whatsapp/{token}"

        html_with_pixel = html_content.replace('</body>', f'<img src="{pixel_url}" width="1" height="1" style="display:none;" /></body>')

        def replace_links(match):
            url = match.group(1)
            if 'whatsapp' in url or 'wa.me' in url:
                return f'href="{whatsapp_url}"'
            elif '.pdf' in url or 'INSPOL_Soluciones.pdf' in url:
                return f'href="{pdf_url}"'
            else:
                return f'href="{click_url.replace("{{url}}", url)}"'
        html_with_pixel = re.sub(r'href="([^"]+)"', replace_links, html_with_pixel)

        msg = MIMEMultipart()
        msg["From"] = config['default_sender_email']
        msg["To"] = contact.email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_with_pixel, "html"))

        server = smtplib.SMTP(config['smtp_host'], config['smtp_port'])
        server.starttls()
        server.login(config['smtp_user'], config['smtp_password'])
        server.sendmail(config['default_sender_email'], contact.email, msg.as_string())
        server.quit()

        contact.sent_at = datetime.utcnow()
        contact.status = 'sent'
        db.session.commit()
        return True
    except Exception as e:
        contact.status = 'failed'
        contact.bounced = True
        db.session.commit()
        print(f"❌ Error enviando a {contact.email}: {e}")
        return False

def calcular_scoring(lead):
    puntaje = 0
    if lead.personal:
        try:
            if '-' in lead.personal:
                nums = [int(x.strip()) for x in lead.personal.split('-') if x.strip().isdigit()]
                personal_prom = sum(nums) // len(nums) if nums else 0
            else:
                personal_prom = int(lead.personal.replace('+', '').strip())
            if personal_prom >= 50: puntaje += 25
            elif personal_prom >= 20: puntaje += 20
            elif personal_prom >= 10: puntaje += 15
            elif personal_prom >= 5: puntaje += 10
            else: puntaje += 5
        except:
            puntaje += 5
    if lead.sitio_web and lead.sitio_web.strip():
        puntaje += 15
    if lead.actividad:
        keywords = ['transporte','logística','construcción','industrial','manufactura','comercio','distribución','alimentos','bebidas','automotriz']
        for kw in keywords:
            if kw.lower() in lead.actividad.lower():
                puntaje += 10
                break
    if lead.estado:
        estados_prioritarios = ['Ciudad de México','Jalisco','Nuevo León','Estado de México','Puebla','Guanajuato','Querétaro']
        for estado in estados_prioritarios:
            if estado.lower() in lead.estado.lower():
                puntaje += 10
                break
    if puntaje >= 60: scoring = 'A'
    elif puntaje >= 40: scoring = 'B'
    elif puntaje >= 20: scoring = 'C'
    else: scoring = 'D'
    return scoring, puntaje

def analizar_con_ia(lead):
    insights = [
        f"Empresa de {lead.actividad} con potencial de optimización operativa.",
        "Puede beneficiarse de control de combustible y geolocalización.",
        "Operaciones logísticas mejorables con videotelemática.",
        "Riesgo de desvíos de ruta detectado en su flotilla."
    ]
    riesgos = ["Falta de visibilidad en tiempo real","Posible robo de combustible sin controles","Rutas no optimizadas","Costos operativos elevados"]
    oportunidades = ["Implementar GPS para flotilla","Control de combustible con sensores","Videotelemática para seguridad","Geocercas y alertas automáticas"]
    return {
        'insight': random.choice(insights),
        'riesgos': ', '.join(random.sample(riesgos, 2)),
        'oportunidades': ', '.join(random.sample(oportunidades, 2)),
        'soluciones': 'Plataforma INSPOL TRACK (GPS, Telemetría, Videotelemática)',
        'prioridad': random.randint(1, 5)
    }

def importar_csv_leads(archivo):
    import csv
    leads_importados = 0

    # Intentar detectar la codificación automáticamente
    with open(archivo, "rb") as f:
        raw_data = f.read()
        try:
            import chardet
            result = chardet.detect(raw_data)
            encoding = result["encoding"] if result["encoding"] else "utf-8-sig"
            print(f"🔍 Codificación detectada: {encoding}")
        except:
            encoding = "latin-1"
            print("⚠️ No se pudo detectar codificación, usando latin-1")

    # Intentar abrir con la codificación detectada, si falla probar con latin-1
    encodings_to_try = [encoding, "latin-1", "windows-1252", "utf-8-sig", "utf-8"]
    rows = None
    for enc in encodings_to_try:
        try:
            with open(archivo, "r", encoding=enc) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                print(f"✅ Archivo leído correctamente con codificación: {enc}")
                break
        except (UnicodeDecodeError, csv.Error) as e:
            continue
    if rows is None:
        raise Exception("No se pudo decodificar el archivo con ninguna codificación común.")

    # Procesar las filas
    for row in rows:
        lead = Lead(
            nombre=row.get("Nombre de la Unidad Económica", "").strip(),
            razon_social=row.get("Razón Social", "").strip(),
            actividad=row.get("giro", "").strip() or row.get("Actividad", "").strip(),
            scian=row.get("scian", "").strip(),
            personal=row.get("personal", "").strip(),
            municipio=row.get("municipio", "").strip(),
            estado=row.get("estado", "").strip(),
            telefono=row.get("Teléfono", "").strip() or row.get("telefono", "").strip(),
            correo=row.get("Correo electrónico", "").strip() or row.get("correo", "").strip(),
            sitio_web=row.get("sitio_web", "").strip(),
            fecha_denue=row.get("fecha_denue", "").strip()
        )
        if not lead.correo:
            continue
        scoring, puntaje = calcular_scoring(lead)
        lead.scoring = scoring
        lead.score_puntaje = puntaje
        db.session.add(lead)
        leads_importados += 1
        if leads_importados % 100 == 0:
            db.session.commit()
    db.session.commit()
    return leads_importados

def analizar_rendimiento():
    total_campaigns = Campaign.query.count()
    total_contacts = Contact.query.count()
    total_sent = Contact.query.filter(Contact.sent_at.isnot(None)).count()
    total_opens = Event.query.filter_by(type='open').count()
    total_clicks = Event.query.filter_by(type='click').count()
    total_responses = Event.query.filter_by(type='reply').count()

    open_rate = round((total_opens / total_sent * 100) if total_sent else 0, 1)
    click_rate = round((total_clicks / total_opens * 100) if total_opens else 0, 1)
    response_rate = round((total_responses / total_sent * 100) if total_sent else 0, 1)

    top_campaigns = []
    campaigns = Campaign.query.filter(Campaign.sent_at.isnot(None)).all()
    for camp in campaigns:
        contacts = Contact.query.filter_by(campaign_id=camp.id).all()
        sent = sum(1 for c in contacts if c.sent_at)
        opened = sum(1 for c in contacts if c.opened_at)
        clicked = sum(1 for c in contacts if c.clicked_at)
        responded = sum(1 for c in contacts if c.opened_at and c.clicked_at)
        if sent > 0:
            top_campaigns.append({
                'name': camp.name,
                'sent': sent,
                'open_rate': round((opened/sent*100), 1),
                'click_rate': round((clicked/opened*100) if opened else 0, 1),
                'response_rate': round((responded/sent*100), 1)
            })
    top_campaigns = sorted(top_campaigns, key=lambda x: x['open_rate'], reverse=True)[:5]

    industrias = {}
    leads = Lead.query.filter(Lead.actividad.isnot(None)).all()
    for lead in leads:
        ind = lead.actividad[:20]
        industrias[ind] = industrias.get(ind, 0) + 1

    scoring_analysis = {}
    for s in ['A', 'B', 'C', 'D']:
        leads = Lead.query.filter_by(scoring=s).all()
        if leads:
            total = len(leads)
            analizados = sum(1 for l in leads if l.analyzed_at)
            scoring_analysis[s] = {
                'total': total,
                'analizados': analizados,
                'open_rate': round((analizados/total*100), 1) if total else 0
            }

    keyword_performance = [
        {'keyword': 'combustible', 'clicks': 45, 'opens': 120},
        {'keyword': 'seguridad', 'clicks': 38, 'opens': 98},
        {'keyword': 'logística', 'clicks': 32, 'opens': 85},
        {'keyword': 'flotilla', 'clicks': 28, 'opens': 72},
        {'keyword': 'ruta', 'clicks': 22, 'opens': 60}
    ]

    recomendaciones = []
    if open_rate < 20:
        recomendaciones.append("⚠️ La tasa de apertura es baja (<20%). Revisa tus asuntos y horarios de envío.")
    elif open_rate < 40:
        recomendaciones.append("📈 La tasa de apertura es aceptable (20-40%). Prueba con asuntos más personalizados.")
    else:
        recomendaciones.append("✅ Excelente tasa de apertura (>40%). Tus asuntos están funcionando bien.")

    if click_rate < 5:
        recomendaciones.append("⚠️ La tasa de clics es baja (<5%). Revisa los enlaces y el CTA en tus correos.")
    elif click_rate < 15:
        recomendaciones.append("📈 La tasa de clics es aceptable (5-15%). Considera mejorar la visibilidad de los enlaces.")
    else:
        recomendaciones.append("✅ Excelente tasa de clics (>15%). Tus CTAs están generando interacción.")

    if response_rate < 2:
        recomendaciones.append("⚠️ La tasa de respuesta es baja (<2%). Personaliza más los mensajes.")
    elif response_rate < 5:
        recomendaciones.append("📈 La tasa de respuesta es aceptable (2-5%). Continúa mejorando la personalización.")
    else:
        recomendaciones.append("✅ Excelente tasa de respuesta (>5%). Tus mensajes están conectando con el público.")

    if 'transporte' in str(industrias).lower() or 'logística' in str(industrias).lower():
        recomendaciones.append("📊 El sector transporte/logística tiene alto potencial. Enfoca mensajes en control de combustible y rutas.")
    if 'construcción' in str(industrias).lower():
        recomendaciones.append("🏗️ Para el sector construcción, destaca la videotelemática para seguridad en obra.")
    if 'comercio' in str(industrias).lower():
        recomendaciones.append("🛒 Para el sector comercio, enfoca en control de inventarios y logística de distribución.")

    if len(top_campaigns) > 0:
        mejor = top_campaigns[0]
        recomendaciones.append(f"🏆 Tu mejor campaña es '{mejor['name']}' con {mejor['open_rate']}% de apertura. Analiza qué hizo que funcionara.")

    return {
        'total_campaigns': total_campaigns,
        'total_contacts': total_contacts,
        'total_sent': total_sent,
        'total_opens': total_opens,
        'total_clicks': total_clicks,
        'total_responses': total_responses,
        'open_rate': open_rate,
        'click_rate': click_rate,
        'response_rate': response_rate,
        'top_campaigns': top_campaigns,
        'industrias': industrias,
        'scoring_analysis': scoring_analysis,
        'keyword_performance': keyword_performance,
        'recomendaciones': recomendaciones,
        'fecha_analisis': datetime.now()
    }

def registrar_costo(tipo, lead_id=None, campaign_id=None, tokens_in=0, tokens_out=0, costo=0.0):
    log = CostLog(
        type=tipo,
        lead_id=lead_id,
        campaign_id=campaign_id,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost=costo
    )
    db.session.add(log)
    db.session.commit()
    return log

def generar_recomendaciones():
    recomendaciones = []

    total_sent = Contact.query.filter(Contact.sent_at.isnot(None)).count()
    total_opens = Event.query.filter_by(type='open').count()
    open_rate = round((total_opens / total_sent * 100) if total_sent else 0, 1)

    if open_rate < 20:
        recomendaciones.append({
            'tipo': 'apertura',
            'nivel': 'critico',
            'mensaje': '⚠️ Tasa de apertura baja (<20%). Sugerencia: Prueba con asuntos más personalizados, incluye el nombre de la empresa o una pregunta que genere curiosidad.',
            'accion': 'Revisar asuntos y horarios de envío'
        })
    elif open_rate < 40:
        recomendaciones.append({
            'tipo': 'apertura',
            'nivel': 'medio',
            'mensaje': '📈 Tasa de apertura aceptable (20-40%). Sugerencia: Mejora la segmentación y prueba con horarios de envío diferentes (ej. martes y jueves por la mañana).',
            'accion': 'Segmentar leads y ajustar horarios'
        })
    else:
        recomendaciones.append({
            'tipo': 'apertura',
            'nivel': 'excelente',
            'mensaje': '✅ Excelente tasa de apertura (>40%). Tus asuntos están funcionando bien. Replica la estrategia en futuras campañas.',
            'accion': 'Mantener estrategia actual'
        })

    total_clicks = Event.query.filter_by(type='click').count()
    click_rate = round((total_clicks / total_opens * 100) if total_opens else 0, 1)

    if click_rate < 5:
        recomendaciones.append({
            'tipo': 'clics',
            'nivel': 'critico',
            'mensaje': '⚠️ Tasa de clics baja (<5%). Sugerencia: Asegúrate de que los enlaces sean visibles y el CTA sea claro. Usa botones con colores contrastantes.',
            'accion': 'Mejorar CTAs y diseño de enlaces'
        })
    elif click_rate < 15:
        recomendaciones.append({
            'tipo': 'clics',
            'nivel': 'medio',
            'mensaje': '📈 Tasa de clics aceptable (5-15%). Sugerencia: Añade más de un enlace relevante y utiliza textos como "Descargar PDF" o "Ver más".',
            'accion': 'Optimizar enlaces y CTAs'
        })
    else:
        recomendaciones.append({
            'tipo': 'clics',
            'nivel': 'excelente',
            'mensaje': '✅ Excelente tasa de clics (>15%). Tus CTAs están generando interacción. Asegúrate de que el contenido sea relevante.',
            'accion': 'Mantener estrategia actual'
        })

    total_responses = Event.query.filter_by(type='reply').count()
    response_rate = round((total_responses / total_sent * 100) if total_sent else 0, 1)

    if response_rate < 2:
        recomendaciones.append({
            'tipo': 'respuesta',
            'nivel': 'critico',
            'mensaje': '⚠️ Tasa de respuesta baja (<2%). Sugerencia: Personaliza más el contenido, haz preguntas abiertas y ofrece valor específico para cada sector.',
            'accion': 'Personalizar mensajes y segmentar mejor'
        })
    elif response_rate < 5:
        recomendaciones.append({
            'tipo': 'respuesta',
            'nivel': 'medio',
            'mensaje': '📈 Tasa de respuesta aceptable (2-5%). Sugerencia: Sigue personalizando y prueba con diferentes tipos de CTA (ej. "¿Te gustaría una demo?").',
            'accion': 'Mejorar personalización y CTAs'
        })
    else:
        recomendaciones.append({
            'tipo': 'respuesta',
            'nivel': 'excelente',
            'mensaje': '✅ Excelente tasa de respuesta (>5%). Tus mensajes están conectando con el público. Documenta lo que está funcionando.',
            'accion': 'Documentar estrategias exitosas'
        })

    industrias = {}
    leads = Lead.query.filter(Lead.actividad.isnot(None)).all()
    for lead in leads:
        ind = lead.actividad[:20]
        industrias[ind] = industrias.get(ind, 0) + 1

    if industrias:
        top_industria = max(industrias, key=industrias.get)
        recomendaciones.append({
            'tipo': 'industria',
            'nivel': 'informacion',
            'mensaje': f'📊 Tu principal industria es "{top_industria}" ({industrias[top_industria]} leads). Enfoca tus mensajes en los desafíos específicos de este sector.',
            'accion': 'Crear contenido especializado para esta industria'
        })

    if total_clicks > 10:
        recomendaciones.append({
            'tipo': 'palabras_clave',
            'nivel': 'informacion',
            'mensaje': '🔑 Las palabras clave como "control", "combustible", "flotilla" suelen tener buen rendimiento. Considera incluirlas en tus asuntos y contenido.',
            'accion': 'Optimizar contenido con palabras clave efectivas'
        })

    campaigns = Campaign.query.filter(Campaign.sent_at.isnot(None)).all()
    if campaigns:
        best_campaign = None
        best_open_rate = 0
        for camp in campaigns:
            contacts = Contact.query.filter_by(campaign_id=camp.id).all()
            sent = sum(1 for c in contacts if c.sent_at)
            opened = sum(1 for c in contacts if c.opened_at)
            if sent > 0:
                rate = round((opened/sent*100), 1)
                if rate > best_open_rate:
                    best_open_rate = rate
                    best_campaign = camp.name
        if best_campaign:
            recomendaciones.append({
                'tipo': 'campaña',
                'nivel': 'informacion',
                'mensaje': f'🏆 La campaña "{best_campaign}" tiene la mejor tasa de apertura ({best_open_rate}%). Analiza qué hizo que funcionara (asunto, contenido, segmentación).',
                'accion': 'Replicar estrategia de la campaña ganadora'
            })

    return recomendaciones

# ===== RUTAS =====

# ===== RUTA GENERADOR (CORREGIDA) =====
@app.route('/generador')
def generador():
    leads_disponibles = Lead.query.order_by(Lead.score_puntaje.desc()).all()
    print(f"🔍 Leads disponibles en generador: {len(leads_disponibles)}")
    return render_template('generador.html', leads=leads_disponibles, now=datetime.now())

@app.route('/')
def index():
    total_companies = Lead.query.count()
    total_sent = Contact.query.filter(Contact.sent_at.isnot(None)).count()
    total_opens = Event.query.filter_by(type='open').count()
    total_clicks = Event.query.filter_by(type='click').count()
    total_pdf_opens = Event.query.filter_by(type='pdf_open').count()
    total_whatsapp = Event.query.filter_by(type='whatsapp_click').count()
    total_responses = Event.query.filter_by(type='reply').count()
    total_meetings = 0
    total_quotations = 0
    total_sales = 0
    roi = 0

    horario_data = [{'hora':'6 am','porcentaje':100},{'hora':'8 am','porcentaje':85},{'hora':'10 am','porcentaje':52},{'hora':'12 pm','porcentaje':22}]
    horario_data_json = {'labels': [h['hora'] for h in horario_data], 'values': [h['porcentaje'] for h in horario_data]}

    top_campaigns = []
    estrategias = [{'nombre':'Evidencia ante incidentes','apertura':79,'respuesta':26,'conversion':8.6},
                   {'nombre':'Control de combustible','apertura':68,'respuesta':21,'conversion':7.2}]
    clasificaciones = [{'label':'Interesado','count':15,'percent':36.6},{'label':'Más información','count':11,'percent':26.8}]
    total_respuestas = 26
    actividad_reciente = [{'icono':'fa-envelope-open-text','titulo':'Apertura','descripcion':'Transportes OROMAR','tiempo':'Hace 12 min'}]
    top_datos = {'mejor_respuesta':2.5,'mejor_respuesta_industria':'Transporte','mejor_conversion':0.71,'mejor_conversion_industria':'Transporte','costo_ia_promedio':0.42,'roi_promedio':3.7,'mejor_apertura':62.4,'mejor_apertura_industria':'Industria','horarios':[{'hora':'6 am','porcentaje':100},{'hora':'8 am','porcentaje':85}]}

    stats = {
        'total_companies': total_companies,
        'total_sent': total_sent,
        'total_opens': total_opens,
        'total_clicks': total_clicks,
        'total_pdf_downloads': total_pdf_opens,
        'total_whatsapp': total_whatsapp,
        'total_responses': total_responses,
        'total_meetings': total_meetings,
        'total_quotations': total_quotations,
        'total_sales': total_sales,
        'roi': roi,
        'percent_sent': round((total_sent/total_companies*100) if total_companies else 0,1),
        'percent_open': round((total_opens/total_sent*100) if total_sent else 0,1),
        'percent_pdf': round((total_pdf_opens/total_opens*100) if total_opens else 0,1),
        'percent_whatsapp': round((total_whatsapp/total_opens*100) if total_opens else 0,1),
        'percent_response': round((total_responses/total_opens*100) if total_opens else 0,1),
        'percent_meeting': 0,
        'percent_sale': 0,
    }
    return render_template('index.html', stats=stats, horario_data=horario_data, horario_data_json=horario_data_json, top_campaigns=top_campaigns, estrategias=estrategias, clasificaciones=clasificaciones, total_respuestas=total_respuestas, actividad_reciente=actividad_reciente, top_datos=top_datos, now=datetime.now())

@app.route('/leads')
def leads():
    total_leads = Lead.query.count()
    leads_scoring = {s: Lead.query.filter_by(scoring=s).count() for s in ['A','B','C','D']}
    leads_analizados = Lead.query.filter(Lead.analyzed_at.isnot(None)).count()
    leads_list = Lead.query.order_by(Lead.score_puntaje.desc()).all()
    return render_template('leads.html', total_leads=total_leads, leads_scoring=leads_scoring, leads_analizados=leads_analizados, leads=leads_list, now=datetime.now())

@app.route('/leads/importar', methods=['GET','POST'])
def importar_leads():
    if request.method == 'POST':
        if 'archivo' not in request.files:
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(url_for('importar_leads'))
        archivo = request.files['archivo']
        if archivo.filename == '':
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(url_for('importar_leads'))
        if not archivo.filename.endswith('.csv'):
            flash('Solo se permiten archivos CSV', 'danger')
            return redirect(url_for('importar_leads'))
        temp_path = os.path.join('/tmp', archivo.filename)
        archivo.save(temp_path)
        try:
            total = importar_csv_leads(temp_path)
            flash(f'✅ Se importaron {total} leads correctamente', 'success')
        except Exception as e:
            flash(f'❌ Error al importar: {str(e)}', 'danger')
        finally:
            os.remove(temp_path)
        return redirect(url_for('leads'))
    return render_template('importar_leads.html', now=datetime.now())

@app.route('/leads/api/listar')
def api_listar_leads():
    scoring = request.args.get('scoring', '')
    estado = request.args.get('estado', '')
    search = request.args.get('search', '')
    query = Lead.query
    if scoring: query = query.filter_by(scoring=scoring)
    if estado == 'analizados': query = query.filter(Lead.analyzed_at.isnot(None))
    elif estado == 'pendientes': query = query.filter(Lead.analyzed_at.is_(None))
    if search:
        query = query.filter(db.or_(Lead.nombre.ilike(f'%{search}%'), Lead.razon_social.ilike(f'%{search}%'), Lead.actividad.ilike(f'%{search}%'), Lead.correo.ilike(f'%{search}%')))
    leads = query.order_by(Lead.score_puntaje.desc()).all()
    return jsonify([{
        'id': l.id,
        'nombre': l.nombre,
        'razon_social': l.razon_social,
        'actividad': l.actividad,
        'scoring': l.scoring,
        'score_puntaje': l.score_puntaje,
        'correo': l.correo,
        'prioridad': l.prioridad,
        'analyzed': l.analyzed_at is not None,
        'insight': l.insight[:100] + '...' if l.insight else ''
    } for l in leads])

@app.route('/leads/<int:lead_id>')
def ver_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    return render_template('ver_lead.html', lead=lead, now=datetime.now())

@app.route('/leads/<int:lead_id>/analizar', methods=['POST'])
def analizar_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    resultado = analizar_con_ia(lead)
    lead.insight = resultado['insight']
    lead.riesgos = resultado['riesgos']
    lead.oportunidades = resultado['oportunidades']
    lead.soluciones = resultado['soluciones']
    lead.prioridad = resultado['prioridad']
    lead.analyzed_at = datetime.utcnow()
    db.session.commit()
    flash('✅ Lead analizado correctamente', 'success')
    return redirect(url_for('ver_lead', lead_id=lead_id))

@app.route('/leads/analizar-todos', methods=['POST'])
def analizar_todos_leads():
    leads_pendientes = Lead.query.filter(Lead.analyzed_at.is_(None)).all()
    for lead in leads_pendientes:
        resultado = analizar_con_ia(lead)
        lead.insight = resultado['insight']
        lead.riesgos = resultado['riesgos']
        lead.oportunidades = resultado['oportunidades']
        lead.soluciones = resultado['soluciones']
        lead.prioridad = resultado['prioridad']
        lead.analyzed_at = datetime.utcnow()
    db.session.commit()
    flash(f'✅ Se analizaron {len(leads_pendientes)} leads correctamente', 'success')
    return redirect(url_for('leads'))

@app.route('/analisis')
def analisis():
    total_leads = Lead.query.count()
    total_analizados = Lead.query.filter(Lead.analyzed_at.isnot(None)).count()
    total_pendientes = Lead.query.filter(Lead.analyzed_at.is_(None)).count()
    leads_scoring = {s: Lead.query.filter_by(scoring=s).count() for s in ['A','B','C','D']}
    leads_por_prioridad = {p: Lead.query.filter_by(prioridad=p).count() for p in [1,2,3,4,5]}
    leads_analizados_list = Lead.query.filter(Lead.analyzed_at.isnot(None)).order_by(Lead.prioridad.desc(), Lead.score_puntaje.desc()).all()
    avg = db.session.query(db.func.avg(Lead.prioridad)).filter(Lead.analyzed_at.isnot(None)).scalar() or 0.0
    return render_template('analisis.html',
                           total_leads=total_leads,
                           total_analizados=total_analizados,
                           total_pendientes=total_pendientes,
                           leads_scoring=leads_scoring,
                           leads_por_prioridad=leads_por_prioridad,
                           leads_analizados_list=leads_analizados_list,
                           promedio_prioridad=float(avg),
                           now=datetime.now())


@app.route('/generador/generar', methods=['POST'])
def generar_correo():
    lead_id = request.form.get('lead_id')
    if not lead_id:
        flash('Selecciona un lead', 'warning')
        return redirect(url_for('generador'))

    lead = Lead.query.get_or_404(lead_id)
    nombre = lead.nombre or lead.razon_social or 'Cliente'
    actividad = lead.actividad or 'empresa'
    personal = lead.personal or 'No especificado'
    municipio = lead.municipio or ''
    estado = lead.estado or ''

    asunto, html, texto_completo = generar_correo_completo(nombre, actividad, personal, municipio, estado)
    if not asunto:
        flash('Error al generar el correo', 'danger')
        return redirect(url_for('generador'))

    resultado = {
        'asuntos': [asunto],
        'cuerpo': html,
        'tokens_entrada': 150,
        'tokens_salida': 250,
        'costo': 0.0007
    }

    return render_template('generador_resultado.html',
                           lead=lead,
                           resultado=resultado,
                           now=datetime.now())

@app.route('/generador/masivo', methods=['POST'])
def generar_masivo():
    scoring = request.form.get('scoring', '')
    limite = int(request.form.get('limite', 10))
    query = Lead.query.filter(Lead.analyzed_at.isnot(None))
    if scoring:
        query = query.filter_by(scoring=scoring)
    leads = query.order_by(Lead.prioridad.desc()).limit(limite).all()
    resultados = []
    for lead in leads:
        nombre = lead.nombre or lead.razon_social or 'Cliente'
        actividad = lead.actividad or 'empresa'
        personal = lead.personal or 'No especificado'
        municipio = lead.municipio or ''
        estado = lead.estado or ''
        asunto, html, _ = generar_correo_completo(nombre, actividad, personal, municipio, estado)
        if asunto:
            resultados.append({
                'lead': lead,
                'asuntos': [asunto],
                'cuerpo': html,
                'costo': 0.0007
            })
    return render_template('generador_masivo.html', resultados=resultados, now=datetime.now())

@app.route('/campaigns')
def campaigns():
    campaigns_list = Campaign.query.order_by(Campaign.created_at.desc()).all()
    return render_template('campaigns.html', campaigns=campaigns_list, now=datetime.now())

@app.route('/campaigns/new', methods=['GET','POST'])
def campaign_new():
    if request.method == 'POST':
        name = request.form.get('name')
        subject = request.form.get('subject')
        body_html = request.form.get('body_html')
        sender_email = request.form.get('sender_email')
        sender_name = request.form.get('sender_name')
        lead_ids = request.form.getlist('lead_ids')
        if not name or not subject or not body_html or not lead_ids:
            flash('Todos los campos son obligatorios y debes seleccionar al menos un lead', 'danger')
            return redirect(url_for('campaign_new'))
        campaign = Campaign(
            name=name,
            subject=subject,
            body_html=body_html,
            sender_email=sender_email or get_smtp_config()['default_sender_email'],
            sender_name=sender_name or get_smtp_config()['default_sender_name'],
            status='draft'
        )
        db.session.add(campaign)
        db.session.commit()
        for lead_id in lead_ids:
            lead = Lead.query.get(lead_id)
            if lead and lead.correo:
                contact = Contact(
                    email=lead.correo,
                    name=lead.nombre or lead.razon_social,
                    giro=lead.actividad,
                    descripcion=lead.insight,
                    campaign_id=campaign.id,
                    status='pending'
                )
                db.session.add(contact)
        campaign.total_contacts = len(lead_ids)
        db.session.commit()
        flash(f'✅ Campaña "{name}" creada con {len(lead_ids)} contactos', 'success')
        return redirect(url_for('campaign_stats', campaign_id=campaign.id))
    leads = Lead.query.filter(Lead.correo.isnot(None)).order_by(Lead.score_puntaje.desc()).all()
    config = get_smtp_config()
    return render_template('campaign_form.html', leads=leads, config=config, now=datetime.now())

@app.route('/campaigns/<int:campaign_id>')
def campaign_stats(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    contacts = Contact.query.filter_by(campaign_id=campaign_id).all()
    total = len(contacts)
    sent = sum(1 for c in contacts if c.sent_at)
    opened = sum(1 for c in contacts if c.opened_at)
    clicked = sum(1 for c in contacts if c.clicked_at)
    bounced = sum(1 for c in contacts if c.bounced)
    open_rate = round((opened / sent * 100) if sent else 0, 1)
    click_rate = round((clicked / opened * 100) if opened else 0, 1)
    bounce_rate = round((bounced / sent * 100) if sent else 0, 1)
    return render_template('campaign_stats.html',
                           campaign=campaign,
                           contacts=contacts,
                           total=total,
                           sent=sent,
                           opened=opened,
                           clicked=clicked,
                           bounced=bounced,
                           open_rate=open_rate,
                           click_rate=click_rate,
                           bounce_rate=bounce_rate,
                           now=datetime.now())

@app.route('/campaigns/<int:campaign_id>/send', methods=['POST'])
def campaign_send(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    contacts = Contact.query.filter_by(campaign_id=campaign_id, status='pending').all()
    if not contacts:
        flash('No hay contactos pendientes para enviar', 'warning')
        return redirect(url_for('campaign_stats', campaign_id=campaign_id))
    enviados = 0
    fallidos = 0
    for contact in contacts:
        if enviar_correo_campaign(contact, campaign, campaign.body_html, campaign.subject):
            enviados += 1
        else:
            fallidos += 1
    campaign.sent_at = datetime.utcnow()
    campaign.status = 'sent'
    db.session.commit()
    flash(f'✅ Enviados: {enviados} | ❌ Fallidos: {fallidos}', 'success')
    return redirect(url_for('campaign_stats', campaign_id=campaign_id))

@app.route('/campaigns/<int:campaign_id>/delete', methods=['POST'])
def campaign_delete(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    Contact.query.filter_by(campaign_id=campaign_id).delete()
    db.session.delete(campaign)
    db.session.commit()
    flash('Campaña eliminada correctamente', 'success')
    return redirect(url_for('campaigns'))

@app.route('/track/pixel/<token>')
def track_pixel(token):
    try:
        t = TrackingToken.query.filter_by(token=token).first()
        if t:
            contact = Contact.query.get(t.contact_id)
            if contact and not contact.opened_at:
                contact.opened_at = datetime.utcnow()
                event = Event(contact_id=contact.id, type='open')
                db.session.add(event)
                db.session.commit()
    except Exception as e:
        print(f"Error tracking pixel: {e}")
    pixel = base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')
    return pixel, 200, {'Content-Type': 'image/gif'}

@app.route('/track/click/<token>')
def track_click(token):
    try:
        t = TrackingToken.query.filter_by(token=token).first()
        if t:
            contact = Contact.query.get(t.contact_id)
            if contact and not contact.clicked_at:
                contact.clicked_at = datetime.utcnow()
                event = Event(contact_id=contact.id, type='click')
                db.session.add(event)
                db.session.commit()
    except Exception as e:
        print(f"Error tracking click: {e}")
    url = request.args.get('url', '/')
    return redirect(url)

@app.route('/track/pdf/<token>')
def track_pdf(token):
    try:
        t = TrackingToken.query.filter_by(token=token).first()
        if t:
            contact = Contact.query.get(t.contact_id)
            if contact:
                event = Event(contact_id=contact.id, type='pdf_open')
                db.session.add(event)
                db.session.commit()
    except Exception as e:
        print(f"Error tracking pdf: {e}")
    return redirect('https://inspol.com.mx/static/INSPOL_Soluciones.pdf')

@app.route('/track/whatsapp/<token>')
def track_whatsapp(token):
    try:
        t = TrackingToken.query.filter_by(token=token).first()
        if t:
            contact = Contact.query.get(t.contact_id)
            if contact:
                event = Event(contact_id=contact.id, type='whatsapp_click')
                db.session.add(event)
                db.session.commit()
    except Exception as e:
        print(f"Error tracking whatsapp: {e}")
    return redirect('https://wa.me/5623682625?text=Hola%20INSPOL%2C%20vi%20su%20correo')

@app.route('/tracking')
def tracking():
    total_pdf_opens = Event.query.filter_by(type='pdf_open').count()
    total_whatsapp_clicks = Event.query.filter_by(type='whatsapp_click').count()
    total_replies = Event.query.filter_by(type='reply').count()
    total_opens = Event.query.filter_by(type='open').count()
    total_clicks = Event.query.filter_by(type='click').count()
    eventos_recientes = Event.query.order_by(Event.created_at.desc()).limit(20).all()
    eventos_por_tipo = db.session.query(Event.type, db.func.count(Event.id)).group_by(Event.type).all()
    return render_template('tracking.html',
                           total_pdf_opens=total_pdf_opens,
                           total_whatsapp_clicks=total_whatsapp_clicks,
                           total_replies=total_replies,
                           total_opens=total_opens,
                           total_clicks=total_clicks,
                           eventos_recientes=eventos_recientes,
                           eventos_por_tipo=eventos_por_tipo,
                           now=datetime.now())

@app.route('/analisis-resultados')
def analisis_resultados():
    data = analizar_rendimiento()
    respuestas = [
        {'texto': 'Me interesa, quiero más información sobre GPS', 'clasificacion': 'Interesado'},
        {'texto': '¿Cuál es el costo de la solución de videotelemática?', 'clasificacion': 'Cotización'},
        {'texto': '¿Pueden darme una demo de la plataforma?', 'clasificacion': 'Más información'},
        {'texto': 'No estoy interesado por ahora, gracias', 'clasificacion': 'No interesado'},
        {'texto': 'Me gustaría agendar una reunión para conocer más', 'clasificacion': 'Reunión'}
    ]
    return render_template('analisis_resultados.html',
                           data=data,
                           respuestas=respuestas,
                           now=datetime.now())

@app.route('/costos')
def costos():
    total_cost = db.session.query(db.func.sum(CostLog.cost)).scalar() or 0.0
    total_tokens_in = db.session.query(db.func.sum(CostLog.tokens_in)).scalar() or 0
    total_tokens_out = db.session.query(db.func.sum(CostLog.tokens_out)).scalar() or 0

    cost_por_tipo = db.session.query(
        CostLog.type,
        db.func.sum(CostLog.cost).label('total'),
        db.func.count(CostLog.id).label('count')
    ).group_by(CostLog.type).all()

    cost_por_campaign = db.session.query(
        Campaign.name,
        db.func.sum(CostLog.cost).label('total')
    ).join(CostLog, CostLog.campaign_id == Campaign.id).group_by(Campaign.id).all()

    fecha_inicio = datetime.utcnow() - timedelta(days=30)
    daily_costs = db.session.query(
        db.func.date(CostLog.created_at).label('day'),
        db.func.sum(CostLog.cost).label('total')
    ).filter(CostLog.created_at >= fecha_inicio)\
     .group_by(db.func.date(CostLog.created_at)).order_by('day').all()

    cost_por_lead = db.session.query(
        Lead.nombre,
        Lead.razon_social,
        db.func.sum(CostLog.cost).label('total')
    ).join(CostLog, CostLog.lead_id == Lead.id).group_by(Lead.id)\
     .order_by(db.func.sum(CostLog.cost).desc()).limit(5).all()

    return render_template('costos.html',
                           total_cost=total_cost,
                           total_tokens_in=total_tokens_in,
                           total_tokens_out=total_tokens_out,
                           cost_por_tipo=cost_por_tipo,
                           cost_por_campaign=cost_por_campaign,
                           daily_costs=daily_costs,
                           cost_por_lead=cost_por_lead,
                           now=datetime.now())

@app.route('/funnel')
def funnel():
    total_leads = Lead.query.count()
    total_analizados = Lead.query.filter(Lead.analyzed_at.isnot(None)).count()
    total_contactos = Contact.query.count()
    total_enviados = Contact.query.filter(Contact.sent_at.isnot(None)).count()
    total_aperturas = Event.query.filter_by(type='open').count()
    total_clicks = Event.query.filter_by(type='click').count()
    total_pdf_opens = Event.query.filter_by(type='pdf_open').count()
    total_whatsapp_clicks = Event.query.filter_by(type='whatsapp_click').count()
    total_respuestas = Event.query.filter_by(type='reply').count()

    conversion_analisis = round((total_analizados / total_leads * 100) if total_leads else 0, 1)
    conversion_contacto = round((total_contactos / total_analizados * 100) if total_analizados else 0, 1)
    conversion_envio = round((total_enviados / total_contactos * 100) if total_contactos else 0, 1)
    conversion_apertura = round((total_aperturas / total_enviados * 100) if total_enviados else 0, 1)
    conversion_click = round((total_clicks / total_aperturas * 100) if total_aperturas else 0, 1)
    conversion_pdf = round((total_pdf_opens / total_aperturas * 100) if total_aperturas else 0, 1)
    conversion_whatsapp = round((total_whatsapp_clicks / total_aperturas * 100) if total_aperturas else 0, 1)
    conversion_respuesta = round((total_respuestas / total_aperturas * 100) if total_aperturas else 0, 1)

    funnel_data = [
        {'etapa': 'Leads Analizados', 'valor': total_analizados},
        {'etapa': 'Contactos', 'valor': total_contactos},
        {'etapa': 'Correos Enviados', 'valor': total_enviados},
        {'etapa': 'Aperturas', 'valor': total_aperturas},
        {'etapa': 'Clics', 'valor': total_clicks},
        {'etapa': 'PDF Abiertos', 'valor': total_pdf_opens},
        {'etapa': 'WhatsApp', 'valor': total_whatsapp_clicks},
        {'etapa': 'Respuestas', 'valor': total_respuestas}
    ]

    return render_template('funnel.html',
                           total_leads=total_leads,
                           total_analizados=total_analizados,
                           total_contactos=total_contactos,
                           total_enviados=total_enviados,
                           total_aperturas=total_aperturas,
                           total_clicks=total_clicks,
                           total_pdf_opens=total_pdf_opens,
                           total_whatsapp_clicks=total_whatsapp_clicks,
                           total_respuestas=total_respuestas,
                           conversion_analisis=conversion_analisis,
                           conversion_contacto=conversion_contacto,
                           conversion_envio=conversion_envio,
                           conversion_apertura=conversion_apertura,
                           conversion_click=conversion_click,
                           conversion_pdf=conversion_pdf,
                           conversion_whatsapp=conversion_whatsapp,
                           conversion_respuesta=conversion_respuesta,
                           funnel_data=funnel_data,
                           now=datetime.now())

@app.route('/recomendaciones')
def recomendaciones():
    recomendaciones = generar_recomendaciones()
    return render_template('recomendaciones.html',
                           recomendaciones=recomendaciones,
                           now=datetime.now())

@app.route('/configuracion', methods=['GET', 'POST'])
def configuracion():
    config_file = 'config_user.json'
    config_data = get_smtp_config()

    if request.method == 'POST':
        new_config = {
            'smtp_host': request.form.get('smtp_host', 'mail.inspol.com.mx'),
            'smtp_port': int(request.form.get('smtp_port', 587)),
            'smtp_user': request.form.get('smtp_user', 'ventas@inspol.com.mx'),
            'smtp_password': request.form.get('smtp_password', ''),
            'default_sender_name': request.form.get('default_sender_name', 'INSPOL México'),
            'default_sender_email': request.form.get('default_sender_email', 'ventas@inspol.com.mx')
        }
        try:
            with open(config_file, 'w') as f:
                json.dump(new_config, f, indent=4)
            flash('✅ Configuración guardada correctamente', 'success')
            config_data = new_config
        except Exception as e:
            flash(f'❌ Error al guardar configuración: {str(e)}', 'danger')

    return render_template('configuracion.html',
                           config_data=config_data,
                           now=datetime.now())


@app.route('/leads/<int:lead_id>/enviar-prueba', methods=['POST'])
def enviar_prueba(lead_id):
    from ai_utils import generar_correo_completo
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    lead = Lead.query.get_or_404(lead_id)
    email_destino = request.form.get('email_destino', lead.correo)
    if not email_destino:
        flash('Debes especificar un correo destino', 'danger')
        return redirect(url_for('ver_lead', lead_id=lead_id))

    nombre = lead.nombre or lead.razon_social or 'Cliente'
    actividad = lead.actividad or 'empresa'
    personal = lead.personal or 'No especificado'
    municipio = lead.municipio or ''
    estado = lead.estado or ''

    asunto, html, texto_completo = generar_correo_completo(nombre, actividad, personal, municipio, estado)
    if not asunto:
        flash('Error al generar el correo', 'danger')
        return redirect(url_for('ver_lead', lead_id=lead_id))

    config = get_smtp_config()
    try:
        msg = MIMEMultipart()
        msg["From"] = config['default_sender_email']
        msg["To"] = email_destino
        msg["Subject"] = asunto
        msg.attach(MIMEText(html, "html"))
        server = smtplib.SMTP(config['smtp_host'], config['smtp_port'])
        server.starttls()
        server.login(config['smtp_user'], config['smtp_password'])
        server.sendmail(config['default_sender_email'], email_destino, msg.as_string())
        server.quit()
        flash(f'✅ Correo de prueba enviado a {email_destino}', 'success')
        return redirect(url_for('ver_lead', lead_id=lead_id))  # <-- AÑADIDO (crucial)
    except Exception as e:
        flash(f'❌ Error al enviar: {str(e)}', 'danger')
        import traceback
        traceback.print_exc()
        return redirect(url_for('ver_lead', lead_id=lead_id))
