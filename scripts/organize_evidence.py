#!/usr/bin/env python3
"""Organiza archivos en 1_Evidencia_Cronologica por fecha en el nombre,
genera moves_map.tsv, renombra 0.Memoria.md a README.md y actualiza enlaces,
y crea la carpeta 2_Evidencia_Faltante_y_Tareas con plantillas.

Uso: python3 scripts/organize_evidence.py
"""
import re
import shutil
from pathlib import Path
from datetime import datetime
import sys
import csv

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / '1_Evidencia_Cronologica'
MISSING = ROOT / '2_Evidencia_Faltante_y_Tareas'
MAP_FILE = ROOT / 'moves_map.tsv'
MEMORIA = ROOT / '0.Memoria.md'
README = ROOT / 'README.md'

MONTHS_ES = [
    'Enero','Febrero','Marzo','Abril','Mayo','Junio',
    'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'
]

date_regexes = [
    re.compile(r"(19|20)\d{2}[- _]?\d{1,2}[- _]?\d{1,2}"),
    re.compile(r"\b(19|20)\d{6}\b"),
]

def find_date(s: str):
    s = s.replace('/', ' ')
    # try yyyy-mm-dd or similar
    m = re.search(r"(19|20)\d{2}[- _]?\d{1,2}[- _]?\d{1,2}", s)
    if m:
        token = m.group(0)
        digits = re.findall(r"\d+", token)
        if len(digits) >= 3:
            y = int(digits[0])
            mo = int(digits[1])
            return y, mo
        # fallback for 8-digit
    m2 = re.search(r"\b(19|20)(\d{2})(\d{2})(\d{2})\b", s)
    if m2:
        y = int(m2.group(1) + m2.group(2))
        mo = int(m2.group(3))
        return y, mo
    # 8-digit contiguous
    m3 = re.search(r"\b(19|20)\d{6}\b", s)
    if m3:
        token = m3.group(0)
        y = int(token[0:4]); mo = int(token[4:6]);
        return y, mo
    return None


def date_from_pdf(path: Path):
    try:
        from PyPDF2 import PdfReader
    except Exception:
        return None
    try:
        reader = PdfReader(str(path))
        info = reader.metadata
        # common keys: '/CreationDate' or 'CreationDate'
        date_str = None
        for k in ('/CreationDate', 'CreationDate', 'ModDate', '/ModDate'):
            if info and k in info:
                date_str = info[k]
                break
        if date_str:
            # try to parse formats like D:20240516...
            m = re.search(r"(19|20)\d{2}", date_str)
            if m:
                y = int(m.group(0))
                # try to get month
                mm = re.search(r"(19|20)\d{2}(\d{2})", date_str)
                if mm:
                    mo = int(mm.group(2))
                    return y, mo
                return y, 1
    except Exception:
        return None
    return None


def date_from_image(path: Path):
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
    except Exception:
        return None
    try:
        img = Image.open(str(path))
        exif = img._getexif()
        if not exif:
            return None
        for tag, val in exif.items():
            tagname = TAGS.get(tag, tag)
            if tagname in ('DateTime', 'DateTimeOriginal', 'DateTimeDigitized'):
                m = re.search(r"(19|20)\d{2}[:\-]?([01]\d)[:\-]?(\d{2})", str(val))
                if m:
                    y = int(m.group(0)[0:4])
                    mo = int(m.group(2))
                    return y, mo
    except Exception:
        return None
    return None


def month_folder(m: int):
    name = f"{m:02d}_{MONTHS_ES[m-1]}" if 1 <= m <= 12 else f"{m:02d}_Mes{m}"
    return name


def ensure_dirs(p: Path):
    if not p.exists():
        p.mkdir(parents=True, exist_ok=True)


def main():
    print(f"Root: {ROOT}")
    ensure_dirs(EVID)
    ensure_dirs(MISSING)

    moves = []

    # iterate top-level items (files and directories) in ROOT
    for item in sorted(ROOT.iterdir()):
        if item.name in ('scripts', '1_Evidencia_Cronologica', '2_Evidencia_Faltante_y_Tareas', 'moves_map.tsv', 'README.md', '0.Memoria.md'):
            continue
        if item.name.startswith('.'):
            continue

        # Only consider items in root (files and directories)
        if item == Path(__file__):
            continue

        # find date in name
        found = find_date(item.name)
        if found:
            y, mo = found
            year_dir = EVID / str(y)
            month_dir = year_dir / month_folder(mo)
            ensure_dirs(month_dir)
            dest = month_dir / item.name
        else:
            # no date -> put in 0000/00_Documentos_Fundamentales
            dest = EVID / '0000' / '00_Documentos_Fundamentales' / item.name
            ensure_dirs(dest.parent)

        # If destination exists, avoid overwrite by appending index
        final_dest = dest
        i = 1
        while final_dest.exists():
            final_dest = dest.with_name(f"{dest.stem}_{i}{dest.suffix}")
            i += 1

        print(f"Moving: {item.name} -> {final_dest.relative_to(ROOT)}")
        try:
            shutil.move(str(item), str(final_dest))
            moves.append((str(item.relative_to(ROOT)), str(final_dest.relative_to(ROOT))))
        except Exception as e:
            print(f"Failed to move {item}: {e}")

    # write moves_map.tsv
    # write moves_map.tsv (append if exists)
    write_header = not MAP_FILE.exists()
    with MAP_FILE.open('a', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        if write_header:
            w.writerow(['original','new'])
        for o,n in moves:
            w.writerow([o,n])

    print(f"Wrote map to {MAP_FILE}")

    # Rename 0.Memoria.md to README.md if exists
    if MEMORIA.exists():
        if README.exists():
            print("README.md already exists; backing up existing as README.old.md")
            (ROOT / 'README.old.md').write_bytes(README.read_bytes())
        MEMORIA.replace(README)
        print("Renombrado 0.Memoria.md -> README.md")

        # Update links in README based on moves
        text = README.read_text(encoding='utf-8')
        # For each moved file, replace bare filename occurrences with markdown links
        for o,n in moves:
            basename = Path(o).name
            newpath = './' + n.replace(' ', '%20')
            # Replace backtick code `filename` and plain filename occurrences
            # Try backtick first
            text = re.sub(rf"`{re.escape(basename)}`", f"[{basename}]({newpath})", text)
            # Replace occurrences like (Documento: filename) or - filename -
            text = re.sub(rf"(?<!\(|\[)\b{re.escape(basename)}\b(?!\))", f"[{basename}]({newpath})", text)

        README.write_text(text, encoding='utf-8')
        print("Actualizado README.md con enlaces relativos para archivos movidos")
    else:
        print("0.Memoria.md no encontrado; no se renombra a README.md")

    # Create some placeholder missing-evidence files (assumptions)
    placeholders = [
        'Falta_Inscripcion_Registro_Civil.md',
        'Falta_Pericial_Trabajo_Social.md',
        'Falta_Resultados_Investigacion_Financiera_SAT_CNBV.md',
        'Falta_Pliego_Posiciones_y_RFC_CURP.md'
    ]
    for p in placeholders:
        fp = MISSING / p
        if not fp.exists():
            fp.write_text(f"# {p.replace('_', ' ').replace('.md','')}\n\n- Descripción: \n- Fecha identificada: \n- Responsable: \n- Estado: pendiente\n", encoding='utf-8')
            print(f"Creado placeholder: {fp.relative_to(ROOT)}")

    print("Organización completada.")

    # --- New improvements: reclassify files from 0000 using mtime, validate readme links, create indexes
    reclassify_from_0000()
    # update README from moves_map after reclassification
    update_readme_from_map()
    # fix links that include parentheses or were truncated by regex
    fix_tricky_links()
    validate_readme_links()
    create_year_indexes()
    # create root TOC linking to year indexes
    create_toc()


def update_readme_from_map():
    """Actualiza README.md reemplazando rutas antiguas por las nuevas usando moves_map.tsv."""
    if not README.exists() or not MAP_FILE.exists():
        print("No hay README.md o moves_map.tsv para actualizar desde mapa.")
        return
    text = README.read_text(encoding='utf-8')
    # load map into dict: original -> new
    mapping = {}
    with MAP_FILE.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            o = row.get('original')
            n = row.get('new')
            if o and n:
                mapping[o] = n

    updated = text
    from urllib.parse import quote
    # First replace explicit link targets like (./oldpath)
    for o, n in mapping.items():
        old_target = './' + o
        new_target = './' + n.replace(' ', '%20')
        # replace any occurrence of (./oldpath) -> (./newpath)
        updated = updated.replace('(' + old_target + ')', '(' + new_target + ')')
        # also replace URL-encoded old targets
        updated = updated.replace('(' + './' + quote(o) + ')', '(' + new_target + ')')

    # Then replace bare filenames in backticks `name` -> [name](./newpath)
    for o, n in mapping.items():
        basename = Path(o).name
        new_target = './' + n.replace(' ', '%20')
        updated = re.sub(rf"`{re.escape(basename)}`", f"[{basename}]({new_target})", updated)

    # Finally replace unlinked bare occurrences of basename if they are not already inside [](...)
    def bare_replace(match):
        name = match.group(0)
        # if already part of a markdown link text [name] or link destination, skip
        # We'll check a small window around match in original text
        return match.group(0)

    # write back if changed
    if updated != text:
        README.write_text(updated, encoding='utf-8')
        print('README.md actualizado usando moves_map.tsv')
    else:
        print('No se detectaron cambios necesarios en README.md a partir de moves_map.tsv')


def reclassify_from_0000():
    """Mueve archivos que están en 1_Evidencia_Cronologica/0000/00_Documentos_Fundamentales
    a carpetas por año/mes usando la fecha de modificación del archivo.
    """
    src_root = EVID / '0000' / '00_Documentos_Fundamentales'
    if not src_root.exists():
        print("No hay carpeta 0000 para reclasificar.")
        return
    moved = []
    for item in sorted(src_root.iterdir()):
        # Try metadata first (pdf or image)
        found = None
        if item.is_file():
            suf = item.suffix.lower()
            if suf in ('.pdf',):
                found = date_from_pdf(item)
            elif suf in ('.jpg', '.jpeg', '.png'):
                found = date_from_image(item)
        # fallback to mtime
        if not found:
            try:
                mtime = item.stat().st_mtime
                dt = datetime.fromtimestamp(mtime)
                found = (dt.year, dt.month)
            except Exception:
                continue
        y, mo = found
        # only reasonable years
        if y < 1990 or y > 2100:
            continue
        dest_dir = EVID / str(y) / month_folder(mo)
        ensure_dirs(dest_dir)
        dest = dest_dir / item.name
        final_dest = dest
        i = 1
        while final_dest.exists():
            final_dest = dest.with_name(f"{dest.stem}_{i}{dest.suffix}")
            i += 1
        try:
            shutil.move(str(item), str(final_dest))
            moved.append((str(item.relative_to(ROOT)), str(final_dest.relative_to(ROOT))))
            print(f"Reclassified: {item.name} -> {final_dest.relative_to(ROOT)}")
        except Exception as e:
            print(f"Failed to reclassify {item}: {e}")
    # append to moves_map
    if moved:
        with MAP_FILE.open('a', newline='') as f:
            w = csv.writer(f, delimiter='\t')
            for o,n in moved:
                w.writerow([o,n])


def validate_readme_links():
    """Valida enlaces en README.md: reporta enlaces rotos relativos (no http).
    """
    if not README.exists():
        print("README.md no existe para validar enlaces.")
        return
    text = README.read_text(encoding='utf-8')
    # find markdown links [text](link)
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    broken = []
    from urllib.parse import unquote
    for link in links:
        if link.startswith('http://') or link.startswith('https://'):
            continue
        # normalize leading ./
        l = link
        if l.startswith('./'):
            l = l[2:]
        l = unquote(l)
        target = (ROOT / l).resolve()
        if not target.exists():
            broken.append((link, str(target.relative_to(ROOT))))
    if broken:
        print('\nEnlaces rotos detectados en README.md:')
        for orig, targ in broken:
            print(f" - {orig} -> (no encontrado) {targ}")
    else:
        print('Todos los enlaces relativos en README.md apuntan a archivos existentes.')


def create_year_indexes():
    """Crea INDEX.md por año listando meses y archivos con enlaces relativos."""
    for year_dir in sorted(EVID.iterdir()):
        if not year_dir.is_dir():
            continue
        year = year_dir.name
        if year == '0000':
            continue
        index_lines = [f"# Índice {year}", ""]
        # list months sorted by leading numeric
        months = sorted([p for p in year_dir.iterdir() if p.is_dir()], key=lambda p: p.name)
        for month_dir in months:
            index_lines.append(f"## {month_dir.name}")
            index_lines.append("")
            # list files and directories
            items = sorted(month_dir.iterdir(), key=lambda p: p.name)
            for it in items:
                rel = it.relative_to(ROOT)
                display = it.name
                index_lines.append(f"- [{display}](./{rel.as_posix()})")
            index_lines.append("")
        # write INDEX.md
        idx_file = year_dir / 'INDEX.md'
        idx_file.write_text('\n'.join(index_lines), encoding='utf-8')
        print(f"Created index: {idx_file.relative_to(ROOT)}")


def create_toc():
    """Crea TOC.md en la raíz que enlace a los INDEX.md por año."""
    toc = ['# TOC - Evidencia Cronológica', '']
    years = sorted([p.name for p in EVID.iterdir() if p.is_dir() and p.name.isdigit()])
    for y in years:
        idx = Path('1_Evidencia_Cronologica') / y / 'INDEX.md'
        if idx.exists():
            toc.append(f"- [{y}]({idx.as_posix()})")
        else:
            toc.append(f"- {y} (no index)")
    TOC = ROOT / 'TOC.md'
    TOC.write_text('\n'.join(toc), encoding='utf-8')
    print(f"Created TOC: {TOC.relative_to(ROOT)}")


def fix_tricky_links():
    """Arregla enlaces con paréntesis y espacios que pudieron quedar mal codificados.
    Específicamente busca la mención a Actas de nacimientos con caracteres especiales y la corrige usando moves_map.tsv.
    """
    if not README.exists() or not MAP_FILE.exists():
        return
    text = README.read_text(encoding='utf-8')
    # load map
    mapping = {}
    with MAP_FILE.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            o = row.get('original')
            n = row.get('new')
            if o and n:
                mapping[o] = n

    # common problematic original
    candidates = [k for k in mapping.keys() if 'Actas de nacimientos' in k]
    if not candidates:
        return
    orig = candidates[0]
    new = mapping[orig]
    # replace URL-encoded and truncated variants
    variants = [
        './' + orig,
        './' + orig.replace(' ', '%20'),
        './' + orig.replace(' ', '%20').replace('(', '%28').replace(')', '%29'),
        './' + '1_Evidencia_Cronologica/0000/00_Documentos_Fundamentales/Actas%20de%20nacimientos%20(Sofía%20y%20Darío'
    ]
    updated = text
    new_target = './' + new.replace(' ', '%20')
    for v in variants:
        updated = updated.replace('(' + v + ')', '(' + new_target + ')')

    if updated != text:
        README.write_text(updated, encoding='utf-8')
        print('Fixed tricky links in README.md')

if __name__ == '__main__':
    main()
