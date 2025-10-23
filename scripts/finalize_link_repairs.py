#!/usr/bin/env python3
"""Finalize Markdown link repairs by converting mapped targets to correct relative links.

Loads moves_map_applied.tsv (or moves_map.tsv) and replaces markdown link targets
with a computed relative path from each md file to the new target. Creates backups
and logs changes in repair_links.log.
"""
from pathlib import Path
import re
import csv
import time
import shutil
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
MAP_FILES = ['moves_map_applied.tsv', 'moves_map.tsv']
LOG_FILE = ROOT / 'repair_links.log'


def find_map():
    for name in MAP_FILES:
        p = ROOT / name
        if p.exists():
            return p
    # search recursively
    for name in MAP_FILES:
        found = list(ROOT.rglob(name))
        if found:
            return found[0]
    return None


def load_map(path):
    m = {}
    with path.open('r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if not row: continue
            if row[0].startswith('#'): continue
            if len(row) < 2: continue
            old, new = row[0].strip(), row[1].strip()
            if old and new:
                m[old] = new
    return m


LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def backup_file(file_path, backup_root):
    dest = backup_root / file_path.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, dest)


def compute_relative(from_md: Path, target: Path) -> str:
    try:
        rel = target.relative_to(from_md.parent)
        return str(rel).replace('\\', '/')
    except Exception:
        # fallback to os relative
        return str(target.relative_to(ROOT))


def maybe_replace_target(md_path: Path, text: str, mapping: dict):
    changed = False
    reports = []

    def repl(match):
        nonlocal changed, reports
        label, target = match.group(1), match.group(2)
        # decode percent-encoded target for matching
        target_dec = urllib.parse.unquote(target)
        # strip any leading ./
        target_norm = target_dec.lstrip('./')

        # If exact match in mapping
        if target_norm in mapping:
            new_abs = ROOT / mapping[target_norm]
            if new_abs.exists():
                rel = compute_relative(md_path, new_abs)
                # re-encode spaces
                rel_enc = urllib.parse.quote(rel)
                reports.append((target, rel))
                changed = True
                return f'[{label}]({rel_enc})'
        # also check unquoted version
        if urllib.parse.unquote(target) in mapping:
            new_abs = ROOT / mapping[urllib.parse.unquote(target)]
            if new_abs.exists():
                rel = compute_relative(md_path, new_abs)
                rel_enc = urllib.parse.quote(rel)
                reports.append((target, rel))
                changed = True
                return f'[{label}]({rel_enc})'
        return match.group(0)

    new_text = LINK_RE.sub(repl, text)
    return new_text, changed, reports


def main():
    map_path = find_map()
    if not map_path:
        print('No mapping file found (moves_map_applied.tsv or moves_map.tsv). Exiting.')
        return 1
    mapping = load_map(map_path)
    if not mapping:
        print('Mapping empty. Exiting.')
        return 1

    timestamp = time.strftime('%Y%m%d-%H%M%S')
    backup_root = ROOT / f'.md_backups/{timestamp}/final'
    backup_root.mkdir(parents=True, exist_ok=True)

    md_files = list(ROOT.rglob('*.md'))
    changed_files = []

    for md in md_files:
        try:
            text = md.read_text(encoding='utf-8')
        except Exception:
            continue
        new_text, changed, reports = maybe_replace_target(md, text, mapping)
        if changed:
            backup_file(md, backup_root)
            md.write_text(new_text, encoding='utf-8')
            changed_files.append((str(md.relative_to(ROOT)), reports))

    with LOG_FILE.open('a', encoding='utf-8') as lf:
        lf.write(f'finalize_link_repairs run at {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        lf.write(f'Using map: {map_path}\n')
        lf.write(f'Backups: {backup_root}\n')
        lf.write(f'MD files scanned: {len(md_files)}\n')
        lf.write(f'Files changed: {len(changed_files)}\n')
        for fname, reports in changed_files:
            lf.write(f'- {fname}\n')
            for oldt, newt in reports:
                lf.write(f'    {oldt} -> {newt}\n')
        lf.write('\n')

    print(f'Finalized links in {len(changed_files)} markdown files; backups at {backup_root}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
