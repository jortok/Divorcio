#!/usr/bin/env python3
"""rename_tool.py

Consolidated renaming tool with two main modes:

- Dry-run: scan repository and propose normalized names, write
  `moves_map_suggested.tsv` and `reference_updates.txt`.

- Apply: read `moves_map_suggested.tsv` and perform safe renames under
  `1_Evidencia_Cronologica/` (optionally all), creating backups under
  `.rename_backups/<timestamp>/`, writing `moves_map_applied.tsv` and
  update markdown references listed in `reference_updates.txt`.

Usage examples:

  # produce suggestions only
  python3 scripts/rename_tool.py --dry-run

  # apply previously suggested map (safe, only under 1_Evidencia_Cronologica)
  python3 scripts/rename_tool.py --apply

  # apply and update markdown references
  python3 scripts/rename_tool.py --apply --update-refs

"""
from pathlib import Path
import argparse
import unicodedata
import re
import csv
import time
import shutil
import sys
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".git", "scripts/archived", "scripts", "re", "unicodedata", ".venv", "__pycache__", "venv", "node_modules"}
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def slugify(name: str) -> str:
    nfkd = unicodedata.normalize('NFKD', name)
    only_ascii = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    s = only_ascii
    s = s.replace('/', '-')
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", s)
    s = re.sub(r"[-_]{2,}", "-", s)
    s = s.strip('-_')
    return s.lower()


def should_skip(rel: Path) -> bool:
    parts = [p for p in rel.parts]
    if any(p in EXCLUDE_DIRS or p.startswith('.') for p in parts):
        return True
    if rel.name in ("moves_map.tsv", "moves_map_suggested.tsv", "moves_map_applied.tsv"):
        return True
    return False


def propose_new_name(path: Path, used_names: set) -> Path:
    rel = path.relative_to(ROOT)
    parent = rel.parent
    stem = path.stem
    ext = path.suffix
    new_stem = slugify(stem)
    if new_stem == '':
        new_stem = 'file'
    new_name = new_stem + ext.lower()
    candidate = parent / new_name
    i = 1
    while str(candidate) in used_names:
        candidate = parent / f"{new_stem}-{i}{ext.lower()}"
        i += 1
    used_names.add(str(candidate))
    return candidate


def scan_and_suggest(out_map: Path, out_refs: Path):
    files = [p for p in ROOT.rglob("*") if p.is_file()]
    suggestions = []
    used = set()
    for p in files:
        used.add(str(p.relative_to(ROOT)))
    for p in sorted(files):
        rel = p.relative_to(ROOT)
        if should_skip(rel):
            continue
        bad = False
        name = p.name
        if re.search(r"[A-Z]", name):
            bad = True
        if ' ' in name or '%' in name or '(' in name or ')' in name or '\\' in name:
            bad = True
        try:
            name.encode('ascii')
        except Exception:
            bad = True
        if bad:
            new_rel = propose_new_name(p, used)
            suggestions.append((str(rel), str(new_rel)))

    # analyze markdown references
    md_files = [p for p in ROOT.rglob('*.md') if not should_skip(p.relative_to(ROOT))]
    reference_updates = []
    lookup = {old: new for old, new in suggestions}
    basename_map = {Path(old).name: Path(new).name for old, new in suggestions}
    for md in md_files:
        text = md.read_text(encoding='utf-8', errors='ignore')
        for m in LINK_RE.finditer(text):
            target = m.group(1)
            if target.startswith('http') or target.startswith('#') or target.startswith('mailto:'):
                continue
            norm = target.lstrip('./')
            if norm in lookup:
                reference_updates.append((str(md.relative_to(ROOT)), target, lookup[norm]))
            else:
                base = Path(norm).name
                if base in basename_map:
                    new_base = basename_map[base]
                    new_target = str(Path(norm).with_name(new_base))
                    reference_updates.append((str(md.relative_to(ROOT)), target, new_target))

    with out_map.open('w', encoding='utf-8') as f:
        f.write('# old\tnew\n')
        for old, new in suggestions:
            f.write(f"{old}\t{new}\n")

    with out_refs.open('w', encoding='utf-8') as f:
        if not reference_updates:
            f.write('No markdown references to update detected.\n')
        else:
            for md, oldt, newt in reference_updates:
                f.write(f"{md}: {oldt} -> {newt}\n")

    print(f"Scanned {len(files)} files; suggestions: {len(suggestions)}; reference updates: {len(reference_updates)}")
    return len(suggestions), len(reference_updates)


def load_suggested_map(map_file: Path):
    pairs = []
    if not map_file.exists():
        print('Suggested map not found:', map_file)
        return pairs
    with map_file.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                pairs.append((parts[0].strip(), parts[1].strip()))
    return pairs


def ensure_backup(src: Path, backup_root: Path):
    dest = backup_root / src
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        if src.is_file():
            shutil.copy2(src, dest)
        else:
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)


def apply_map(pairs, backup_root: Path, only_within_evid=True):
    applied = []
    skipped = []
    for old_rel, new_rel in pairs:
        # optional filter
        if only_within_evid and not old_rel.startswith('1_Evidencia_Cronologica/'):
            # skip but record
            skipped.append((old_rel, new_rel, 'outside_scope'))
            continue
        old = ROOT / old_rel
        new = ROOT / new_rel
        if not old.exists():
            skipped.append((old_rel, new_rel, 'missing_source'))
            continue
        if new.exists():
            skipped.append((old_rel, new_rel, 'target_exists'))
            continue
        new.parent.mkdir(parents=True, exist_ok=True)
        try:
            ensure_backup(old, backup_root)
            old.replace(new)
            applied.append((old_rel, new_rel))
            print(f'APPLIED: {old_rel} -> {new_rel}')
        except Exception as e:
            skipped.append((old_rel, new_rel, f'error:{e}'))
    return applied, skipped


def update_markdown_refs_from_file(refs_file: Path):
    changed = []
    if not refs_file.exists():
        print('Reference updates file not found:', refs_file)
        return changed
    with refs_file.open('r', encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]
    for line in lines:
        if ': ' in line and ' -> ' in line:
            md, rest = line.split(': ', 1)
            old, new = rest.split(' -> ', 1)
            md_path = ROOT / md
            if not md_path.exists():
                continue
            text = md_path.read_text(encoding='utf-8', errors='ignore')
            if old in text:
                ensure_dir = ROOT / '.md_backups' / time.strftime('%Y%m%d-%H%M%S')
                ensure_backup(md_path, ensure_dir)
                new_text = text.replace(old, new)
                md_path.write_text(new_text, encoding='utf-8')
                changed.append((md, old, new))
            else:
                # try basename replacement
                b = Path(old).name
                if b in text:
                    ensure_dir = ROOT / '.md_backups' / time.strftime('%Y%m%d-%H%M%S')
                    ensure_backup(md_path, ensure_dir)
                    new_b = Path(new).name
                    new_text = text.replace(b, new_b)
                    md_path.write_text(new_text, encoding='utf-8')
                    changed.append((md, b, new_b))
    print(f'Markdown files updated: {len(changed)}')
    return changed


def write_applied_map(applied_list, out_path: Path):
    with out_path.open('w', encoding='utf-8') as f:
        f.write('# old\tnew\n')
        for o, n in applied_list:
            f.write(f"{o}\t{n}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dry-run', action='store_true', help='Scan and propose renames (writes moves_map_suggested.tsv)')
    p.add_argument('--apply', action='store_true', help='Apply renames from moves_map_suggested.tsv')
    p.add_argument('--update-refs', action='store_true', help='Update markdown references using reference_updates.txt after apply')
    p.add_argument('--apply-all', action='store_true', help='Apply renames even if outside 1_Evidencia_Cronologica (use with caution)')
    args = p.parse_args()

    suggested_map = ROOT / 'moves_map_suggested.tsv'
    reference_updates = ROOT / 'reference_updates.txt'
    applied_map = ROOT / 'moves_map_applied.tsv'

    if not args.dry_run and not args.apply:
        p.print_help()
        sys.exit(1)

    if args.dry_run:
        scan_and_suggest(suggested_map, reference_updates)

    if args.apply:
        pairs = load_suggested_map(suggested_map)
        if not pairs:
            print('No suggested pairs to apply. Run --dry-run first or provide a moves map.')
            sys.exit(1)
        ts = time.strftime('%Y%m%d-%H%M%S')
        backup_root = ROOT / '.rename_backups' / ts / 'apply'
        backup_root.mkdir(parents=True, exist_ok=True)
        applied, skipped = apply_map(pairs, backup_root, only_within_evid=not args.apply_all)
        if applied:
            write_applied_map(applied, applied_map)
        # write a log
        with (ROOT / 'rename_apply.log').open('a', encoding='utf-8') as lf:
            lf.write(f'Run at {time.asctime()}\n')
            lf.write(f'Backups: {backup_root}\n')
            lf.write(f'Applied: {len(applied)}; Skipped: {len(skipped)}\n')
            for o,n in applied:
                lf.write(f'APPLIED: {o} -> {n}\n')
            for o,n,reason in skipped:
                lf.write(f'SKIPPED: {o} -> {n} ({reason})\n')
            lf.write('\n')

        if args.update_refs:
            update_markdown_refs_from_file(reference_updates)

    print('Done.')


if __name__ == '__main__':
    main()
