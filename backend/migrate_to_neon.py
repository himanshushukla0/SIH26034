"""
Migrate local SQLite inspection audits to Neon PostgreSQL.
"""

import asyncio
import sqlite3
from datetime import datetime, timezone
from sqlalchemy import select
from backend.database import async_session, init_db
from backend.models import Audit, Violation, AuditInputType, AuditStatus, ViolationSeverity


async def migrate():
    print("Ensuring Neon DB schema is initialized...")
    await init_db()

    sqlite_conn = sqlite3.connect("lmpc_audits.db")
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    sqlite_cur.execute("SELECT * FROM audits;")
    sqlite_audits = sqlite_cur.fetchall()
    print(f"Found {len(sqlite_audits)} audits in SQLite.")

    sqlite_cur.execute("SELECT * FROM violations;")
    sqlite_violations = sqlite_cur.fetchall()
    print(f"Found {len(sqlite_violations)} violations in SQLite.")

    async with async_session() as session:
        for row in sqlite_audits:
            existing = await session.get(Audit, row["id"])
            if existing:
                print(f"Audit {row['id'][:8]} already exists in Neon. Skipping.")
                continue

            created_at_val = row["created_at"]
            if isinstance(created_at_val, str):
                try:
                    created_at_dt = datetime.fromisoformat(created_at_val)
                except Exception:
                    created_at_dt = datetime.now(timezone.utc)
            else:
                created_at_dt = datetime.now(timezone.utc)

            input_type_val = row["input_type"]
            try:
                input_type_enum = AuditInputType(input_type_val)
            except Exception:
                input_type_enum = AuditInputType.IMAGE

            status_val = row["status"]
            try:
                status_enum = AuditStatus(status_val)
            except Exception:
                status_enum = AuditStatus.COMPLETED

            audit = Audit(
                id=row["id"],
                created_at=created_at_dt,
                input_type=input_type_enum,
                source_url=row["source_url"],
                image_path=row["image_path"],
                status=status_enum,
                compliance_score=row["compliance_score"],
                overall_status=row["overall_status"],
                total_checks=row["total_checks"] or 10,
                passed_checks=row["passed_checks"] or 0,
                failed_checks=row["failed_checks"] or 0,
                product_name=row["product_name"],
                manufacturer=row["manufacturer"],
                mrp=row["mrp"],
                net_quantity=row["net_quantity"],
                report_pdf_path=row["report_pdf_path"],
                raw_extractions_json=row["raw_extractions_json"],
            )
            session.add(audit)

        for v in sqlite_violations:
            sev_val = str(v["severity"] or "major").lower()
            if "crit" in sev_val:
                sev_enum = ViolationSeverity.CRITICAL
            elif "min" in sev_val:
                sev_enum = ViolationSeverity.MINOR
            else:
                sev_enum = ViolationSeverity.MAJOR

            violation = Violation(
                audit_id=v["audit_id"],
                rule_reference=v["rule_reference"],
                act_section=v["act_section"],
                punishment_section=v["punishment_section"],
                statutory_penalty=v["statutory_penalty"],
                legal_proof_summary=v["legal_proof_summary"],
                field_name=v["field_name"],
                severity=sev_enum,
                description=v["description"],
                expected_value=v["expected_value"],
                found_value=v["found_value"],
                is_discrepancy=bool(v["is_discrepancy"]),
            )
            session.add(violation)

        await session.commit()
        print("Successfully migrated records to Neon PostgreSQL!")

    sqlite_conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
