#!/usr/bin/env python3
import os
import sys
import subprocess
import tkinter.font as tkfont
import tkinter as tk
from tkinter import ttk, messagebox
import threading


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

        # Scale fonts and overall UI ~30%
        scale_factor = 1.3
        try:
            for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"): 
                f = tkfont.nametofont(name)
                f.configure(size=int(round(f.cget("size") * scale_factor)))
        except Exception:
            pass

        container = ttk.Frame(self, padding=16)
        container.grid(row=0, column=0, sticky="nsew")

        # TechEx Environment
        ttk.Label(container, text="TechEx Environment").grid(row=0, column=0, sticky="w")
        self.env_var = tk.StringVar(value=ENV_FOLDERS[0])
        self.env_combo = ttk.Combobox(container, textvariable=self.env_var, values=ENV_FOLDERS, state="readonly", width=int(round(30 * scale_factor)))
        self.env_combo.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.env_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_json_options())

        # Script
        ttk.Label(container, text="Script").grid(row=2, column=0, sticky="w")
        self.script_var = tk.StringVar(value="Stream Config")
        self.script_combo = ttk.Combobox(container, textvariable=self.script_var, values=list(SCRIPT_LABEL_TO_FILE.keys()), state="readonly", width=int(round(30 * scale_factor)))
        self.script_combo.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        # JSON File
        ttk.Label(container, text="JSON File").grid(row=4, column=0, sticky="w")
        refresh_btn = ttk.Button(container, text="Refresh", command=self._refresh_json_options)
        refresh_btn.grid(row=4, column=1, sticky="w", padx=(8, 0))
        self.json_var = tk.StringVar(value="")
        self.json_combo = ttk.Combobox(container, textvariable=self.json_var, values=[], state="readonly", width=int(round(50 * scale_factor)))
        self.json_combo.grid(row=5, column=0, sticky="ew", pady=(0, 12))

        # Convert all checkbox
        self.convert_all_var = tk.BooleanVar(value=False)
        self.convert_all_checkbox = ttk.Checkbutton(container, text="Convert ALL TechEx JSON Files", variable=self.convert_all_var)
        self.convert_all_checkbox.grid(row=6, column=0, sticky="w", pady=(0, 8))

        # Progress bar and active file label (shown during batch conversions)
        self.progress_var = tk.IntVar(value=0)
        self.progress = ttk.Progressbar(container, orient="horizontal", mode="determinate", maximum=0, variable=self.progress_var)
        self.progress.grid(row=8, column=0, columnspan=2, sticky="ew")
        self.active_file_var = tk.StringVar(value="")
        self.active_file_label = ttk.Label(container, textvariable=self.active_file_var, foreground="#555")
        self.active_file_label.grid(row=9, column=0, columnspan=2, sticky="w")

        # Run button
        self.run_button = ttk.Button(container, text="Run", command=self.on_run_clicked)
        self.run_button.grid(row=7, column=0, sticky="ew")

        # Status
        self.status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(container, textvariable=self.status_var, foreground="#555")
        self.status_label.grid(row=10, column=0, sticky="w", pady=(8, 0))

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

        if not os.path.exists(script_abs_path):
            messagebox.showerror("Error", f"Script not found: {script_rel_path}")
            return

        self.status_var.set("Running...")
        self.run_button.configure(state=tk.DISABLED)
        self.update_idletasks()

        # Helper for naming rule
        def make_output_path(input_filename: str) -> str:
            base_no_ext, _ = os.path.splitext(input_filename)
            base_lower = base_no_ext.lower()
            if base_lower.endswith("-config"):
                trimmed_base = base_no_ext[: -len("-config")]
            else:
                trimmed_base = base_no_ext
            if script_label == "Stream Config":
                output_base = f"{trimmed_base}-StreamInfo"
            else:
                output_base = trimmed_base
            # Route to subfolder based on script
            if script_label == "Stream Config":
                subfolder = "StreamInfo-CSVs"
            else:
                subfolder = "Input-Output-CSVs"
            env_output_dir = os.path.join(PROJECT_ROOT, env_folder, subfolder)
            os.makedirs(env_output_dir, exist_ok=True)
            return os.path.join(env_output_dir, f"{output_base}.csv")

        # Batch or single
        if self.convert_all_var.get():
            all_jsons = list_json_files(env_folder)
            if not all_jsons:
                messagebox.showerror("Error", f"No JSON files found in '{env_folder}'.")
                self.status_var.set("Failed.")
                self.run_button.configure(state=tk.NORMAL)
                return

            # Prepare progress
            self.progress.configure(maximum=len(all_jsons))
            self.progress_var.set(0)
            self.active_file_var.set("")

            def worker() -> None:
                successes = 0
                failures = 0
                failure_msgs = []
                for idx, fname in enumerate(all_jsons, start=1):
                    self.after(0, lambda f=fname: self.active_file_var.set(f"Converting: {f}"))
                    input_abs_path = os.path.join(PROJECT_ROOT, env_folder, fname)
                    output_abs_path = make_output_path(fname)
                    cmd = [sys.executable, script_abs_path, "-i", input_abs_path, "-o", output_abs_path]
                    proc = subprocess.run(cmd, capture_output=True, text=True)
                    if proc.returncode != 0:
                        failures += 1
                        failure_msgs.append(f"{fname}: {proc.stderr.strip() or 'Unknown error'}")
                    else:
                        successes += 1
                    self.after(0, lambda i=idx: self.progress_var.set(i))

                def finish() -> None:
                    if failures:
                        self.status_var.set(f"Done with errors: {successes} succeeded, {failures} failed")
                        messagebox.showwarning("Completed with errors", "\n".join(failure_msgs[:20]))
                    else:
                        self.status_var.set(f"Completed: {successes} files converted")
                        messagebox.showinfo("Success", f"Converted {successes} file(s) in {env_folder}.")
                    self.active_file_var.set("")
                    self.run_button.configure(state=tk.NORMAL)

                self.after(0, finish)

            threading.Thread(target=worker, daemon=True).start()
            return

        # Single file path (synchronous)
        try:
            input_abs_path = os.path.join(PROJECT_ROOT, env_folder, json_file_name)
            if not os.path.exists(input_abs_path):
                messagebox.showerror("Error", f"Input JSON not found: {input_abs_path}")
                self.status_var.set("Failed.")
                return
            output_abs_path = make_output_path(json_file_name)
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


