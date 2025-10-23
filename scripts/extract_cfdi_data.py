import os
from PyPDF2 import PdfReader
import csv

# Directorios a buscar
base_dirs = [
    '1_Evidencia_Cronologica/2025/10_Octubre/20251021/recibos de nomina',
    '1_Evidencia_Cronologica/2025/10_Octubre/20251021/finiquito'
]

output_csv = 'cfdi_extract.csv'

rows = []
for base in base_dirs:
    full_base = os.path.join(os.path.dirname(__file__), '..', base)
    for fname in os.listdir(full_base):
        if fname.endswith('.pdf') and fname.startswith('cfdi_'):
            fpath = os.path.join(full_base, fname)
            try:
                reader = PdfReader(fpath)
                text = ''
                for page in reader.pages:
                    text += page.extract_text() or ''
                # Buscar monto y fecha
                # Ejemplo: buscar $ y fecha tipo 2025-xx-xx o similar
                import re
                monto_match = re.search(r'\$\s?([\d,]+\.\d{2})', text)
                fecha_match = re.search(r'(20\d{2}[-/]\d{2}[-/]\d{2})', text)
                monto = monto_match.group(1) if monto_match else ''
                fecha = fecha_match.group(1) if fecha_match else ''
                rows.append({
                    'archivo': fname,
                    'ruta': fpath,
                    'fecha': fecha,
                    'monto': monto
                })
            except Exception as e:
                rows.append({
                    'archivo': fname,
                    'ruta': fpath,
                    'fecha': '',
                    'monto': '',
                    'error': str(e)
                })

with open(os.path.join(os.path.dirname(__file__), '..', output_csv), 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['archivo', 'ruta', 'fecha', 'monto', 'error'])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

print(f"Extracción completada. {len(rows)} archivos procesados. Resultados en {output_csv}")
