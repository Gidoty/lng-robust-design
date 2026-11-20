"""Build a Zenodo-ready archive of a results run. It does NOT upload anything.

    python tools/zenodo_archive.py --run-id <github run id> [--results results/<run_id>] [--shards-dir shards] [--out zenodo_<run_id>]

Output folder contains: the code at the run's commit (git archive), the results package, optional evaluation shards you downloaded
from the workflow artifacts (gh run download <id> -p 'shards-*'), CITATION.cff, LICENSE, LICENSE-DATA, a zenodo.json metadata file and
SHA256SUMS. Upload the folder (or its .zip) by hand through zenodo.org when you are ready."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(p: Path):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--results")
    ap.add_argument("--shards-dir")
    ap.add_argument("--out")
    ap.add_argument("--commit", default="HEAD")
    a = ap.parse_args()
    out = Path(a.out or f"zenodo_{a.run_id}")
    if out.exists():
        raise SystemExit(f"{out} exists; remove it first")
    out.mkdir(parents=True)
    commit = subprocess.check_output(["git", "rev-parse", a.commit], cwd=ROOT).decode().strip()
    code_zip = out / f"lng-robust-design-code-{commit[:10]}.zip"
    subprocess.check_call(["git", "archive", "--format=zip", f"--output={code_zip}", commit], cwd=ROOT)
    res = Path(a.results or ROOT / "results" / a.run_id)
    if res.exists():
        shutil.copytree(res, out / "results_package")
    else:
        print(f"warning: {res} not found; no results package included")
    if a.shards_dir and Path(a.shards_dir).exists():
        shutil.copytree(a.shards_dir, out / "evaluation_shards")
    for f in ("CITATION.cff", "LICENSE", "LICENSE-DATA"):
        shutil.copy(ROOT / f, out / f)
    meta = dict(title="lng-robust-design: code, data and results for the price of robustness in modular LNG refrigeration",
                upload_type="software", description="Engine, composition register, benchmark inputs, results package and evaluation shards of GitHub Actions run "
                + a.run_id + ". Commit " + commit + ".", creators=[dict(name="Fadoyeni, Tunji"), dict(name="Owhonda, Gideon")],
                license="MIT (code); CC-BY-4.0 (data)", keywords=["LNG", "robust optimisation", "CVaR", "Niger Delta"],
                related_identifiers=[dict(identifier="https://github.com/Gidoty/lng-robust-design", relation="isSupplementTo", resource_type="software")])
    (out / "zenodo.json").write_text(json.dumps(meta, indent=2))
    sums = {str(p.relative_to(out)): sha256(p) for p in sorted(out.rglob("*")) if p.is_file()}
    (out / "SHA256SUMS").write_text("".join(f"{h}  {n}\n" for n, h in sums.items()))
    zpath = Path(str(out) + ".zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(out.parent))
    print(f"archive folder: {out}\narchive zip:    {zpath}\nfiles: {len(sums)}   (nothing was uploaded)")


if __name__ == "__main__":
    main()
