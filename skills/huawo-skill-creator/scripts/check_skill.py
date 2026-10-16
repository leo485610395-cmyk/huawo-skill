"""Read-only checks for a skill's entrypoint and Markdown resources; no dependencies."""
from pathlib import Path
import argparse
import json
import re
from urllib.parse import unquote


def check(root):
    root = root.expanduser().resolve()
    errors = []
    entry = root / 'SKILL.md'
    if not entry.is_file():
        return {'ok': False, 'errors': ['SKILL.md is missing']}
    if entry.is_symlink():
        return {'ok': False, 'errors': ['SKILL.md must not be an external link']}
    try:
        source = entry.read_text(encoding='utf-8-sig')
    except UnicodeError:
        return {'ok': False, 'errors': ['SKILL.md is not UTF-8']}
    match = re.match(r'\A---\s*\n(.*?)\n---(?:\s*\n|\Z)', source, re.S)
    if not match:
        return {'ok': False, 'errors': ['YAML frontmatter is missing']}
    header = match.group(1)
    name = re.search(r'^name:\s*[\"\']?([a-z0-9]+(?:-[a-z0-9]+)*)[\"\']?\s*$', header, re.M)
    if not name or name.group(1) != root.name or len(name.group(1)) >= 64:
        errors.append('name must match directory, use lower-case hyphenated words, and be shorter than 64 characters')
    description = re.search(r'^description:\s*(.*)$', header, re.M)
    if not description or not description.group(1).strip():
        errors.append('description is missing')
    elif description.group(1).strip() in ('|', '>'):
        tail = header[description.end():]
        if not re.match(r'\n[ \t]+\S', tail):
            errors.append('description block is empty')
    checked = 0
    for path in sorted(root.rglob('*.md')):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            errors.append(f'external Markdown path: {path.name}')
            continue
        try:
            text = path.read_text(encoding='utf-8-sig')
        except UnicodeError:
            errors.append(f'not UTF-8: {path.relative_to(root)}')
            continue
        unfinished = r'TO' + r'DO:|FI' + r'XME|<待' + r'填写>'
        if re.search(unfinished, text):
            errors.append(f'unfinished marker: {path.relative_to(root)}')
        for raw in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
            target = raw.strip().strip('<>').split('#', 1)[0]
            if not target or re.match(r'^[a-z][a-z0-9+.-]*:', target, re.I):
                continue
            resolved = (path.parent / unquote(target)).resolve()
            checked += 1
            if not resolved.is_relative_to(root):
                errors.append(f'reference escapes skill: {raw}')
            elif not resolved.exists():
                errors.append(f'reference is missing: {raw}')
    return {'ok': not errors, 'references_checked': checked, 'errors': errors,
            'scope': 'entrypoint and Markdown resources only; no business or script execution validation'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('skill_directory')
    result = check(Path(parser.parse_args().skill_directory))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['ok'] else 1)
