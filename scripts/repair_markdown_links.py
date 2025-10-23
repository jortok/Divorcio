#!/usr/bin/env python3
"""Repair Markdown links using moves_map_applied.tsv.

Creates backups of modified .md files under .md_backups/<timestamp>/ and
writes a log at repair_links.log listing replacements made.

Usage: python3 scripts/repair_markdown_links.py
"""
from pathlib import Path
import csv
import shutil
import time
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
# try the root first; if not present, search recursively for the file
MAP_FILE = ROOT / 'moves_map_applied.tsv'
if not MAP_FILE.exists():
    found = list(ROOT.rglob('moves_map_applied.tsv'))
    if found:
        MAP_FILE = found[0]
LOG_FILE = ROOT / 'repair_links.log'


def load_map(path):
    pairs = []
    if not path.exists():
        print(f"Map file not found: {path}")
        return pairs
    with path.open('r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if not row: 
                continue
            if row[0].startswith('#'):
                continue
            if len(row) < 2:
                continue
            old, new = row[0].strip(), row[1].strip()
            if old and new:
                pairs.append((old, new))
    return pairs


def make_replacements(text, pairs):
    changed = False
    report = []
    # Sort by length desc to avoid partial replacements
    pairs_sorted = sorted(pairs, key=lambda p: len(p[0]), reverse=True)
    for old, new in pairs_sorted:
        # raw occurrence
        if old in text:
            text = text.replace(old, new)
            changed = True
            report.append((old, new, 'raw'))
        # URL-encoded occurrence
        old_q = urllib.parse.quote(old)
        new_q = urllib.parse.quote(new)
        if old_q in text:
            text = text.replace(old_q, new_q)
            changed = True
            report.append((old_q, new_q, 'urlencoded'))
        # spaces encoded as %20
        old_space = old.replace(' ', '%20')
        new_space = new.replace(' ', '%20')
        if old_space in text:
            text = text.replace(old_space, new_space)
            changed = True
            report.append((old_space, new_space, 'pct20'))
    return text, changed, report


def backup_file(file_path, backup_root):
    dest = backup_root / file_path.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if file_path.is_file():
        shutil.copy2(file_path, dest)


def main():
    pairs = load_map(MAP_FILE)
    if not pairs:
        print('No map entries found. Exiting.')
        return 1

    timestamp = time.strftime('%Y%m%d-%H%M%S')
    backup_root = ROOT / f'.md_backups/{timestamp}'
    backup_root.mkdir(parents=True, exist_ok=True)

    md_files = list(ROOT.rglob('*.md'))
    replaced_count = 0
    file_changes = []

    for md in md_files:
        try:
            text = md.read_text(encoding='utf-8')
        except Exception:
            # skip unreadable files
            continue
        new_text, changed, report = make_replacements(text, pairs)
        if changed:
            backup_file(md, backup_root)
            md.write_text(new_text, encoding='utf-8')
            replaced_count += 1
            file_changes.append((str(md.relative_to(ROOT)), report))

    # write log
    with LOG_FILE.open('a', encoding='utf-8') as lf:
        lf.write(f'Run at {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        lf.write(f'Backups: {backup_root}\n')
        lf.write(f'MD files scanned: {len(md_files)}\n')
        lf.write(f'Files changed: {replaced_count}\n')
        for fname, reports in file_changes:
            lf.write(f'- {fname}\n')
            for old, new, typ in reports:
                lf.write(f'    {typ}: {old} -> {new}\n')
        lf.write('\n')

    print(f'Marked {replaced_count} markdown files updated; backups at {backup_root}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
