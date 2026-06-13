#!/usr/bin/env python3
import json
import sys
from pathlib import Path

project = Path.cwd()
pack = project.parent / "learnforge_v4_all_requirements_test_gated_goal_pack"
req_file = pack / "requirements" / "requirements.json"
if not req_file.exists():
    req_file = project / "requirements" / "requirements.json"
results_file = project / "validation" / "requirement_results.json"

req = json.loads(req_file.read_text(encoding="utf-8"))["requirements"]
results = json.loads(results_file.read_text(encoding="utf-8"))
if isinstance(results, dict) and "results" in results:
    results = results["results"]
by_id = {r["requirement_id"]: r for r in results}
missing = []
failed = []
extra = sorted(set(by_id) - {item["id"] for item in req})
duplicates = sorted({rid for rid in [r.get("requirement_id") for r in results] if [r.get("requirement_id") for r in results].count(rid) > 1})


def evidence_exists(path_text: str) -> bool:
    return (project / path_text).exists() or (pack / path_text).exists()


for item in req:
    rid = item["id"]
    r = by_id.get(rid)
    if not r:
        missing.append(rid)
    elif r.get("status") != "pass":
        failed.append((rid, r.get("status"), r.get("notes")))
    elif not r.get("evidence"):
        failed.append((rid, "missing_evidence", r.get("notes")))
    elif not r.get("tests"):
        failed.append((rid, "missing_tests", r.get("notes")))
    else:
        absent = [path for path in r.get("evidence", []) if not evidence_exists(path)]
        if absent:
            failed.append((rid, f"missing_evidence_paths:{absent}", r.get("notes")))

blocked = project / "BLOCKED_REAL_INTEGRATION_REPORT.md"
if blocked.exists():
    blocked_text = blocked.read_text(encoding="utf-8")
    if "Status: not complete for external readiness." not in blocked_text:
        failed.append(("REPORT-002", "blocked_report_semantics", "Blocked report must not mark external readiness complete."))

if missing or failed or extra or duplicates:
    print("Requirement validation failed")
    print("Missing:", missing)
    print("Extra:", extra)
    print("Duplicates:", duplicates)
    print("Failed:", failed)
    sys.exit(1)
print(f"All {len(req)} requirements pass")
