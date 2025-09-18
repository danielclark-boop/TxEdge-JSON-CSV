#!/usr/bin/env python3
import csv
import io
import json
import os
from typing import Any, Dict, List, Optional


def _parse_bool(s: str) -> Optional[bool]:
    v = s.strip().lower()
    if v in ("true", "1", "yes", "y"):  # allow common truthy
        return True
    if v in ("false", "0", "no", "n"):  # allow common falsy
        return False
    return None


def _coerce_to_type(new_text: str, old_value: Any) -> Any:
    # Empty text means "no change"
    if new_text is None:
        return old_value
    s = new_text.strip()
    if s == "":
        return old_value

    if isinstance(old_value, bool):
        parsed = _parse_bool(s)
        return old_value if parsed is None else parsed
    if isinstance(old_value, int) and not isinstance(old_value, bool):
        try:
            return int(s)
        except Exception:
            return old_value
    if isinstance(old_value, float):
        try:
            return float(s)
        except Exception:
            return old_value
    if isinstance(old_value, (list, dict)):
        try:
            return json.loads(s)
        except Exception:
            return old_value
    # Default: string
    return s


def _update_obj_from_row(obj: Dict[str, Any], row: Dict[str, str]) -> None:
    skip_keys = {"id", "objectType", "stream", "state"}

    def recurse(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in skip_keys:
                    continue
                if key == "state":
                    continue
                if isinstance(value, dict):
                    recurse(value)
                elif isinstance(value, list):
                    if key in row and row[key].strip() != "":
                        try:
                            node[key] = json.loads(row[key])
                        except Exception:
                            # Ignore invalid JSON payloads for lists
                            pass
                else:
                    if key in row:
                        node[key] = _coerce_to_type(row[key], value)

    recurse(obj)


def _read_csv_rows(csv_path: str, delimiter: str, encoding: str) -> List[Dict[str, str]]:
    with io.open(csv_path, "r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        return [dict(row) for row in reader]


def convert_csv_to_json(
    input_csv_path: str,
    output_json_path: str,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> None:
    # Determine the source JSON path in the environment root
    env_dir = os.path.dirname(os.path.dirname(os.path.abspath(input_csv_path)))
    csv_base = os.path.splitext(os.path.basename(input_csv_path))[0]
    source_json_path = os.path.join(env_dir, f"{csv_base}-config.json")
    if not os.path.exists(source_json_path):
        raise FileNotFoundError(f"Matching JSON not found: {source_json_path}")

    # Load current JSON
    with io.open(source_json_path, "r", encoding=encoding) as f:
        data = json.load(f)

    # Read CSV rows, index by id (string form for robustness)
    rows = _read_csv_rows(input_csv_path, delimiter, encoding)
    id_to_row: Dict[str, Dict[str, str]] = {}
    for row in rows:
        rid = (row.get("id") or "").strip()
        if rid != "":
            id_to_row[rid] = row

    # Update each object in configuredStreams/Sources/Outputs by id
    for section_key in ("configuredStreams", "configuredSources", "configuredOutputs"):
        items = data.get(section_key)
        if not isinstance(items, list):
            continue
        for obj in items:
            if not isinstance(obj, dict):
                continue
            obj_id = obj.get("id")
            if obj_id is None:
                continue
            row = id_to_row.get(str(obj_id))
            if not row:
                continue
            _update_obj_from_row(obj, row)

    # Ensure destination directory exists and write updated JSON
    os.makedirs(os.path.dirname(os.path.abspath(output_json_path)), exist_ok=True)
    with io.open(output_json_path, "w", encoding=encoding) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


