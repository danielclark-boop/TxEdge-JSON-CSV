#!/usr/bin/env python3
import argparse
import csv
import io
import json
import os
import sys
from typing import Any, Dict, List, Optional


def _get_option_value(item: Dict[str, Any], key: str) -> Optional[Any]:
    options = item.get("options")
    if isinstance(options, dict):
        return options.get(key)
    return None


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def convert_txedge_to_csv(input_path: str, output_path: str, delimiter: str = ",", encoding: str = "utf-8") -> None:
    with io.open(input_path, "r", encoding=encoding) as f:
        data = json.load(f)

    streams = data.get("configuredStreams") or []
    sources = data.get("configuredSources") or []
    outputs = data.get("configuredOutputs") or []

    if not isinstance(streams, list) or not isinstance(sources, list) or not isinstance(outputs, list):
        raise ValueError("Input JSON must contain lists: configuredStreams, configuredSources, configuredOutputs")

    # Header per user specification/order (common across sources and outputs)
    headers: List[str] = [
        "streamName",
        "name",
        "protocol",
        "port",
        "networkInterface/hostAddress",
        "sourceAddress/address",
        "stopped",
        "paused",
        "priority",
    ]

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with io.open(output_path, "w", encoding=encoding, newline="") as csvfile:
        writer = csv.writer(csvfile, delimiter=delimiter)
        writer.writerow(headers)

        # Iterate streams in order
        for stream in streams:
            if not isinstance(stream, dict):
                continue
            stream_id = stream.get("id")
            stream_name = stream.get("name")

            # First, write rows for matching configuredSources
            for source in sources:
                if not isinstance(source, dict):
                    continue
                if source.get("stream") != stream_id:
                    continue

                row = [
                    _to_str(stream_name),
                    _to_str(source.get("name")),
                    _to_str(source.get("protocol")),
                    _to_str(_get_option_value(source, "port")),
                    _to_str(_get_option_value(source, "networkInterface")),
                    _to_str(_get_option_value(source, "sourceAddress")),
                    _to_str(source.get("stopped")),
                    _to_str(source.get("paused")),
                    _to_str(source.get("priority")),
                ]
                writer.writerow(row)

            # Then, write rows for matching configuredOutputs
            for output in outputs:
                if not isinstance(output, dict):
                    continue
                if output.get("stream") != stream_id:
                    continue

                row = [
                    _to_str(stream_name),
                    _to_str(output.get("name")),
                    _to_str(output.get("protocol")),
                    _to_str(_get_option_value(output, "port")),
                    _to_str(_get_option_value(output, "hostAddress")),
                    _to_str(_get_option_value(output, "address")),
                    "",  # blank entry in place of 'stopped'
                    _to_str(output.get("paused")),
                    "",  # blank entry in place of 'priority'
                ]
                writer.writerow(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert TechEx txEdge JSON to CSV as specified")
    parser.add_argument("-i", "--input", required=True, help="Path to txEdge JSON file")
    parser.add_argument("-o", "--output", required=True, help="Path to output CSV file")
    parser.add_argument("--delimiter", default=",", help="CSV delimiter")
    parser.add_argument("--encoding", default="utf-8", help="File encoding")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        convert_txedge_to_csv(args.input, args.output, delimiter=args.delimiter, encoding=args.encoding)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

