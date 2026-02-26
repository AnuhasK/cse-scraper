import argparse
import csv
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent


def resolve_audit_file(user_value: Optional[str]) -> Path:
    if user_value:
        audit_file = Path(user_value)
        if audit_file.is_file():
            return audit_file
        raise FileNotFoundError(f"Audit file not found: {audit_file}")

    candidates = sorted(
        BASE_DIR.glob("rearrange_financial_pdfs_audit_*.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(
            "No rearrange audit file found. Provide one with --audit-file."
        )
    return candidates[0]


def load_rollback_rows(audit_file: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with audit_file.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            status = (row.get("status") or "").strip().upper()
            old_path = (row.get("old_path") or "").strip()
            new_path = (row.get("new_path") or "").strip()

            if status != "RENAMED":
                continue
            if not old_path or not new_path:
                continue

            rows.append(
                {
                    "old_path": old_path,
                    "new_path": new_path,
                    "status": status,
                    "match_method": (row.get("match_method") or "").strip(),
                }
            )
    return rows


def write_log(log_rows: List[Dict[str, str]], log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "old_path",
                "new_path",
                "result",
                "reason",
                "match_method",
            ],
        )
        writer.writeheader()
        for row in log_rows:
            writer.writerow(row)


def run_rollback(audit_file: Path, apply_changes: bool, overwrite_old: bool) -> int:
    rollback_rows = load_rollback_rows(audit_file)
    if not rollback_rows:
        print("No RENAMED rows found in the audit file.")
        return 0

    log_rows: List[Dict[str, str]] = []
    moved_back = 0
    skipped_new_missing = 0
    skipped_old_exists = 0
    errors = 0

    for row in rollback_rows:
        old_path = Path(row["old_path"])
        new_path = Path(row["new_path"])

        if not new_path.exists():
            skipped_new_missing += 1
            log_rows.append(
                {
                    "old_path": str(old_path),
                    "new_path": str(new_path),
                    "result": "SKIPPED_NEW_MISSING",
                    "reason": "new_path not found",
                    "match_method": row["match_method"],
                }
            )
            continue

        if old_path.exists() and not overwrite_old:
            skipped_old_exists += 1
            log_rows.append(
                {
                    "old_path": str(old_path),
                    "new_path": str(new_path),
                    "result": "SKIPPED_OLD_EXISTS",
                    "reason": "old_path already exists",
                    "match_method": row["match_method"],
                }
            )
            continue

        if apply_changes:
            try:
                old_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(new_path), str(old_path))
                moved_back += 1
                log_rows.append(
                    {
                        "old_path": str(old_path),
                        "new_path": str(new_path),
                        "result": "ROLLED_BACK",
                        "reason": "",
                        "match_method": row["match_method"],
                    }
                )
            except Exception as exc:
                errors += 1
                log_rows.append(
                    {
                        "old_path": str(old_path),
                        "new_path": str(new_path),
                        "result": "ERROR",
                        "reason": str(exc),
                        "match_method": row["match_method"],
                    }
                )
        else:
            moved_back += 1
            log_rows.append(
                {
                    "old_path": str(old_path),
                    "new_path": str(new_path),
                    "result": "WOULD_ROLLBACK",
                    "reason": "",
                    "match_method": row["match_method"],
                }
            )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = BASE_DIR / f"rollback_from_audit_{timestamp}.csv"
    write_log(log_rows, log_file)

    print("=" * 70)
    print(f"Mode: {'APPLY' if apply_changes else 'DRY-RUN'}")
    print(f"Audit file: {audit_file}")
    print(f"Rows considered (RENAMED): {len(rollback_rows)}")
    print(f"Moved back: {moved_back}")
    print(f"Skipped (new missing): {skipped_new_missing}")
    print(f"Skipped (old exists): {skipped_old_exists}")
    print(f"Errors: {errors}")
    print(f"Rollback log: {log_file}")
    print("=" * 70)

    return 0 if errors == 0 else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rollback PDF moves done by rearrange_financial_pdfs.py using its audit CSV."
    )
    parser.add_argument(
        "--audit-file",
        default=None,
        help="Path to rearrange_financial_pdfs_audit_*.csv. Defaults to latest in this folder.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply filesystem changes. If omitted, runs in dry-run mode.",
    )
    parser.add_argument(
        "--overwrite-old",
        action="store_true",
        help="Allow overwrite when old_path already exists.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit_file = resolve_audit_file(args.audit_file)
    return run_rollback(
        audit_file=audit_file,
        apply_changes=args.apply,
        overwrite_old=args.overwrite_old,
    )


if __name__ == "__main__":
    raise SystemExit(main())