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
    ap.add_argument("--zip", help="also write this zip file next to the folder and print its size and SHA-256")
    a = ap.parse_args()
    out = Path(a.out or f"zenodo_{a.run_id}").resolve()
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
    prov_p = res / "provenance.json"
    run_commit = json.loads(prov_p.read_text()).get("commit_hash", "") if prov_p.exists() else ""
    desc = ("Models, Niger Delta associated-gas composition register and results for the manuscript on risk-averse design of modular LNG refrigeration cycles "
            "(single mixed refrigerant, single and dual nitrogen expander) under feed-composition variability. Contents: the engine code at commit " + commit
            + " (code licence: MIT), the results package of GitHub Actions run " + a.run_id + (" (computed at commit " + run_commit + ")" if run_commit else "") + " (tables, figures, provenance.json, RESULTS_SUMMARY.md)"
            + (", and the evaluation shards of that run" if a.shards_dir and Path(a.shards_dir).exists() else "")
            + ". Data and results licence: CC-BY-4.0. Source repository: https://github.com/Gidoty/lng-robust-design.")
    aff = "NLNG Centre for Gas, Refining and Petrochemical Engineering, University of Port Harcourt"
    meta = dict(title="lng-robust-design: models, Niger Delta composition register and results for risk-averse design of modular LNG refrigeration cycles",
                upload_type="dataset", description=desc,
                creators=[dict(name="Fadoyeni, Tunji", affiliation=aff), dict(name="Owhonda, Gideon", affiliation=aff)],
                license="cc-by-4.0", keywords=["LNG", "robust optimisation", "CVaR", "Niger Delta", "nitrogen expander cycle", "mixed refrigerant"],
                related_identifiers=[dict(identifier="https://github.com/Gidoty/lng-robust-design", relation="isSupplementTo", scheme="url", resource_type="software")])
    (out / "zenodo.json").write_text(json.dumps(meta, indent=2))
    sums = {str(p.relative_to(out)): sha256(p) for p in sorted(out.rglob("*")) if p.is_file()}
    (out / "SHA256SUMS").write_text("".join(f"{h}  {n}\n" for n, h in sums.items()))
    zpath = Path(a.zip) if a.zip else Path(str(out) + ".zip")
    top = zpath.stem                      # folder inside the zip, so that extracting does not spread files
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file():
                z.write(p, Path(top) / p.relative_to(out))
    tops = sorted({q.parts[0] if len(q.parts) > 1 else q.name + " (file)" for q in (p.relative_to(out) for p in out.rglob("*") if p.is_file())})
    print(f"archive folder: {out}\narchive zip:    {zpath}\nfiles: {len(sums)}   (nothing was uploaded)")
    print(f"zip size: {zpath.stat().st_size} bytes   sha256: {sha256(zpath)}")
    print(f"inside the zip, under '{top}/': " + ", ".join(tops))
    print("evaluation shards included: " + ("yes" if (out / "evaluation_shards").exists() else "NO"))

if __name__ == "__main__":
    main()
