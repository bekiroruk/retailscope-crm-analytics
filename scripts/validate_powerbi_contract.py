#!/usr/bin/env python3
"""Validate the source-controlled Power BI delivery contract and optional marts."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


def validate_package(contract_path: Path, data_root: Path | None) -> list[str]:
    errors: list[str] = []
    contract_path = contract_path.resolve()
    package_root = contract_path.parent
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Cannot read contract: {exc}"]

    tables = contract.get("tables", [])
    table_map = {table.get("name"): table for table in tables}
    if not tables or None in table_map or len(table_map) != len(tables):
        errors.append("Contract tables must have unique, non-empty names.")
    if not (package_root / "queries" / "DataRoot.m").is_file():
        errors.append("Missing Power Query DataRoot parameter template.")

    for table in tables:
        name = table.get("name", "<unnamed>")
        columns = table.get("columns", [])
        column_names = [column.get("name") for column in columns]
        if not table.get("file", "").endswith(".csv"):
            errors.append(f"{name}: source file must be CSV.")
        if not columns or None in column_names or len(set(column_names)) != len(column_names):
            errors.append(f"{name}: columns must be unique and non-empty.")
        query = package_root / "queries" / f"{name}.m"
        if not query.is_file():
            errors.append(f"{name}: missing Power Query file {query.name}.")
        else:
            query_text = query.read_text(encoding="utf-8")
            if table.get("file") not in query_text or "Encoding = 65001" not in query_text:
                errors.append(f"{name}: query must reference its CSV and UTF-8 encoding.")
        if data_root is not None:
            source = data_root / table["file"]
            if not source.is_file():
                errors.append(f"{name}: missing mart {source}.")
            else:
                with source.open("r", encoding="utf-8-sig", newline="") as handle:
                    actual = next(csv.reader(handle), [])
                if actual != column_names:
                    errors.append(f"{name}: CSV header differs from the contract: {actual!r}.")

    for relationship in contract.get("relationships", []):
        for side in ("from", "to"):
            reference = relationship.get(side, "")
            if "." not in reference:
                errors.append(f"Relationship has invalid {side} reference: {reference!r}.")
                continue
            table_name, column_name = reference.split(".", 1)
            table = table_map.get(table_name)
            if table is None or column_name not in {c["name"] for c in table["columns"]}:
                errors.append(f"Relationship references unknown field {reference!r}.")

    measures_path = package_root / contract.get("measures_file", "")
    measures = set(contract.get("measures", []))
    if not measures_path.is_file():
        errors.append(f"Missing DAX measures file: {measures_path}.")
    else:
        dax = measures_path.read_text(encoding="utf-8")
        missing = {name for name in measures if not any(
            line.startswith(f"{name} =") for line in dax.splitlines()
        )}
        if missing:
            errors.append(f"DAX file is missing measures: {sorted(missing)}.")

    fields = {
        f"{table['name']}.{column['name']}"
        for table in tables
        for column in table.get("columns", [])
    }
    for page in contract.get("pages", []):
        if not page.get("name") or not page.get("visuals"):
            errors.append("Every report page must have a name and at least one visual.")
        for visual in page.get("visuals", []):
            for binding in visual.get("bindings", []):
                if binding.startswith("[") and binding.endswith("]"):
                    if binding[1:-1] not in measures:
                        errors.append(f"Unknown measure binding {binding!r}.")
                elif binding not in fields:
                    errors.append(f"Unknown field binding {binding!r}.")

    theme_path = package_root / contract.get("theme_file", "")
    try:
        theme = json.loads(theme_path.read_text(encoding="utf-8"))
        if not theme.get("name") or len(theme.get("dataColors", [])) < 5:
            errors.append("Theme must define a name and at least five data colors.")
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Cannot read theme: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path("powerbi/model_contract.json"))
    parser.add_argument("--data-root", type=Path, help="Also validate generated CSV headers.")
    args = parser.parse_args()
    errors = validate_package(args.contract, args.data_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    mode = "package + marts" if args.data_root else "package structure"
    print(f"Power BI validation passed ({mode}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
