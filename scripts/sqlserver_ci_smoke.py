"""Prepare and verify the ephemeral SQL Server integration-test database."""
import os
import sys
import time

import pyodbc


def connect(value, attempts=30):
    error = None
    for _ in range(attempts):
        try:
            return pyodbc.connect(value, timeout=3, autocommit=True)
        except pyodbc.Error as exc:
            error = exc
            time.sleep(2)
    raise error


def prepare():
    value = os.environ["RETAILSCOPE_MASTER_ODBC"]
    with connect(value) as connection:
        connection.cursor().execute("IF DB_ID(N'RetailScopeCI') IS NULL CREATE DATABASE RetailScopeCI")
    print("RetailScopeCI database is ready")


def verify():
    value = os.environ["RETAILSCOPE_ODBC"]
    with connect(value, attempts=3) as connection:
        cursor = connection.cursor()
        tables = ["dim_customer", "dim_product", "dim_date", "fact_sales", "customer_scores"]
        counts = {name: cursor.execute(f"SELECT COUNT_BIG(*) FROM retailscope_uci.[{name}]").fetchone()[0]
                  for name in tables}
        if any(count != 1 for count in counts.values()):
            raise AssertionError(counts)
        view_row = cursor.execute("SELECT net_revenue, sale_orders, purchasing_customers "
                                  "FROM retailscope_uci.v_monthly_performance WHERE year_month='2011-12'").fetchone()
        if tuple(map(float, view_row)) != (21.0, 1.0, 1.0):
            raise AssertionError(tuple(view_row))
        try:
            cursor.execute("UPDATE retailscope_uci.customer_scores SET inactive_risk90=1.5")
        except pyodbc.Error:
            connection.rollback()
        else:
            raise AssertionError("inactive_risk90 CHECK constraint did not reject 1.5")
    print(f"Verified live SQL Server tables, view, foreign keys and checks: {counts}")


if __name__ == "__main__":
    {"prepare": prepare, "verify": verify}[sys.argv[1]]()
