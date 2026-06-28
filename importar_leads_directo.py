from app import app, db, Lead, calcular_scoring, analizar_con_ia
from datetime import datetime

leads_raw = [
    ("PRIMERA PLUS", "PRIMERA PLUS", "Transporte colectivo foráneo de pasajeros de ruta fija", "31 a 50 personas", "Colima", "Colima", "3148027", "GFUNACOLIMA@PRIMERAPLUS.COM.MX", ""),
    ("PRIMERA PLUS", "PRIMERA PLUS", "Transporte colectivo foráneo de pasajeros de ruta fija", "0 a 5 personas", "Manzanillo", "Colima", "3336000014", "RHGUAD@PRIMERAPLUS.COM.MX", "WWW.PRIMERAPLUS.COM.MX"),
    ("PRIMERA PLUS Y FLECHA AMARILLA", "PRIMERA PLUS Y FLECHA AMARILLA", "Transporte colectivo foráneo de pasajeros de ruta fija", "31 a 50 personas", "Tecomán", "Colima", "", "WWW.PRIMERAPLUS.COM.MX", ""),
    ("QUALITY SHIP SUPPLIERS", "QUALITY SHIP SUPPLIERS", "Otros servicios relacionados con el transporte por agua", "0 a 5 personas", "Manzanillo", "Colima", "4437252795", "FACTURACION@CUALITYSHIPSUPPLIERS.COM", "WWW.QUALITYSHIPSUPPLIERS.COM"),
    ("REPRESENTACIONES MARITIMAS", "REPRESENTACIONES MARITIMAS", "Transporte marítimo de cabotaje", "11 a 30 personas", "Manzanillo", "Colima", "", "WWW.MARITIMEX.COM.MX", ""),
    ("REPRESENTACIONES MARITIMAS", "REPRESENTACIONES MARITIMAS", "Otros servicios de intermediación para el transporte de carga", "11 a 30 personas", "Manzanillo", "Colima", "", "VPENA@MARITIMEX.COM.MX", "WWW.MARITIMEX.COM.MX"),
    ("REPRESENTACIONES TRANSPACIFICAS TRANSPAC", "REPRESENTACIONES TRANSPACIFICAS TRANSPAC", "Transporte marítimo de altura", "11 a 30 personas", "Manzanillo", "Colima", "5527363658", "NAGUILAR@TRANSPAC.COM.MX", ""),
    ("SEAL LOGISTICS", "SEAL LOGISTICS", "Otros servicios de intermediación para el transporte de carga", "6 a 10 personas", "Manzanillo", "Colima", "", "OPERACIONES1@SEALLOGISTICS.COM.MX", ""),
    ("SERVICIOS COORDINADOS DE TRANSPORTE DE COLIMA", "SERVICIOS COORDINADOS DE TRANSPORTE DE COLIMA", "Transporte colectivo urbano y suburbano", "0 a 5 personas", "Manzanillo", "Colima", "", "GABO.36@HOTMAIL.COM", ""),
    ("SERVICIOS DE AUTOTRASPORTE COLIMA VILLA DE ALVREZ", "", "Transporte colectivo foráneo de pasajeros de ruta fija", "0 a 5 personas", "Colima", "Colima", "3123183203", "ELI_050506@HOTMAIL.COM", ""),
    ("SERVICIOS INTEGRALES MARITIMOS Y PORTUARIOS", "SERVICIOS INTEGRALES MARITIMOS Y PORTUARIOS", "Otros servicios relacionados con el transporte por agua", "51 a 100 personas", "Manzanillo", "Colima", "3141640163", "CONTABILIDAD@AMARRADORES.COM", "WWW.AMARRADORES.COM"),
    ("SOCIEDAD COOPERATIVA DE AUTOTRANSPORTE COLIMA-PUEBLO JUAREZ", "SOCIEDAD COOPERATIVA DE AUTOTRANSPORTE COLIMAPUEBLO JUAREZ", "Transporte colectivo urbano y suburbano", "11 a 30 personas", "Colima", "Colima", "", "SCATCOL@HOTMAIL.COM", ""),
    ("SOCIEDAD COOPERATIVA DE AUTOTRANSPORTE EL COLOMO SCL", "SOCIEDAD COOPERATIVA DE AUTOTRANSPORTE EL COLOMO", "Transporte colectivo urbano y suburbano", "11 a 30 personas", "El Colomo", "Colima", "", "SOC.COOP.ELCOLOMO@GMAIL.COM", ""),
    ("SOCIEDAD COOPERATIVA DE AUTOTRANSPORTES COLIMA VILLA DE ALVAREZ", "SOCIEDAD COOPERATIVA DE AUTOTRANSPORTES COLIMA VILLA DE ALVAREZ", "Transporte colectivo foráneo de pasajeros de ruta fija", "51 a 100 personas", "Colima", "Colima", "", "SOCACOVA.COLIMA1@GMAIL.COM", ""),
]

with app.app_context():
    # Limpiar leads existentes
    db.session.query(Lead).delete()
    db.session.commit()
    
    count = 0
    for nombre, razon_social, actividad, personal, municipio, estado, telefono, correo, sitio_web in leads_raw:
        lead = Lead(
            nombre=nombre,
            razon_social=razon_social,
            actividad=actividad,
            personal=personal,
            municipio=municipio,
            estado=estado,
            telefono=telefono,
            correo=correo,
            sitio_web=sitio_web,
            fecha_denue="2026"
        )
        scoring, puntaje = calcular_scoring(lead)
        lead.scoring = scoring
        lead.score_puntaje = puntaje
        resultado = analizar_con_ia(lead)
        lead.insight = resultado['insight']
        lead.riesgos = resultado['riesgos']
        lead.oportunidades = resultado['oportunidades']
        lead.soluciones = resultado['soluciones']
        lead.prioridad = resultado['prioridad']
        lead.analyzed_at = datetime.utcnow()
        db.session.add(lead)
        count += 1
    db.session.commit()
    print(f"✅ {count} leads importados y analizados correctamente")
