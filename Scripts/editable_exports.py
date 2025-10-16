import json
import csv
from typing import List, Dict, Any


def _collect_columns(items: List[Dict[str, Any]]) -> List[str]:
	columns: List[str] = []
	seen = set()
	for item in items:
		for key in item.keys():
			# Drop any 'state' columns entirely (and any dotted state.* just in case)
			if key == "state" or str(key).startswith("state."):
				continue
			if key not in seen:
				seen.add(key)
				columns.append(key)
	return columns


def _normalize_value(value: Any) -> Any:
	if isinstance(value, list):
		return json.dumps(value, separators=(",", ":"))
	return value


def _flatten(prefix: str, obj: Any, out: Dict[str, Any]) -> None:
	"""Flatten nested dicts into dotted keys. Lists are JSON-serialized."""
	if isinstance(obj, dict):
		for k, v in obj.items():
			# Skip any state.* keys entirely
			if (not prefix and k == "state") or (prefix and prefix.split(".")[0] == "state"):
				continue
			key = f"{prefix}.{k}" if prefix else str(k)
			if isinstance(v, dict):
				_flatten(key, v, out)
			else:
				out[key] = _normalize_value(v)
	else:
		out[prefix] = _normalize_value(obj)


def _flatten_record(item: Dict[str, Any]) -> Dict[str, Any]:
	flat: Dict[str, Any] = {}
	for k, v in item.items():
		# Drop the entire state subtree (even if it's not a dict)
		if k == "state":
			continue
		if isinstance(v, dict):
			_flatten(k, v, flat)
		else:
			flat[k] = _normalize_value(v)
	return flat


def convert_stream_edit(input_json_path: str, output_csv_path: str) -> None:
	with open(input_json_path, "r", encoding="utf-8") as f:
		data = json.load(f)
	rows = data.get("configuredStreams", [])
	if not isinstance(rows, list):
		rows = []
	flat_rows = [_flatten_record(r) for r in rows]
	columns = _collect_columns(flat_rows)
	with open(output_csv_path, "w", encoding="utf-8", newline="") as out:
		writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore")
		writer.writeheader()
		for row in flat_rows:
			flat = {k: row.get(k, "") for k in columns}
			writer.writerow(flat)


def convert_input_edit(input_json_path: str, output_csv_path: str) -> None:
	with open(input_json_path, "r", encoding="utf-8") as f:
		data = json.load(f)
	rows = data.get("configuredSources", [])
	if not isinstance(rows, list):
		rows = []
	# Build stream id -> name map
	streams = data.get("configuredStreams", [])
	stream_id_to_name = {str(s.get("id")) if "id" in s else str(s.get("_id")): s.get("name", "") for s in streams if isinstance(s, dict)}
	# Grouping: sort by 'stream' to keep like-stream items together
	rows_sorted = sorted(rows, key=lambda r: str(r.get("stream", "")))
	flat_rows = []
	for r in rows_sorted:
		fr = _flatten_record(r)
		fr["streamName"] = stream_id_to_name.get(str(r.get("stream", "")), "")
		flat_rows.append(fr)
	# Columns: ensure id, streamName are first two
	colset = _collect_columns(flat_rows)
	rest = [c for c in colset if c not in ("id", "streamName")]
	columns = ["id", "streamName", *rest]
	with open(output_csv_path, "w", encoding="utf-8", newline="") as out:
		writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore")
		writer.writeheader()
		for row in flat_rows:
			flat = {k: row.get(k, "") for k in columns}
			writer.writerow(flat)


def convert_output_edit(input_json_path: str, output_csv_path: str) -> None:
	with open(input_json_path, "r", encoding="utf-8") as f:
		data = json.load(f)
	rows = data.get("configuredOutputs", [])
	if not isinstance(rows, list):
		rows = []
	# Build stream id -> name map
	streams = data.get("configuredStreams", [])
	stream_id_to_name = {str(s.get("id")) if "id" in s else str(s.get("_id")): s.get("name", "") for s in streams if isinstance(s, dict)}
	rows_sorted = sorted(rows, key=lambda r: str(r.get("stream", "")))
	flat_rows = []
	for r in rows_sorted:
		fr = _flatten_record(r)
		fr["streamName"] = stream_id_to_name.get(str(r.get("stream", "")), "")
		flat_rows.append(fr)
	colset = _collect_columns(flat_rows)
	rest = [c for c in colset if c not in ("id", "streamName")]
	columns = ["id", "streamName", *rest]
	with open(output_csv_path, "w", encoding="utf-8", newline="") as out:
		writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore")
		writer.writeheader()
		for row in flat_rows:
			flat = {k: row.get(k, "") for k in columns}
			writer.writerow(flat)


