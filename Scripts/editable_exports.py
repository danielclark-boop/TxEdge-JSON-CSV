import json
import csv
from typing import List, Dict, Any


def _collect_columns(items: List[Dict[str, Any]]) -> List[str]:
	columns = []
	seen = set()
	for item in items:
		for key, value in item.items():
			if key not in seen:
				seen.add(key)
				columns.append(key)
	return columns


def _normalize_value(value: Any) -> Any:
	if isinstance(value, (dict, list)):
		return json.dumps(value, separators=(",", ":"))
	return value


def convert_stream_edit(input_json_path: str, output_csv_path: str) -> None:
	with open(input_json_path, "r", encoding="utf-8") as f:
		data = json.load(f)
	rows = data.get("configuredStreams", [])
	if not isinstance(rows, list):
		rows = []
	columns = _collect_columns(rows)
	with open(output_csv_path, "w", encoding="utf-8", newline="") as out:
		writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore")
		writer.writeheader()
		for row in rows:
			flat = {k: _normalize_value(row.get(k, "")) for k in columns}
			writer.writerow(flat)


def convert_input_edit(input_json_path: str, output_csv_path: str) -> None:
	with open(input_json_path, "r", encoding="utf-8") as f:
		data = json.load(f)
	rows = data.get("configuredSources", [])
	if not isinstance(rows, list):
		rows = []
	# Grouping: sort by 'stream' to keep like-stream items together
	rows_sorted = sorted(rows, key=lambda r: str(r.get("stream", "")))
	columns = _collect_columns(rows_sorted)
	with open(output_csv_path, "w", encoding="utf-8", newline="") as out:
		writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore")
		writer.writeheader()
		for row in rows_sorted:
			flat = {k: _normalize_value(row.get(k, "")) for k in columns}
			writer.writerow(flat)


def convert_output_edit(input_json_path: str, output_csv_path: str) -> None:
	with open(input_json_path, "r", encoding="utf-8") as f:
		data = json.load(f)
	rows = data.get("configuredOutputs", [])
	if not isinstance(rows, list):
		rows = []
	rows_sorted = sorted(rows, key=lambda r: str(r.get("stream", "")))
	columns = _collect_columns(rows_sorted)
	with open(output_csv_path, "w", encoding="utf-8", newline="") as out:
		writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore")
		writer.writeheader()
		for row in rows_sorted:
			flat = {k: _normalize_value(row.get(k, "")) for k in columns}
			writer.writerow(flat)


