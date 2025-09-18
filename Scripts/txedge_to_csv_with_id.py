#!/usr/bin/env python3
import csv
import io
import json
import os
from typing import Any, Dict, List, Optional, Set


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _flatten_to_last_keys(obj: Any, out: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Flatten nested dicts to a mapping of last-key -> string value.

    - Dicts are traversed recursively; only leaf values are recorded.
    - Lists are JSON-encoded and stored under their immediate key name.
    - If the same last-key appears multiple times within the same object, the first
      occurrence wins to avoid ambiguous collisions.
    """
    if out is None:
        out = {}
    if isinstance(obj, dict):
        # Prefer processing direct, simple keys first
        for key, value in obj.items():
            if key == "state":
                # Skip massive/non-editable state blocks entirely
                continue
            if isinstance(value, (dict, list)):
                continue
            if key not in out:
                out[key] = _to_str(value)
        # Then recursively process nested dicts and lists
        for key, value in obj.items():
            if key == "state":
                # Skip recursion into state
                continue
            if isinstance(value, dict):
                _flatten_to_last_keys(value, out)
            elif isinstance(value, list):
                # Preserve lists as JSON text under the list's own key name
                if key not in out:
                    try:
                        out[key] = json.dumps(value, ensure_ascii=False)
                    except Exception:
                        out[key] = _to_str(value)
    else:
        # Non-dict root; nothing to flatten
        pass
    return out


def _collect_headers(items: List[Dict[str, Any]]) -> List[str]:
    header_set: Set[str] = set()
    for obj in items:
        flat = _flatten_to_last_keys(obj, {})
        header_set.update(flat.keys())

    # Keep key identifiers first if present, then "objectType" as the 4th column,
    # then the rest alphabetical for stability
    preferred_order = ["id", "stream", "name"]
    remaining = sorted([h for h in header_set if h not in preferred_order and h != "objectType"], key=str.lower)
    ordered = [h for h in preferred_order if h in header_set]
    # Ensure objectType is present as column 4
    ordered.append("objectType")
    ordered.extend(remaining)
    return ordered


def convert_txedge_to_csv_with_id(
    input_json_path: str,
    output_csv_path: str,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> None:
    with io.open(input_json_path, "r", encoding=encoding) as f:
        data = json.load(f)

    streams = data.get("configuredStreams") or []
    sources = data.get("configuredSources") or []
    outputs = data.get("configuredOutputs") or []

    if not isinstance(streams, list) or not isinstance(sources, list) or not isinstance(outputs, list):
        raise ValueError("Input JSON must contain lists: configuredStreams, configuredSources, configuredOutputs")

    # Build unified header set based on all three collections
    headers = _collect_headers(streams + sources + outputs)

    # Ensure parent directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_csv_path)), exist_ok=True)

    with io.open(output_csv_path, "w", encoding=encoding, newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=delimiter)
        writer.writerow(headers)

        # Write rows grouped by stream id: stream row, then its sources, then its outputs
        for stream in streams:
            if not isinstance(stream, dict):
                continue
            stream_id = stream.get("id")

            # Stream row
            flat_stream = _flatten_to_last_keys(stream, {})
            flat_stream["objectType"] = "Stream"
            writer.writerow([flat_stream.get(h, "") for h in headers])

            # Matching sources
            for source in sources:
                if not isinstance(source, dict):
                    continue
                if source.get("stream") != stream_id:
                    continue
                flat_source = _flatten_to_last_keys(source, {})
                flat_source["objectType"] = "Source"
                writer.writerow([flat_source.get(h, "") for h in headers])

            # Matching outputs
            for output in outputs:
                if not isinstance(output, dict):
                    continue
                if output.get("stream") != stream_id:
                    continue
                flat_output = _flatten_to_last_keys(output, {})
                flat_output["objectType"] = "Output"
                writer.writerow([flat_output.get(h, "") for h in headers])


