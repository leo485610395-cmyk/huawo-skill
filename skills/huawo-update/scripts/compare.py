"""Read-only file comparison; no network, writes, source execution or host discovery.

The caller must independently verify the official source and optional baseline.
Python 3.10+, standard library only.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat


PRIVATE = {"private", ".private", ".git"}
NAME = re.compile(r"huawo-[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def linked(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & 0x400
    )


def present(path):
    return os.path.lexists(path)


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def inventory(root, strict):
    files, blocked, retained, spellings = {}, [], [], {}

    def visit(folder):
        for path in sorted(folder.iterdir()):
            rel = path.relative_to(root).as_posix()
            variants = spellings.setdefault(rel.casefold(), [])
            variants.append(rel)
            if strict and len(variants) > 1:
                raise ValueError(f"source has ambiguous case-only paths: {variants}")
            if path.name.lower() in PRIVATE:
                if strict:
                    raise ValueError(f"source contains excluded private/git path: {rel}")
                retained.append(rel + "/ (not read)")
                continue
            if linked(path):
                if strict:
                    raise ValueError(f"source contains link/reparse path: {rel}")
                blocked.append(rel)
            elif path.is_dir():
                visit(path)
            elif path.is_file():
                files[rel] = digest(path)
            else:
                raise ValueError(f"unsupported file type: {rel}")

    visit(root)
    return files, blocked, retained, spellings


def official(root):
    if not root.is_dir() or linked(root):
        raise ValueError("source/baseline must be a plain skills directory")
    skills = {}
    for path in sorted(root.iterdir()):
        if path.name.lower() in PRIVATE:
            raise ValueError("private/git content found directly in skills source")
        if linked(path):
            raise ValueError(f"source contains link/reparse path: {path.name}")
        if not path.is_dir():
            continue
        if not NAME.fullmatch(path.name) or len(path.name) >= 64:
            raise ValueError(f"unexpected skill directory: {path.name}")
        entry = path / "SKILL.md"
        if not entry.is_file() or linked(entry):
            raise ValueError(f"missing/plain SKILL.md required: {path.name}")
        text = entry.read_text(encoding="utf-8-sig")
        header = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|\Z)", text, re.S)
        if not header:
            raise ValueError(f"missing frontmatter: {path.name}")
        name = re.search(r"^name:\s*[\"']?([a-z0-9-]+)[\"']?\s*$", header[1], re.M)
        description = re.search(r"^description:[ \t]*(.*)$", header[1], re.M)
        has_description = bool(description and description[1].strip())
        if has_description and description[1].strip() in ("|", ">", "|-", ">-", "|+", ">+"):
            has_description = bool(re.match(r"\n[ \t]+\S", header[1][description.end():]))
        if not name or name[1] != path.name or not has_description:
            raise ValueError(f"invalid skill name/description: {path.name}")
        skills[path.name] = inventory(path, strict=True)[0]
    if not skills:
        raise ValueError("no official huawo skills found")
    return skills


def compare(source, target, baseline=None):
    # Deliberately do not resolve() before checking link/reparse status.
    source = Path(os.path.abspath(source.expanduser()))
    target = Path(os.path.abspath(target.expanduser()))
    new_skills = official(source)
    old_skills = official(Path(os.path.abspath(baseline.expanduser()))) if baseline else {}
    if present(target) and (linked(target) or not target.is_dir()):
        raise ValueError("target root must be an approved plain directory")
    if source == target or source.is_relative_to(target) or target.is_relative_to(source):
        raise ValueError("source and target must be separate, non-nested directories")
    output = {"source": str(source), "target": str(target), "read_only": True,
              "source_identity_verified": False, "skills": [],
              "retired_detection": "verified_baseline_only" if baseline else "unavailable_without_baseline",
              "retained_skills": []}
    for name, wanted in new_skills.items():
        dest = target / name
        item = {"name": name, "same": [], "add": [], "replace": [],
                "conflicts": [], "retained": [], "files": []}
        output["skills"].append(item)
        if present(dest) and (linked(dest) or not dest.is_dir()):
            item["conflicts"].append({"path": ".", "reason": "linked/blocked skill root"})
            continue
        existing, blocked, private, spellings = inventory(dest, strict=False) if dest.is_dir() else ({}, [], [], {})
        item["retained"] = sorted(set(existing) - set(wanted)) + private
        # Even an unrelated reparse point prevents treating a skill as a safe write unit.
        item["conflicts"].extend({"path": p, "reason": "linked/reparse path"} for p in blocked)
        old = old_skills.get(name, {})
        for rel, sha in wanted.items():
            before = existing.get(rel)
            variants = spellings.get(rel.casefold(), [])
            if before is None and len(variants) == 1:
                before = existing.get(variants[0])
            file = {"path": rel, "source_sha256": sha, "before_sha256": before}
            item["files"].append(file)
            parts = Path(rel).parts
            ancestors = [Path(*parts[:n]).as_posix() for n in range(1, len(parts))]
            case_alias = any(spellings.get(p.casefold(), []) not in ([], [p]) for p in [*ancestors, rel])
            if case_alias:
                status = "conflicts"
                item[status].append({"path": rel, "reason": "case-only path alias; preserve and resolve explicitly"})
            elif (rel in blocked or any(p in blocked or p in existing for p in ancestors)
                    or (present(dest / rel) and (dest / rel).is_dir())):
                status = "conflicts"
                item[status].append({"path": rel, "reason": "file/directory or linked ancestor conflict"})
            elif before == sha:
                status = "same"
                item[status].append(rel)
            elif before is None:
                status = "add"
                item[status].append(rel)
            elif old.get(rel) == before:
                status = "replace"
                item[status].append(rel)
            else:
                status = "conflicts"
                item[status].append({"path": rel, "reason": "local change or unknown old version"})
            file["status"] = status
        item["safe_to_write"] = not item["conflicts"]
        item["official_files_match"] = len(item["same"]) == len(wanted) and not item["conflicts"]
    for name in sorted(set(old_skills) - set(new_skills)):
        if present(target / name):
            output["retained_skills"].append({"name": name, "path": str(target / name),
                "status": "removed_upstream_preserved", "host_impact": "needs_review",
                "reason": "in verified baseline, absent from new source; not deleted or traversed"})
    output["legacy_entries_pending"] = bool(output["retained_skills"])
    output["all_official_files_match"] = all(s.get("official_files_match", False) for s in output["skills"])
    output["conflicting_skills"] = [s["name"] for s in output["skills"] if s["conflicts"]]
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.source, args.target, args.baseline)
    except (OSError, ValueError, UnicodeError) as error:
        print(json.dumps({"ok": False, "read_only": True, "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
