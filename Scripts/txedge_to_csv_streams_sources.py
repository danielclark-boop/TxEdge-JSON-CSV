#!/usr/bin/env python3
import argparse
import csv
import io
import json
import os
import sys
from typing import Any, Dict, List, Optional


def _get(d: Optional[Dict[str, Any]], key: str) -> Optional[Any]:
    if isinstance(d, dict):
        return d.get(key)
    return None


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


STREAM_HEADERS: List[str] = [
    "name",
    "zeroBitrate",
    "TSSyncLoss",
    "lowBitrateThreshold",
    "CCErrorsInPeriodThreshold",
    "CCErrorsInPeriodTime",
    "lowBitrate",
    "CCErrorsInPeriod",
    "failoverMode",
    "failoverRevertTime",
    "failoverWaitTime",
    "enableThumbnails",
    "priority",
]


def convert_streams_sources(
    input_path: str,
    output_path: str,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> None:
    with io.open(input_path, "r", encoding=encoding) as f:
        data = json.load(f)

    streams = data.get("configuredStreams") or []
    sources = data.get("configuredSources") or []

    if not isinstance(streams, list) or not isinstance(sources, list):
        raise ValueError("Input JSON must contain lists: configuredStreams, configuredSources")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with io.open(output_path, "w", encoding=encoding, newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=delimiter)
        writer.writerow(STREAM_HEADERS)

        for stream in streams:
            if not isinstance(stream, dict):
                continue

            options = _get(stream, "options")
            triggers = _get(options, "failoverTriggers")

            # Row for stream-level values (columns 1-12), leave 'priority' blank
            row_stream = [
                _to_str(stream.get("name")),
                _to_str(_get(triggers, "zeroBitrate")),
                _to_str(_get(triggers, "TSSyncLoss")),
                _to_str(_get(triggers, "lowBitrateThreshold")),
                _to_str(_get(triggers, "CCErrorsInPeriodThreshold")),
                _to_str(_get(triggers, "CCErrorsInPeriodTime")),
                _to_str(_get(triggers, "lowBitrate")),
                _to_str(_get(triggers, "CCErrorsInPeriod")),
                _to_str(_get(options, "failoverMode")),
                _to_str(_get(options, "failoverRevertTime")),
                _to_str(_get(options, "failoverWaitTime")),
                _to_str(stream.get("enableThumbnails") if stream.get("enableThumbnails") is not None else _get(options, "enableThumbnails")),
                "",
            ]
            writer.writerow(row_stream)

            stream_id = stream.get("id")

            # Rows for each matching source: column 1 = source.name, columns 2-12 blanks, column 13 = priority
            for source in sources:
                if not isinstance(source, dict):
                    continue
                if source.get("stream") != stream_id:
                    continue

                row_source = [
                    _to_str(source.get("name")),
                ] + [""] * 11 + [
                    _to_str(source.get("priority")),
                ]
                writer.writerow(row_source)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert txEdge configuredStreams and configuredSources to CSV with stream fields + priority")
    parser.add_argument("-i", "--input", required=True, help="Path to txEdge JSON file")
    parser.add_argument("-o", "--output", required=True, help="Path to output CSV file")
    parser.add_argument("--delimiter", default=",", help="CSV delimiter")
    parser.add_argument("--encoding", default="utf-8", help="File encoding")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        convert_streams_sources(args.input, args.output, delimiter=args.delimiter, encoding=args.encoding)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

