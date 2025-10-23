#!/usr/bin/env python3
"""
Apply rename suggestions safely (gradual) for files under 1_Evidencia_Cronologica.
- Reads `moves_map_suggested.tsv` (created by rename_dryrun.py).
- Filters entries under `1_Evidencia_Cronologica/`.
- Copies originals to a backup folder `./.rename_backups/<timestamp>/` preserving relative paths.
- Performs filesystem renames (os.replace) to move old -> new (creates parent dirs as needed).
- Updates markdown files listed in `reference_updates.txt` (simple text replace of targets) backing up original md files.
- Writes `moves_map_applied.tsv` and a log file.

This script is conservative: it only operates on files that currently exist at the old path. It will skip entries whose target already exists (to avoid overwriting) and will stop on unexpected errors.
"""
from pathlib import Path
import shutil
import time
import csv
import sys

ROOT = Path(__file__).resolve().parents[1]
MAP_FILE = ROOT / 'moves_map_suggested.tsv'
REFS_FILE = ROOT / 'reference_updates.txt'
BACKUP_DIR = ROOT / '.rename_backups' / time.strftime('%Y%m%d-%H%M%S')
APPLIED_MAP = ROOT / 'moves_map_applied.tsv'
LOG_FILE = ROOT / 'rename_apply.log'

def load_map():
    pairs = []
    if not MAP_FILE.exists():
        print('No moves_map_suggested.tsv found. Run scripts/rename_dryrun.py first.')
        sys.exit(1)
    with MAP_FILE.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                old, new = parts[0], parts[1]
                pairs.append((old, new))
    return pairs


def load_refs():
    entries = []
    if not REFS_FILE.exists():
        return entries
    with REFS_FILE.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # format: md: old -> new
            if ': ' in line and ' -> ' in line:
                md, rest = line.split(': ', 1)
                old, new = rest.split(' -> ', 1)
                entries.append((md.strip(), old.strip(), new.strip()))
    return entries


def ensure_backup(path):
    # path may be a relative string like '1_Evidencia_Cronologica/2024/..'
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    dest = BACKUP_DIR / p.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        if p.is_file():
            shutil.copy2(p, dest)
        else:
            # copytree for directories
            # if dest exists (shouldn't) remove to allow copy
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(p, dest)


def apply_renames(pairs):
    applied = []
    for old_rel, new_rel in pairs:
        # only apply inside 1_Evidencia_Cronologica
        if not old_rel.startswith('1_Evidencia_Cronologica/'):
            continue
        old = ROOT / old_rel
        new = ROOT / new_rel
        if not old.exists():
            print(f'SKIP missing: {old_rel}')
            continue
        if new.exists():
            print(f'SKIP target exists: {new_rel} (will not overwrite)')
            continue
        # backup original
        ensure_backup(old_rel)
        # ensure parent for new exists
        new.parent.mkdir(parents=True, exist_ok=True)
        # perform move
        old.replace(new)
        applied.append((old_rel, new_rel))
        print(f'APPLIED: {old_rel} -> {new_rel}')
    return applied


def update_markdown_refs(refs):
    changed = []
    for md_rel, old_target, new_target in refs:
        md_path = ROOT / md_rel
        if not md_path.exists():
            print(f'MD missing, skip: {md_rel}')
            continue
        # backup md file
        ensure_backup(md_rel)
        text = md_path.read_text(encoding='utf-8', errors='ignore')
        if old_target in text:
            new_text = text.replace(old_target, new_target)
            md_path.write_text(new_text, encoding='utf-8')
            changed.append((md_rel, old_target, new_target))
            print(f'MD updated: {md_rel}: {old_target} -> {new_target}')
        else:
            # sometimes links include ./ or different prefix; try basename replace
            if '/' in old_target:
                b = Path(old_target).name
                if b in text:
                    new_b = Path(new_target).name
                    new_text = text.replace(b, new_b)
                    md_path.write_text(new_text, encoding='utf-8')
                    changed.append((md_rel, old_target, new_target))
                    print(f'MD basename updated: {md_rel}: {b} -> {new_b}')
                else:
                    print(f'No occurrence in {md_rel} for {old_target} (or basename)')
            else:
                print(f'No occurrence in {md_rel} for {old_target}')
    return changed


def write_applied(applied):
    with APPLIED_MAP.open('w', encoding='utf-8') as f:
        f.write('# old\tnew\n')
        for old, new in applied:
            f.write(f"{old}\t{new}\n")


def main():
    pairs = load_map()
    refs = load_refs()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open('w', encoding='utf-8') as log:
        log.write(f'Apply rename run at {time.asctime()}\n')
    applied = apply_renames(pairs)
    md_changed = update_markdown_refs(refs)
    write_applied(applied)
    with LOG_FILE.open('a', encoding='utf-8') as log:
        log.write(f'Applied renames: {len(applied)}\n')
        for old,new in applied:
            log.write(f'{old}\t{new}\n')
        log.write(f'Markdown updated: {len(md_changed)}\n')
        for md,old,new in md_changed:
            log.write(f'{md}: {old} -> {new}\n')
    print('\nDone. Summary:')
    print(f'Applied renames: {len(applied)}')
    print(f'Markdown updated: {len(md_changed)}')
    print(f'Backups at: {BACKUP_DIR}')

if __name__ == '__main__':
    main()
