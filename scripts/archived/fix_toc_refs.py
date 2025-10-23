#!/usr/bin/env python3
"""Fix references to 'toc.md' by replacing with 'TOC.md' across .md files.

Backs up modified files under .md_backups/<timestamp>/ and appends to repair_links.log.
"""
from pathlib import Path
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR_ROOT = ROOT / '.md_backups'
LOG_FILE = ROOT / 'repair_links.log'


def find_md_files():
    return list(ROOT.rglob('*.md'))


def backup_file(file_path, backup_root):
    dest = backup_root / file_path.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, dest)


def main():
    md_files = find_md_files()
    timestamp = time.strftime('%Y%m%d-%H%M%S')
    backup_root = BACKUP_DIR_ROOT / timestamp
    backup_root.mkdir(parents=True, exist_ok=True)

    changed_files = []
    for md in md_files:
        try:
            text = md.read_text(encoding='utf-8')
        except Exception:
            continue
        if 'toc.md' in text:
            new_text = text.replace('toc.md', 'TOC.md')
            if new_text != text:
                backup_file(md, backup_root)
                md.write_text(new_text, encoding='utf-8')
                changed_files.append(str(md.relative_to(ROOT)))

    with LOG_FILE.open('a', encoding='utf-8') as lf:
        lf.write(f"fix_toc_refs run at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        lf.write(f"Backups: {backup_root}\n")
        lf.write(f"Files changed: {len(changed_files)}\n")
        for f in changed_files:
            lf.write(f"- {f}\n")
        lf.write('\n')

    print(f"Replaced 'toc.md' in {len(changed_files)} files; backups at {backup_root}")


if __name__ == '__main__':
    raise SystemExit(main())
