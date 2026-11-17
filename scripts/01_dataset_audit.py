"""
Dataset inventory for the AI IT Helpdesk research project.
Read-only: does not modify the SQLite database or knowledge-base files.
Run from the project root:
    python scripts/01_dataset_audit.py
Outputs aggregate metadata only; it does NOT export ticket descriptions or user details.
"""
from pathlib import Path
import sqlite3, csv, json, hashlib
from collections import Counter
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "helpdesk.db"
DATA_DIR = ROOT / "data"
OUT = ROOT / "experiment_artifacts"
OUT.mkdir(exist_ok=True)

def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

report = {
    "generated_at_local": datetime.now().astimezone().isoformat(),
    "project_root": str(ROOT),
    "database_path_exists": DB.exists(),
    "knowledge_data_directory_exists": DATA_DIR.exists(),
    "privacy_note": "Aggregate metadata only; no ticket text, usernames, emails, or credentials exported."
}

# SQLite: open read-only so this script cannot alter project data.
if DB.exists():
    uri = DB.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    tables = [r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )]
    report["sqlite_tables"] = tables
    table_reports = {}
    for table in tables:
        # Table names originate from sqlite_master, not user input.
        count = conn.execute(f'SELECT COUNT(*) AS n FROM "{table}"').fetchone()["n"]
        cols = [r["name"] for r in conn.execute(f'PRAGMA table_info("{table}")')]
        table_reports[table] = {"row_count": count, "columns": cols}
    report["tables"] = table_reports

    if "tickets" in tables:
        cols = set(table_reports["tickets"]["columns"])
        ticket_count = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        report["tickets"] = {"row_count": ticket_count, "columns": sorted(cols)}
        for col in ["category", "priority", "status", "sentiment", "urgency"]:
            if col in cols:
                rows = conn.execute(
                    f'SELECT COALESCE(CAST("{col}" AS TEXT), "[NULL]") AS value, COUNT(*) AS n '
                    f'FROM tickets GROUP BY "{col}" ORDER BY n DESC, value'
                ).fetchall()
                report["tickets"][f"{col}_distribution"] = [
                    {"value": r["value"], "count": r["n"]} for r in rows
                ]
        for col in ["ticket_id", "title", "description", "category", "priority", "status"]:
            if col in cols:
                report["tickets"].setdefault("null_counts", {})[col] = conn.execute(
                    f'SELECT COUNT(*) FROM tickets WHERE "{col}" IS NULL OR TRIM(CAST("{col}" AS TEXT)) = ""'
                ).fetchone()[0]
        if "ticket_id" in cols:
            report["tickets"]["duplicate_ticket_ids"] = conn.execute(
                "SELECT COUNT(*) FROM (SELECT ticket_id FROM tickets GROUP BY ticket_id HAVING COUNT(*) > 1)"
            ).fetchone()[0]
        if "created_at" in cols:
            row = conn.execute("SELECT MIN(created_at), MAX(created_at) FROM tickets").fetchone()
            report["tickets"]["created_at_min"] = row[0]
            report["tickets"]["created_at_max"] = row[1]
    conn.close()
else:
    report["database_error"] = "Database file not found at database/helpdesk.db. Check database_manager.py and update DB path in this script if needed."

# TXT knowledge corpus: filenames, sizes, hashes and text quality only.
kb_rows = []
if DATA_DIR.exists():
    for p in sorted(DATA_DIR.glob("*.txt")):
        raw = p.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        kb_rows.append({
            "filename": p.name,
            "size_bytes": len(raw),
            "characters": len(text),
            "words_approx": len(text.split()),
            "blank": not text.strip(),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
report["knowledge_base"] = {
    "directory": str(DATA_DIR),
    "txt_document_count": len(kb_rows),
    "total_characters": sum(x["characters"] for x in kb_rows),
    "total_words_approx": sum(x["words_approx"] for x in kb_rows),
    "empty_document_count": sum(x["blank"] for x in kb_rows),
    "unique_content_hashes": len({x["sha256"] for x in kb_rows}),
    "duplicate_content_count": len(kb_rows) - len({x["sha256"] for x in kb_rows}),
}
write_csv(OUT / "knowledge_base_inventory.csv", kb_rows,
          ["filename","size_bytes","characters","words_approx","blank","sha256"])
(OUT / "dataset_inventory.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
)
print("Audit complete.")
print(f"Database found: {report['database_path_exists']}")
print(f"Ticket rows: {report.get('tickets', {}).get('row_count', 'N/A')}")
print(f"TXT knowledge documents: {report['knowledge_base']['txt_document_count']}")
print(f"Aggregate report: {OUT / 'dataset_inventory.json'}")
print(f"KB inventory: {OUT / 'knowledge_base_inventory.csv'}")
print("No ticket descriptions or user identity fields were exported.")
