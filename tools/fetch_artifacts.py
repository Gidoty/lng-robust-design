"""Download artifacts of ANOTHER workflow run of this repository by name pattern (fnmatch), into <out>/<artifact name>/.

actions/download-artifact lists only the first 100 artifacts of another run, so a run with several hundred artifacts (the full study has
more than 300) silently misses most of them. This script pages through the whole list with the GitHub CLI (`gh api --paginate`),
which is installed on GitHub-hosted runners; it needs GH_TOKEN (the workflow token with actions: read).

    python tools/fetch_artifacts.py --run-id 44682889025 --out work --require 'unit-nominal-smr' --require 'unit-surrogate-smr' --optional 'shards-robust-smr-*'

A --require pattern that matches no artifact is an error (exit 1). Expired artifacts are reported and also an error for --require."""
from __future__ import annotations

import argparse
import fnmatch
import io
import os
import subprocess
import sys
import zipfile
from pathlib import Path


def gh(*args, binary=False):
    r = subprocess.run(["gh", *args], capture_output=True, check=False)
    if r.returncode != 0:
        raise SystemExit(f"gh {' '.join(args)} failed: {r.stderr.decode()[:500]}")
    return r.stdout if binary else r.stdout.decode()


def list_artifacts(repo: str, run_id: str):
    out = gh("api", "--paginate", f"repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100", "--jq", '.artifacts[] | [.id, .name, .expired, .size_in_bytes] | @tsv')
    rows = []
    for line in out.splitlines():
        i, name, expired, size = line.split("\t")
        rows.append(dict(id=int(i), name=name, expired=expired == "true", size=int(size)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", default="work")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    ap.add_argument("--require", action="append", default=[], help="pattern that must match at least one artifact")
    ap.add_argument("--optional", action="append", default=[], help="pattern that may match nothing")
    a = ap.parse_args()
    if not a.repo:
        raise SystemExit("--repo or GITHUB_REPOSITORY is needed")
    arts = list_artifacts(a.repo, a.run_id)
    print(f"run {a.run_id}: {len(arts)} artifacts listed")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    missing = []
    for kind, pats in (("require", a.require), ("optional", a.optional)):
        for pat in pats:
            hit = [x for x in arts if fnmatch.fnmatch(x["name"], pat)]
            ok = [x for x in hit if not x["expired"]]
            if not ok:
                msg = f"pattern '{pat}': {'EXPIRED' if hit else 'no artifact'}"
                print(msg)
                if kind == "require":
                    missing.append(pat)
                continue
            for x in ok:
                data = gh("api", f"repos/{a.repo}/actions/artifacts/{x['id']}/zip", binary=True)
                dest = out / x["name"]
                dest.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    z.extractall(dest)
                print(f"  {x['name']}  ({x['size']} bytes)")
    if missing:
        print(f"MISSING required artifacts: {missing}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
