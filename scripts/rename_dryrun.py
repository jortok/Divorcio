#!/usr/bin/env python3
"""
Dry-run renaming helper.
- Scans repository for files with spaces, uppercase letters, non-ascii or problematic chars.
- Suggests normalized names (lowercase, dashes, remove diacritics).
- Writes `moves_map_suggested.tsv` with old\tnew (relative paths) and `reference_updates.txt` listing markdown files and suggested replacements.
This script DOES NOT modify files. Use it to review suggestions before applying changes.
"""
from pathlib import Path
import unicodedata
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".git", "scripts", "re", "unicodedata", ".venv", "__pycache__", "venv", "node_modules"}

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

def slugify(name: str) -> str:
    # separate base and extension handled by caller
    # normalize unicode, remove diacritics
    nfkd = unicodedata.normalize('NFKD', name)
    only_ascii = ''.join([c for c in nfkd if not unicodedata.combining(c)])
    # replace spaces and slashes with hyphen
    s = only_ascii
    s = s.replace('/', '-')
    # keep letters, numbers, dot, dash, underscore
    # but we will replace sequences of non alnum with dash
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", s)
    s = re.sub(r"[-_]{2,}", "-", s)
    s = s.strip('-_')
    return s.lower()


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
    # avoid duplicate candidate names
    i = 1
    while str(candidate) in used_names:
        candidate = parent / f"{new_stem}-{i}{ext.lower()}"
        i += 1
    used_names.add(str(candidate))
    return candidate


def should_skip(path: Path) -> bool:
    # skip directories and excluded
    if any(p in EXCLUDE_DIRS for p in path.parts):
        return True
    # skip moves_map or other control files
    if path.name in ("moves_map.tsv", "moves_map_suggested.tsv"):
        return True
    return False


def main():
    files = [p for p in ROOT.rglob("*") if p.is_file()]
    suggestions = []  # tuples old_rel, new_rel
    used = set()

    # seed used with existing relative paths to avoid collisions
    for p in files:
        used.add(str(p.relative_to(ROOT)))

    for p in sorted(files):
        rel = p.relative_to(ROOT)
        if should_skip(rel):
            continue
        # proposal rules: if name contains uppercase, spaces, percent-escapes, parentheses, non-ascii, multiple dots, leading/trailing spaces, or odd chars
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
        # also normalize excessively long names? skip
        if bad:
            new_rel = propose_new_name(p, used)
            suggestions.append((str(rel), str(new_rel)))

    # analyze markdown links for references to these names
    md_files = [p for p in ROOT.rglob('*.md') if not should_skip(p.relative_to(ROOT))]
    reference_updates = []
    # build quick lookup
    lookup = {old: new for old,new in suggestions}
    # also consider basename matches
    basename_map = {Path(old).name: Path(new).name for old,new in suggestions}

    for md in md_files:
        text = md.read_text(encoding='utf-8', errors='ignore')
        for m in LINK_RE.finditer(text):
            target = m.group(1)
            # ignore http(s) and anchors and mailto
            if target.startswith('http') or target.startswith('#') or target.startswith('mailto:'):
                continue
            # remove possible ./ or leading /
            norm = target.lstrip('./')
            # if exact relative path in suggestions
            if norm in lookup:
                reference_updates.append((str(md.relative_to(ROOT)), target, lookup[norm]))
            else:
                # try basename match
                base = Path(norm).name
                if base in basename_map:
                    new_base = basename_map[base]
                    new_target = str(Path(norm).with_name(new_base))
                    reference_updates.append((str(md.relative_to(ROOT)), target, new_target))

    # write outputs
    out_map = ROOT / 'moves_map_suggested.tsv'
    with out_map.open('w', encoding='utf-8') as f:
        f.write('# old\tnew\n')
        for old,new in suggestions:
            f.write(f"{old}\t{new}\n")

    out_refs = ROOT / 'reference_updates.txt'
    with out_refs.open('w', encoding='utf-8') as f:
        if not reference_updates:
            f.write('No markdown references to update detected.\n')
        else:
            for md, oldt, newt in reference_updates:
                f.write(f"{md}: {oldt} -> {newt}\n")

    print(f"Scanned {len(files)} files; suggestions: {len(suggestions)}; reference updates: {len(reference_updates)}")
    print(f"Wrote: {out_map} and {out_refs}")

if __name__ == '__main__':
    main()
