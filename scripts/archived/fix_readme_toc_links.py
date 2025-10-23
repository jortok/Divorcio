#!/usr/bin/env python3
"""Safely fix README.md TOC.md links by adding ./ prefix.

Backs up README.md under .md_backups/<timestamp>/README.md and writes a small log to repair_links.log.
"""
from pathlib import Path
import time
import shutil

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / 'README.md'
BACKUP_ROOT = ROOT / '.md_backups'
LOG = ROOT / 'repair_links.log'


def main():
    if not README.exists():
        print('README.md not found')
        return 1
    text = README.read_text(encoding='utf-8')
    new_text = text.replace('](TOC.md)', '](./TOC.md)')
    if new_text == text:
        print('No changes needed in README.md')
        return 0
    timestamp = time.strftime('%Y%m%d-%H%M%S')
    backup_dir = BACKUP_ROOT / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(README, backup_dir / 'README.md')
    README.write_text(new_text, encoding='utf-8')
    with LOG.open('a', encoding='utf-8') as lf:
        lf.write(f'fix_readme_toc_links run at {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        lf.write(f'Backup: {backup_dir}/README.md\n')
        lf.write('Replaced ](TOC.md) -> ](./TOC.md) in README.md\n\n')
    print(f'Updated README.md (backup at {backup_dir}/README.md)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
