#!/usr/bin/env python3
import os
from typing import Any


def convert_txedge_to_csv_with_id(input_json_path: str, output_csv_path: str) -> None:
    """
    Placeholder converter: Reads input JSON and writes a minimal CSV with an ID column.
    This will be implemented per requirements. For now, it ensures the file pipeline works.

    Parameters
    ----------
    input_json_path: str
        Absolute path to the input TechEx JSON file.
    output_csv_path: str
        Absolute path to the output CSV to write.
    """
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)

    # Minimal placeholder output so the GUI flow is functional before implementation
    # We deliberately avoid importing pandas here to keep dependencies light until needed.
    with open(output_csv_path, "w", encoding="utf-8", newline="") as f:
        f.write("id,data\n")
        f.write("placeholder-0001,TODO-implement\n")


