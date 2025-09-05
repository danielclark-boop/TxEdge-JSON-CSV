#!/usr/bin/env python3
"""
json_to_csv.py

A simple and robust JSON/NDJSON to CSV converter.

Features:
- Supports JSON arrays and NDJSON (one JSON object per line).
- Optional explicit field selection using dot-paths (e.g., "user.name", "items[0].id").
- If fields are not provided, infers headers by flattening keys (dot notation) from the first N records.
- Streams NDJSON inputs line-by-line for low memory usage.
- Writes UTF-8 CSV with configurable delimiter and null placeholder.

Limitations:
- Arrays are serialized as JSON strings unless a numeric index is provided in the field path (e.g., "items[0]").
  There is no array explosion in this initial version.

Usage examples:
  python json_to_csv.py -i input.json -o output.csv
  python json_to_csv.py -i input.json -o output.csv --fields id,name,contact.email
  python json_to_csv.py -i input.ndjson -o output.csv --ndjson --delimiter '\t'

"""

import argparse
import csv
import io
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple


DOT_INDEX_PATTERN = re.compile(r"^(?P<key>[^\[]+)(\[(?P<index>\d+)\])?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert JSON/NDJSON to CSV with optional field selection",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-i", "--input", required=True, help="Path to input JSON or NDJSON file")
    parser.add_argument("-o", "--output", required=True, help="Path to output CSV file")
    parser.add_argument(
        "--ndjson",
        action="store_true",
        help="Treat input as NDJSON (newline-delimited JSON). If not set, attempts to load as a JSON array",
    )
    parser.add_argument(
        "--fields",
        help=(
            "Comma-separated list of dot-paths to extract (e.g., 'id,user.name,items[0].id'). "
            "If omitted, headers are inferred by flattening keys of the first N records"
        ),
    )
    parser.add_argument(
        "--infer-records",
        type=int,
        default=1000,
        help="Number of records to sample for inferring headers when --fields is not provided",
    )
    parser.add_argument(
        "--delimiter",
        default=",",
        help="CSV delimiter",
    )
    parser.add_argument(
        "--null",
        default="",
        help="Placeholder for missing/null values in output",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="File encoding for input and output",
    )
    return parser.parse_args()


def load_json_records(input_path: str, is_ndjson: bool, encoding: str) -> Iterable[Dict[str, Any]]:
    if is_ndjson or input_path.lower().endswith(".ndjson") or input_path.lower().endswith(".jsonl"):
        with io.open(input_path, "r", encoding=encoding) as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    obj = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON line: {exc}\nLine: {stripped[:200]}") from exc
                if isinstance(obj, dict):
                    yield obj
                else:
                    raise ValueError("Each NDJSON line must be a JSON object (not array/scalar)")
    else:
        with io.open(input_path, "r", encoding=encoding) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON file: {exc}") from exc
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    raise ValueError("Top-level JSON array must contain objects only")
                yield item
        elif isinstance(data, dict):
            # Allow single object: treat as one-record dataset
            yield data
        else:
            raise ValueError("Unsupported JSON structure. Provide NDJSON or an array/object of records.")


def tokenize_path(path: str) -> List[Tuple[str, Optional[int]]]:
    tokens: List[Tuple[str, Optional[int]]] = []
    for segment in path.split("."):
        match = DOT_INDEX_PATTERN.match(segment)
        if not match:
            raise ValueError(f"Invalid field token: {segment}")
        key = match.group("key")
        index = match.group("index")
        tokens.append((key, int(index) if index is not None else None))
    return tokens


def get_value_by_path(obj: Any, path: str) -> Any:
    current = obj
    for key, maybe_index in tokenize_path(path):
        if not isinstance(current, dict):
            return None
        if key not in current:
            return None
        current = current[key]
        if maybe_index is not None:
            if not isinstance(current, list):
                return None
            if maybe_index < 0 or maybe_index >= len(current):
                return None
            current = current[maybe_index]
    return current


def is_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None


def serialize_value(value: Any) -> Any:
    if is_scalar(value):
        return value
    # For lists/dicts, store a compact JSON string representation
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def flatten_record(record: Dict[str, Any], parent_key: str = "") -> Dict[str, Any]:
    flat: Dict[str, Any] = {}
    for k, v in record.items():
        new_key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            flat.update(flatten_record(v, new_key))
        elif isinstance(v, list):
            flat[new_key] = serialize_value(v)
        else:
            flat[new_key] = v
    return flat


def infer_headers(records: Iterable[Dict[str, Any]], sample_size: int) -> List[str]:
    headers: List[str] = []
    seen = set()
    count = 0
    for record in records:
        flat = flatten_record(record)
        for key in flat.keys():
            if key not in seen:
                seen.add(key)
                headers.append(key)
        count += 1
        if count >= sample_size:
            break
    return headers


def reopen_records(input_path: str, is_ndjson: bool, encoding: str) -> Iterable[Dict[str, Any]]:
    # Helper to re-open the iterator after a first pass made by infer_headers
    return load_json_records(input_path, is_ndjson, encoding)


def write_csv(
    input_path: str,
    output_path: str,
    is_ndjson: bool,
    encoding: str,
    delimiter: str,
    null_placeholder: str,
    field_paths: Optional[List[str]],
    infer_records: int,
) -> None:
    records_iter = load_json_records(input_path, is_ndjson, encoding)

    if field_paths is None:
        # Need to infer headers from the first N records. We will materialize the first N into memory.
        sampled: List[Dict[str, Any]] = []
        try:
            for idx, rec in enumerate(records_iter):
                sampled.append(rec)
                if idx + 1 >= infer_records:
                    break
        except Exception:
            raise
        headers = infer_headers(sampled, sample_size=len(sampled))
        # Re-open the stream to iterate all records from the start
        records_iter = reopen_records(input_path, is_ndjson, encoding)
        use_flatten = True
    else:
        headers = field_paths
        use_flatten = False

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with io.open(output_path, "w", encoding=encoding, newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=delimiter)
        writer.writerow(headers)
        for record in records_iter:
            if use_flatten:
                flat = flatten_record(record)
                row = [serialize_value(flat.get(h, None)) for h in headers]
            else:
                values: List[Any] = []
                for path in headers:
                    value = get_value_by_path(record, path)
                    values.append(serialize_value(value))
                row = [null_placeholder if v is None else v for v in values]
            # replace None with placeholder for the flatten path too
            row = [null_placeholder if v is None else v for v in row]
            writer.writerow(row)


def main() -> int:
    args = parse_args()
    field_paths = None
    if args.fields:
        field_paths = [p.strip() for p in args.fields.split(",") if p.strip()]
        if not field_paths:
            field_paths = None

    try:
        write_csv(
            input_path=args.input,
            output_path=args.output,
            is_ndjson=args.ndjson,
            encoding=args.encoding,
            delimiter=args.delimiter,
            null_placeholder=args.null,
            field_paths=field_paths,
            infer_records=args.infer_records,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

