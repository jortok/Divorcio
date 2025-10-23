#!/usr/bin/env python3
"""Apply pending renames from PENDIENTES_VERIFICAR.txt safely.

Creates backups under .rename_backups/<timestamp>/pending_apply/, moves files/dirs,
appends applied mappings to moves_map_applied.tsv (or creates it), and logs to rename_apply.log.
"""
from pathlib import Path
import shutil
import time
import csv

ROOT = Path(__file__).resolve().parents[1]
PENDIENTES = ROOT / 'PENDIENTES_VERIFICAR.txt'
BACKUP_ROOT = ROOT / '.rename_backups'
APPLIED = ROOT / 'moves_map_applied.tsv'
LOG = ROOT / 'rename_apply.log'


def read_pendientes(path):
    pairs = []
    if not path.exists():
        return pairs
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                pairs.append((parts[0].strip(), parts[1].strip()))
    return pairs


def ensure_backup(src, backup_root):
    dest = backup_root / src
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        if src.is_file():
            shutil.copy2(src, dest)
        else:
            # copytree for dirs
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)


def main():
    pairs = read_pendientes(PENDIENTES)
    if not pairs:
        print('No pending entries found in', PENDIENTES)
        return 0

    ts = time.strftime('%Y%m%d-%H%M%S')
    backup_root = BACKUP_ROOT / ts / 'pending_apply'
    backup_root.mkdir(parents=True, exist_ok=True)

    applied_rows = []
    skipped = []

    for old, new in pairs:
        src = ROOT / old
        dst = ROOT / new
        if not src.exists():
            skipped.append((old, new, 'missing_source'))
            continue
        if dst.exists():
            skipped.append((old, new, 'target_exists'))
            continue
        # ensure dst parent
        dst.parent.mkdir(parents=True, exist_ok=True)
        # backup src
        try:
            ensure_backup(src, backup_root)
            shutil.move(str(src), str(dst))
            applied_rows.append((old, new))
        except Exception as e:
            skipped.append((old, new, f'error:{e}'))

    # append applied to moves_map_applied.tsv (create header if needed)
    if applied_rows:
        header = ['# old', 'new']
        exists = APPLIED.exists()
        with APPLIED.open('a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            if not exists:
                writer.writerow(header)
            for r in applied_rows:
                writer.writerow(r)

    # write log
    with LOG.open('a', encoding='utf-8') as lf:
        lf.write(f'Apply pending run at {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        lf.write(f'Backups: {backup_root}\n')
        lf.write(f'Applied: {len(applied_rows)}\n')
        for old, new in applied_rows:
            lf.write(f'APPLIED: {old} -> {new}\n')
        lf.write(f'Skipped: {len(skipped)}\n')
        for old, new, reason in skipped:
            lf.write(f'SKIPPED: {old} -> {new} ({reason})\n')
        lf.write('\n')

    print(f'Applied: {len(applied_rows)}; Skipped: {len(skipped)}; backups at {backup_root}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
