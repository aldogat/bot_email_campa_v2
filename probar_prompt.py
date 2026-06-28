#!/usr/bin/env python3
import csv
from ai_utils import generar_propuesta

# Leer el CSV
with open('prueba_prompt_avanzado.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    contact = list(reader)[0]

nombre = contact['Nombre de la Unidad Económica']
giro = contact['giro']
descripcion = contact['descripcion']

print("=" * 80)
print("📧 GENERANDO CORREO PERSONALIZADO CON EL NUEVO PROMPT")
print("=" * 80)
print(f"Empresa: {nombre}")
print(f"Giro: {giro}")
print(f"Descripción: {descripcion}")
print("-" * 80)

# Generar propuesta con IA
propuesta = generar_propuesta(nombre, giro, descripcion)

# Mostrar el resultado
print("\n📝 CORREO GENERADO:\n")
print(propuesta)
print("\n" + "=" * 80)
print("✅ El correo se ha generado. Revisa si cumple con todas las instrucciones.")
print("Si te gusta, puedes usarlo en una campaña real.")
