"""Transactional SQL Server loader for outputs/real/marts.

Requires a dedicated existing database and RETAILSCOPE_ODBC. It refuses system
databases and populated target tables, and never logs the connection string.
"""
import csv
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TABLES = ["dim_customer", "dim_product", "dim_date", "fact_sales", "customer_scores"]
BOOLS = {"activation_eligible"}
SCHEMA = "retailscope_uci"


def main():
    import pyodbc
    connection_string = os.environ.get("RETAILSCOPE_ODBC")
    if not connection_string:
        raise SystemExit("Set RETAILSCOPE_ODBC for a dedicated existing SQL Server database.")
    paths = {name: ROOT / "outputs" / "real" / "marts" / f"{name}.csv" for name in TABLES}
    if not all(path.is_file() for path in paths.values()):
        raise SystemExit("Run python -m retailscope uci --input <workbook.xlsx> first.")
    connection = pyodbc.connect(connection_string, autocommit=False)
    try:
        cursor = connection.cursor()
        database = cursor.execute("SELECT DB_NAME()").fetchone()[0]
        if database.casefold() in {"master", "tempdb", "model", "msdb"}:
            raise ValueError("Refusing a SQL Server system database.")
        ddl = (ROOT / "sql" / "uci_schema.sql").read_text(encoding="utf-8")
        for batch in re.split(r"^\s*GO\s*$", ddl, flags=re.MULTILINE | re.IGNORECASE):
            if batch.strip():
                cursor.execute(batch)
        for name in TABLES:
            if cursor.execute(f"SELECT COUNT_BIG(*) FROM {SCHEMA}.[{name}]").fetchone()[0]:
                raise ValueError("Target tables contain data; use a new dedicated database.")
        for name in TABLES:
            with paths[name].open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                columns = reader.fieldnames
                allowed = {row[0] for row in cursor.execute(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=? AND TABLE_NAME=?",
                    SCHEMA, name)}
                if not columns or len(set(columns)) != len(columns) or set(columns) != allowed:
                    raise ValueError(f"Column mismatch in {name}.")
                statement = (f"INSERT INTO {SCHEMA}.[{name}] (" + ",".join(f"[{c}]" for c in columns)
                             + ") VALUES (" + ",".join("?" for _ in columns) + ")")
                batch, count = [], 0
                for row in reader:
                    values = [None if row[c] == "" else
                              (1 if row[c].lower() in {"1", "true"} else 0) if c in BOOLS else row[c]
                              for c in columns]
                    batch.append(values)
                    if len(batch) == 1000:
                        cursor.executemany(statement, batch)
                        count += len(batch)
                        batch = []
                if batch:
                    cursor.executemany(statement, batch)
                    count += len(batch)
                actual = cursor.execute(f"SELECT COUNT_BIG(*) FROM {SCHEMA}.[{name}]").fetchone()[0]
                if actual != count:
                    raise ValueError(f"Row count mismatch in {name}.")
                print(f"{name}: {count} rows prepared")
        connection.commit()
        print("All UCI tables committed in one transaction.")
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
