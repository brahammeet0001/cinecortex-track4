"""Pre-upload checker for the final TEAM_ID/ package (Track 04).

Run from the package root (the folder that holds run.sh):
  PYTHONPATH=code python code/tools/check_package.py --manifest data_manifest/manifest.csv \
      --classes data_manifest/supported_classes.json [--team-id YOUR_ID] [--final]

Without --final, missing outputs and a placeholder team_id are WARNINGS (work in progress).
With --final they are ERRORS. Exit code 1 if any error.

Checks: required layout, run.sh executable, no video/ground-truth/test files inside, one valid
JSON per manifest video (official schema), one identical team_id, no manifest video IDs hardcoded
in code/ or run.sh (hardcoding = disqualification), and run-time network/install calls (warning).
"""
import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluation.validate_extra import check, load_manifest, load_vocab  # noqa: E402

import json  # noqa: E402

REQUIRED_FILES = ("run.sh", "requirements.txt", "README.md")
REQUIRED_DIRS = ("code", "weights", "outputs")
PLACEHOLDER_IDS = {"", "TEAM_ID", "T07", "team_alpha", "team", "TEAM_NAME", "YOUR_TEAM_ID"}
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache"}
STRAY_AT_ROOT = ("durations.json", "results.json", "gt", "logs", "PATCH_APPLY_INSTRUCTIONS.txt",
                 ".venv", "data")
NET_PATTERN = re.compile(r"urlopen|urllib\.request|requests\.(get|post)|torch\.hub|from_pretrained|"
                         r"hf_hub|wget |curl |git clone|pip install")
BIG_FILE_MB = 200


def _walk(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            yield Path(dp) / fn


def _lines(path):
    try:
        return path.read_text(errors="ignore").splitlines()
    except Exception:
        return []


def run_checks(root, manifest=None, classes=None, team_id=None, final=False):
    root = Path(root)
    errs, warns = [], []
    soft = errs if final else warns

    # 1. layout
    for f in REQUIRED_FILES:
        if not (root / f).is_file():
            errs.append(f"missing file: {f}")
    for d in REQUIRED_DIRS:
        if not (root / d).is_dir():
            errs.append(f"missing folder: {d}/")
    run_sh = root / "run.sh"
    if run_sh.is_file() and not os.access(run_sh, os.X_OK):
        errs.append("run.sh is not executable (run: chmod +x run.sh)")
    if team_id and final and root.resolve().name != team_id:
        warns.append(f"package folder is named '{root.resolve().name}', expected '{team_id}'")

    # 2. forbidden / stray content
    for name in STRAY_AT_ROOT:
        if (root / name).exists():
            warns.append(f"remove from package: {name}")
    for p in _walk(root):
        rel = p.relative_to(root)
        if p.suffix.lower() in VIDEO_EXT:
            # data/ etc. are local-only folders (git-ignored); they must not ship, but are
            # only a warning until --final. Videos anywhere else are always an error.
            (soft if rel.parts[0] in STRAY_AT_ROOT else errs).append(f"video file inside package: {rel}")
        elif p.stat().st_size > BIG_FILE_MB * 1024 * 1024:
            warns.append(f"large file ({p.stat().st_size // 2**20} MB): {rel}")

    # 3. outputs
    vocab = load_vocab(classes) if classes else None
    man = load_manifest(manifest) if manifest else {}
    out_dir = root / "outputs"
    files = sorted(out_dir.glob("*.json")) if out_dir.is_dir() else []
    team_ids = set()
    for f in files:
        try:
            data = json.load(open(f))
        except Exception as ex:
            errs.append(f"outputs/{f.name}: invalid JSON ({ex})")
            continue
        if isinstance(data, dict) and isinstance(data.get("team_id"), str):
            team_ids.add(data["team_id"])
        e, _w = check(data, f.stem, man.get(f.stem), vocab)
        errs.extend(f"outputs/{f.name}: {m}" for m in e)
    if man:
        stems = {f.stem for f in files}
        missing, extra = sorted(set(man) - stems), sorted(stems - set(man))
        if missing:
            soft.append(f"{len(missing)}/{len(man)} manifest videos have no output JSON "
                        f"(e.g. {', '.join(missing[:3])})")
        if extra:
            soft.append(f"{len(extra)} output file(s) not in manifest (e.g. {', '.join(extra[:3])})")
    if len(team_ids) > 1:
        errs.append(f"team_id differs across outputs: {sorted(team_ids)}")
    for t in team_ids:
        if t in PLACEHOLDER_IDS:
            soft.append(f"team_id is a placeholder: '{t}'")
        if team_id and t != team_id:
            errs.append(f"team_id '{t}' != expected '{team_id}'")

    # 4. hardcoded video IDs in code
    code_files = [p for p in _walk(root / "code")] if (root / "code").is_dir() else []
    if run_sh.is_file():
        code_files.append(run_sh)
    # skip this checker wherever it sits (its own regex patterns would match itself)
    code_files = [p for p in code_files
                  if p.suffix in {".py", ".sh", ".txt", ".json", ".yaml", ".yml", ""}
                  and p.name != "check_package.py"]
    if man:
        ids = sorted(man, key=len, reverse=True)
        rx = re.compile(r"(?<![A-Za-z0-9_-])(" + "|".join(re.escape(i) for i in ids) + r")(?![A-Za-z0-9_-])")
        hits = []
        for p in code_files:
            for n, line in enumerate(_lines(p), 1):
                m = rx.search(line)
                if m:
                    hits.append(f"{p.relative_to(root)}:{n} contains manifest ID '{m.group(1)}'")
        errs.extend(hits[:10])
        if len(hits) > 10:
            errs.append(f"... and {len(hits) - 10} more hardcoded-ID hits")

    # 5. run-time network / install calls
    nhits = []
    for p in code_files:
        if p.suffix in {".py", ".sh", ""}:
            for n, line in enumerate(_lines(p), 1):
                if line.strip().startswith("#"):
                    continue
                if NET_PATTERN.search(line):
                    nhits.append(f"{p.relative_to(root)}:{n}: {line.strip()[:90]}")
    warns.extend(f"possible run-time download/install: {h}" for h in nhits[:10])

    # 6. requirements pinned
    req = root / "requirements.txt"
    if req.is_file():
        for line in _lines(req):
            s = line.strip()
            if s and not s.startswith("#") and "==" not in s:
                warns.append(f"requirements.txt not pinned: {s}")
    return errs, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--classes", default=None)
    ap.add_argument("--team-id", default=None)
    ap.add_argument("--final", action="store_true")
    a = ap.parse_args()
    errs, warns = run_checks(a.root, a.manifest, a.classes, a.team_id, a.final)
    for w in warns:
        print("WARN ", w)
    for e in errs[:40]:
        print("ERROR", e)
    if len(errs) > 40:
        print(f"ERROR ... and {len(errs) - 40} more")
    print(f"\n{len(errs)} error(s), {len(warns)} warning(s)  ->  {'FAIL' if errs else 'PASS'}"
          f"{'' if a.final else '  (not --final: placeholders/missing outputs are warnings)'}")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
