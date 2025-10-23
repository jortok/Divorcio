#!/usr/bin/env python3
"""Prune PENDIENTES_VERIFICAR and attempt to apply remaining pending renames.

Rules:
- If old == new (exact), drop the entry (no-op).
- If old doesn't exist but new exists, drop (already moved/resolved).
- If old exists and new exists, keep (target conflict) in SKIPPED file.
- If old exists and new does not exist, keep for apply.

After pruning, runs apply_pending_renames.py and commits updated pending files.
"""
from pathlib import Path
import subprocess
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
PEND = ROOT / 'PENDIENTES_VERIFICAR.txt'
SKIPPED = ROOT / 'PENDIENTES_VERIFICAR_SKIPPED.txt'


def read_pend(path):
    pairs = []
    if not path.exists():
        return pairs
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                pairs.append((parts[0], parts[1]))
    return pairs


def write_pend(path, pairs):
    with path.open('w', encoding='utf-8') as f:
        f.write('# PENDIENTES_VERIFICAR\n# old\tnew (sugerido)\n')
        for old, new in pairs:
            f.write(f'{old}\t{new}\n')


def main():
    pairs = read_pend(PEND)
    to_apply = []
    skipped = []
    dropped = []

    for old, new in pairs:
        oldp = ROOT / old
        newp = ROOT / new
        if old == new:
            dropped.append((old, new, 'same'))
            continue
        if not oldp.exists() and newp.exists():
            dropped.append((old, new, 'new_exists'))
            continue
        if oldp.exists() and newp.exists():
            skipped.append((old, new, 'target_exists'))
            continue
        if not oldp.exists() and not newp.exists():
            skipped.append((old, new, 'missing_source_and_target'))
            continue
        # old exists and new does not -> candidate to apply
        if oldp.exists() and not newp.exists():
            to_apply.append((old, new))
            continue

    write_pend(PEND, to_apply)
    # write skipped file
    with SKIPPED.open('w', encoding='utf-8') as f:
        f.write('# SKIPPED PENDIENTES (manual review)\n# old\tnew\treason\n')
        for old, new, reason in skipped:
            f.write(f'{old}\t{new}\t{reason}\n')
        for old, new, reason in dropped:
            f.write(f'{old}\t{new}\t{reason}\n')

    print(f'Pruned: kept {len(to_apply)} to apply; skipped {len(skipped)}; dropped {len(dropped)}')

    # run apply_pending_renames.py
    rc = subprocess.call(['python3', 'scripts/apply_pending_renames.py'])

    # run repair markdown links to catch references
    rc2 = subprocess.call(['python3', 'scripts/repair_markdown_links.py'])

    # rerun organizer
    rc3 = subprocess.call(['python3', 'scripts/organize_evidence.py', '--check-links'])

    # commit changes
    subprocess.call(['git', 'add', 'PENDIENTES_VERIFICAR.txt', 'PENDIENTES_VERIFICAR_SKIPPED.txt', 'moves_map_applied.tsv', 'rename_apply.log'])
    subprocess.call(['git', 'commit', '-m', 'chore: prune pending renames, apply remaining and update logs'],)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
