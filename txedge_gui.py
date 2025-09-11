#!/usr/bin/env python3
import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_FOLDERS = ["TDP", "D2C", "FTS"]
SCRIPT_LABEL_TO_FILE = {
    "Stream Config": os.path.join("Scripts", "txedge_to_csv_streams_sources.py"),
    "Input/Output": os.path.join("Scripts", "txedge_to_csv.py"),
}


def list_json_files(env_folder: str) -> list:
    env_path = os.path.join(PROJECT_ROOT, env_folder)
    try:
        files = sorted(
            [f for f in os.listdir(env_path) if f.lower().endswith(".json")]
        )
    except FileNotFoundError:
        files = []
    return files


class TxEdgeGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("TxEdge JSON → CSV")
        self.resizable(False, False)

        container = ttk.Frame(self, padding=12)
        container.grid(row=0, column=0, sticky="nsew")

        # TechEx Environment
        ttk.Label(container, text="TechEx Environment").grid(row=0, column=0, sticky="w")
        self.env_var = tk.StringVar(value=ENV_FOLDERS[0])
        self.env_combo = ttk.Combobox(container, textvariable=self.env_var, values=ENV_FOLDERS, state="readonly", width=30)
        self.env_combo.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.env_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_json_options())

        # Script
        ttk.Label(container, text="Script").grid(row=2, column=0, sticky="w")
        self.script_var = tk.StringVar(value="Stream Config")
        self.script_combo = ttk.Combobox(container, textvariable=self.script_var, values=list(SCRIPT_LABEL_TO_FILE.keys()), state="readonly", width=30)
        self.script_combo.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        # JSON File
        ttk.Label(container, text="JSON File").grid(row=4, column=0, sticky="w")
        self.json_var = tk.StringVar(value="")
        self.json_combo = ttk.Combobox(container, textvariable=self.json_var, values=[], state="readonly", width=50)
        self.json_combo.grid(row=5, column=0, sticky="ew", pady=(0, 12))

        # Run button
        self.run_button = ttk.Button(container, text="Run", command=self.on_run_clicked)
        self.run_button.grid(row=6, column=0, sticky="ew")

        # Status
        self.status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(container, textvariable=self.status_var, foreground="#555")
        self.status_label.grid(row=7, column=0, sticky="w", pady=(8, 0))

        self._refresh_json_options()

    def _refresh_json_options(self) -> None:
        env_folder = self.env_var.get()
        json_files = list_json_files(env_folder)
        self.json_combo["values"] = json_files
        self.json_var.set(json_files[0] if json_files else "")

    def on_run_clicked(self) -> None:
        env_folder = self.env_var.get()
        script_label = self.script_var.get()
        json_file_name = self.json_var.get()

        if not env_folder:
            messagebox.showerror("Error", "Please select a TechEx Environment.")
            return
        if not script_label:
            messagebox.showerror("Error", "Please select a Script.")
            return
        if not json_file_name:
            messagebox.showerror("Error", f"No JSON files found in '{env_folder}'.")
            return

        script_rel_path = SCRIPT_LABEL_TO_FILE.get(script_label)
        script_abs_path = os.path.join(PROJECT_ROOT, script_rel_path)
        input_abs_path = os.path.join(PROJECT_ROOT, env_folder, json_file_name)

        if not os.path.exists(script_abs_path):
            messagebox.showerror("Error", f"Script not found: {script_rel_path}")
            return
        if not os.path.exists(input_abs_path):
            messagebox.showerror("Error", f"Input JSON not found: {input_abs_path}")
            return

        # Output: same name, .csv, in the same env folder
        base, _ = os.path.splitext(json_file_name)
        output_abs_path = os.path.join(PROJECT_ROOT, env_folder, f"{base}.csv")

        self.status_var.set("Running...")
        self.run_button.configure(state=tk.DISABLED)
        self.update_idletasks()

        try:
            # Invoke selected script with -i and -o
            cmd = [sys.executable, script_abs_path, "-i", input_abs_path, "-o", output_abs_path]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                stderr = proc.stderr.strip() or "Unknown error"
                messagebox.showerror("Conversion failed", stderr)
                self.status_var.set("Failed.")
            else:
                self.status_var.set(f"Done: {os.path.relpath(output_abs_path, PROJECT_ROOT)}")
                messagebox.showinfo("Success", f"CSV created:\n{output_abs_path}")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self.status_var.set("Failed.")
        finally:
            self.run_button.configure(state=tk.NORMAL)


def main() -> int:
    app = TxEdgeGUI()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())


