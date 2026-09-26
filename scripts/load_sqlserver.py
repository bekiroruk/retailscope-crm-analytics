"""Optional local SQL Server import. Never invoked by the analytics pipeline.

Uses an existing dedicated database and a fixed retailscope schema. Refuses to
overwrite populated tables. Create another dedicated database for another run.
Connection string comes only from RETAILSCOPE_ODBC and is never logged.
"""
import csv
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TABLES = ["dim_customer", "dim_product", "dim_date", "fact_sales", "customer_scores"]
BOOLS = {"marketing_consent", "identity_review_required"}


def main():
    import pyodbc
    value = os.environ.get("RETAILSCOPE_ODBC")
    if not value:
        raise SystemExit("Set RETAILSCOPE_ODBC to a connection string for a dedicated existing database.")
    paths = {name:ROOT / "outputs" / "marts" / f"{name}.csv" for name in TABLES}
    if not all(p.is_file() for p in paths.values()):
        raise SystemExit("Run python -m retailscope all first.")
    connection = pyodbc.connect(value, autocommit=False)
    try:
        cursor = connection.cursor()
        database = cursor.execute("SELECT DB_NAME()").fetchone()[0]
        if database.casefold() in {"master", "tempdb", "model", "msdb"}:
            raise ValueError("Refusing a SQL Server system database.")
        ddl = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
        for batch in re.split(r"^\s*GO\s*$", ddl, flags=re.MULTILINE | re.IGNORECASE):
            if batch.strip():
                cursor.execute(batch)
        for name in TABLES:
            # Table identifiers are a fixed internal allowlist, not user input.
            if cursor.execute(f"SELECT COUNT_BIG(*) FROM retailscope.[{name}]").fetchone()[0]:
                raise ValueError("Target tables already contain data. Use a new dedicated database; no data was overwritten.")
        for name in TABLES:
            with paths[name].open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                columns = reader.fieldnames
                # Compare CSV columns against database schema before building identifiers.
                allowed = {r[0] for r in cursor.execute(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='retailscope' AND TABLE_NAME=?", name)}
                if not columns or len(set(columns)) != len(columns) or set(columns) != allowed:
                    raise ValueError(f"Column mismatch in {name}.")
                sql = f"INSERT INTO retailscope.[{name}] (" + ",".join(f"[{c}]" for c in columns) + ") VALUES (" + ",".join("?" for _ in columns) + ")"
                batch, count = [], 0
                for row in reader:
                    values = [None if row[c] == "" else (1 if row[c].lower() in {"1", "true"} else 0) if c in BOOLS else row[c] for c in columns]
                    batch.append(values)
                    if len(batch) == 1000:
                        cursor.executemany(sql, batch)
                        count += len(batch)
                        batch = []
                if batch:
                    cursor.executemany(sql, batch)
                    count += len(batch)
                actual = cursor.execute(f"SELECT COUNT_BIG(*) FROM retailscope.[{name}]").fetchone()[0]
                if actual != count:
                    raise ValueError(f"Row count mismatch in {name}.")
                print(f"{name}: {count} rows prepared")
        connection.commit()
        print("All five tables committed together.")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        main()
    except ImportError:
        sys.exit("Install requirements-sqlserver.txt and Microsoft ODBC Driver 18 first.")
