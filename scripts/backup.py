"""Consistent SQLite backup: python scripts/backup.py /data/app.db /backups/DATE.db"""

import argparse
import sqlite3
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path)
parser.add_argument("destination", type=Path)
args = parser.parse_args()
if args.destination.exists():
    parser.error("destination already exists; choose a new backup path")
args.destination.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(args.source.resolve().as_uri() + "?mode=ro", uri=True) as source:
    with sqlite3.connect(args.destination) as destination:
        source.backup(destination)
        result = destination.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError("Backup integrity check failed")
args.destination.chmod(0o600)
print(f"Backup verified: {args.destination}")
