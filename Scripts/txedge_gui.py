#!/usr/bin/env python3
import os
import sys
import tkinter.font as tkfont
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json

# Make sibling scripts importable and import conversion functions
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.append(SCRIPTS_DIR)
try:
    from txedge_to_csv import convert_txedge_to_csv  # type: ignore
    from txedge_to_csv_streams_sources import convert_streams_sources  # type: ignore
except Exception:
    # If running in an unusual environment (e.g., frozen onefile), load later with a fallback
    convert_txedge_to_csv = None  # type: ignore
    convert_streams_sources = None  # type: ignore


if getattr(sys, "frozen", False):
    PROJECT_ROOT = os.path.dirname(sys.executable)
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FOLDERS = ["TDP", "D2C", "FTS"]
SCRIPT_LABEL_TO_FUNC = {
    "Stream Information": convert_streams_sources,
    "Input/Output": convert_txedge_to_csv,
}

# Load site/env configuration for Core addresses and tokens
def _load_site_env_config() -> dict:
    cfg_path = os.path.join(SCRIPTS_DIR, "site_env_config.json")
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

SITE_ENV_CONFIG = _load_site_env_config()
SITE_OPTIONS = sorted(list(SITE_ENV_CONFIG.keys())) if SITE_ENV_CONFIG else ["Pico", "Tempe"]


def list_json_files(site_folder: str, env_folder: str) -> list:
    env_path = os.path.join(PROJECT_ROOT, "Sites", site_folder, env_folder)
    try:
        files = sorted(
            [f for f in os.listdir(env_path) if f.lower().endswith(".json")]
        )
    except FileNotFoundError:
        files = []
    return files


def _hide_windows_console_if_present() -> None:
    """On Windows, hide the console window so the GUI runs without a static terminal."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32")
        user32 = ctypes.WinDLL("user32")

        GetConsoleWindow = kernel32.GetConsoleWindow
        GetConsoleWindow.restype = wintypes.HWND
        ShowWindow = user32.ShowWindow

        SW_HIDE = 0
        hwnd = GetConsoleWindow()
        if hwnd:
            ShowWindow(hwnd, SW_HIDE)
    except Exception:
        # Non-fatal: if this fails, the app still runs
        pass


def _load_conversion_functions_from_meipass() -> None:
    """In frozen onefile builds, attempt to import converters from bundled data."""
    global convert_txedge_to_csv, convert_streams_sources
    if (
        (convert_txedge_to_csv is not None)
        and (convert_streams_sources is not None)
    ):
        return
    base_dir = getattr(sys, "_MEIPASS", None)
    if not base_dir:
        return
    try:
        import importlib.util
        # txedge_to_csv.py
        csv_mod_path = os.path.join(base_dir, "Scripts", "txedge_to_csv.py")
        if (convert_txedge_to_csv is None) and os.path.exists(csv_mod_path):
            spec = importlib.util.spec_from_file_location("txedge_to_csv", csv_mod_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)  # type: ignore[attr-defined]
                convert_txedge_to_csv = getattr(module, "convert_txedge_to_csv", None)
        # txedge_to_csv_streams_sources.py
        s_mod_path = os.path.join(base_dir, "Scripts", "txedge_to_csv_streams_sources.py")
        if (convert_streams_sources is None) and os.path.exists(s_mod_path):
            spec2 = importlib.util.spec_from_file_location("txedge_to_csv_streams_sources", s_mod_path)
            if spec2 and spec2.loader:
                module2 = importlib.util.module_from_spec(spec2)
                spec2.loader.exec_module(module2)  # type: ignore[attr-defined]
                convert_streams_sources = getattr(module2, "convert_streams_sources", None)
    except Exception:
        # Non-fatal; handled by UI error message later
        pass


def _update_script_mapping() -> None:
    """Refresh mapping after late imports in frozen builds."""
    SCRIPT_LABEL_TO_FUNC["Stream Information"] = convert_streams_sources  # type: ignore[index]
    SCRIPT_LABEL_TO_FUNC["Input/Output"] = convert_txedge_to_csv  # type: ignore[index]


def _ensure_environment_structure() -> None:
    """Ensure TDP/D2C/FTS and output subfolders exist under PROJECT_ROOT."""
    try:
        # Create site-aware structure under Sites/<Site>/<Env>/...
        sites = SITE_OPTIONS if SITE_OPTIONS else ["Pico", "Tempe"]
        for site_name in sites:
            for env_name in ENV_FOLDERS:
                base_dir = os.path.join(PROJECT_ROOT, "Sites", site_name, env_name)
                os.makedirs(base_dir, exist_ok=True)
                os.makedirs(os.path.join(base_dir, "StreamInfo-CSVs"), exist_ok=True)
                os.makedirs(os.path.join(base_dir, "Input-Output-CSVs"), exist_ok=True)
    except Exception:
        # Non-fatal: permissions or other issues should not block app startup
        pass


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

        # Site selector
        ttk.Label(container, text="Site").grid(row=0, column=0, sticky="w")
        self.site_var = tk.StringVar(value=(SITE_OPTIONS[0] if SITE_OPTIONS else ""))
        self.site_combo = ttk.Combobox(container, textvariable=self.site_var, values=SITE_OPTIONS, state="readonly", width=int(round(30 * scale_factor)))
        self.site_combo.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.site_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_json_options())

        # TechEx Environment
        ttk.Label(container, text="TechEx Environment").grid(row=2, column=0, sticky="w")
        self.env_var = tk.StringVar(value=ENV_FOLDERS[0])
        self.env_combo = ttk.Combobox(container, textvariable=self.env_var, values=ENV_FOLDERS, state="readonly", width=int(round(30 * scale_factor)))
        self.env_combo.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        self.env_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_json_options())

        # Script
        ttk.Label(container, text="Script").grid(row=4, column=0, sticky="w")
        self.script_var = tk.StringVar(value="Stream Information")
        self.script_combo = ttk.Combobox(container, textvariable=self.script_var, values=list(SCRIPT_LABEL_TO_FUNC.keys()), state="readonly", width=int(round(30 * scale_factor)))
        self.script_combo.grid(row=5, column=0, sticky="ew", pady=(0, 8))

        # File Label (JSON/CSV depending on script)
        self.file_label = ttk.Label(container, text="JSON File")
        self.file_label.grid(row=6, column=0, sticky="w")
        refresh_btn = ttk.Button(container, text="Refresh", command=self._refresh_json_options)
        refresh_btn.grid(row=6, column=1, sticky="w", padx=(8, 0))
        self.json_var = tk.StringVar(value="")
        self.json_combo = ttk.Combobox(container, textvariable=self.json_var, values=[], state="readonly", width=int(round(50 * scale_factor)))
        self.json_combo.grid(row=7, column=0, sticky="ew", pady=(0, 12))

        # Convert all checkbox
        self.convert_all_var = tk.BooleanVar(value=False)
        self.convert_all_checkbox = ttk.Checkbutton(container, text="Convert ALL TechEx JSON Files", variable=self.convert_all_var)
        self.convert_all_checkbox.grid(row=8, column=0, sticky="w", pady=(0, 8))

        # Progress bar and active file label (shown during batch conversions)
        self.progress_var = tk.IntVar(value=0)
        self.progress = ttk.Progressbar(container, orient="horizontal", mode="determinate", maximum=0, variable=self.progress_var)
        self.progress.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(20, 0))
        self.active_file_var = tk.StringVar(value="")
        self.active_file_label = ttk.Label(container, textvariable=self.active_file_var, foreground="#555")
        self.active_file_label.grid(row=11, column=0, columnspan=2, sticky="w")

        # Run button
        self.run_button = ttk.Button(container, text="Run", command=self.on_run_clicked)
        self.run_button.grid(row=9, column=0, sticky="ew")
        self.open_folder_button = ttk.Button(container, text="Open Output Folder", command=self.on_open_output_folder)
        self.open_folder_button.grid(row=9, column=1, sticky="ew")

        # Fetch button
        self.fetch_button = ttk.Button(container, text="Fetch from Core", command=self.on_fetch_from_core)
        self.fetch_button.grid(row=12, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        # Status
        self.status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(container, textvariable=self.status_var, foreground="#555")
        self.status_label.grid(row=13, column=0, sticky="w", pady=(8, 0))

        # React to script changes to update labels and file lists
        self.script_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_json_options())

        self._refresh_json_options()

    def on_fetch_from_core(self) -> None:
        site = getattr(self, 'site_var', tk.StringVar(value="")).get()
        env = self.env_var.get()
        if not SITE_ENV_CONFIG:
            messagebox.showerror("Missing config", "Expected Scripts/site_env_config.json with site/env core addresses and tokens.")
            return
        if site not in SITE_ENV_CONFIG:
            messagebox.showerror("Invalid Site", f"Site '{site}' not found in configuration.")
            return
        if env not in SITE_ENV_CONFIG[site]:
            messagebox.showerror("Invalid Environment", f"Environment '{env}' not found under site '{site}' in configuration.")
            return

        try:
            from weaver_fetch import fetch_edges_configs
        except Exception as exc:
            messagebox.showerror("Missing dependency", f"Failed to import weaver_fetch.py: {exc}")
            return

        self.status_var.set("Fetching from Core...")
        self.run_button.configure(state=tk.DISABLED)
        self.fetch_button.configure(state=tk.DISABLED)

        def worker() -> None:
            try:
                cores = SITE_ENV_CONFIG[site][env].get("cores", [])
                token = SITE_ENV_CONFIG[site][env].get("token", "")
                target_dir = os.path.join(PROJECT_ROOT, "Sites", site, env)
                os.makedirs(target_dir, exist_ok=True)
                result = fetch_edges_configs(cores=cores, token=token, verify_https=True, delay_ms=10, output_dir=target_dir)
                saved = result.get("saved", [])
                self.after(0, lambda: messagebox.showinfo("Fetch complete", f"Saved {len(saved)} edge configs to:\n{target_dir}"))
            except Exception as exc2:
                self.after(0, lambda: messagebox.showerror("Fetch failed", str(exc2)))
            finally:
                self.after(0, lambda: self.run_button.configure(state=tk.NORMAL))
                self.after(0, lambda: self.fetch_button.configure(state=tk.NORMAL))
                self.after(0, lambda: self.status_var.set(""))
                self.after(0, self._refresh_json_options)

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_json_options(self) -> None:
        env_folder = self.env_var.get()
        site_folder = self.site_var.get()
        script_label = self.script_var.get()
        files = list_json_files(site_folder, env_folder)
        self.file_label.configure(text="JSON File")
        self.convert_all_checkbox.configure(text="Convert ALL TechEx JSON Files")
        self.json_combo["values"] = files
        self.json_var.set(files[0] if files else "")

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

        # Resolve conversion function
        convert_func = SCRIPT_LABEL_TO_FUNC.get(script_label)
        if convert_func is None:
            messagebox.showerror("Error", f"Conversion function not available for: {script_label}")
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
            if script_label == "Stream Information":
                output_base = f"{trimmed_base}-StreamInfo"
            else:
                output_base = trimmed_base
            # Route to subfolder based on script
            if script_label == "Stream Information":
                subfolder = "StreamInfo-CSVs"
            else:
                subfolder = "Input-Output-CSVs"
            env_output_dir = os.path.join(PROJECT_ROOT, "Sites", self.site_var.get(), env_folder, subfolder)
            os.makedirs(env_output_dir, exist_ok=True)
            ext = ".csv"
            return os.path.join(env_output_dir, f"{output_base}{ext}")

        # Batch or single
        if self.convert_all_var.get():
            all_files = list_json_files(self.site_var.get(), env_folder)
            none_msg = f"No JSON files found in '{env_folder}'."
            if not all_files:
                messagebox.showerror("Error", none_msg)
                self.status_var.set("Failed.")
                self.run_button.configure(state=tk.NORMAL)
                return

            # Prepare progress
            self.progress.configure(maximum=len(all_files))
            self.progress_var.set(0)
            self.active_file_var.set("")

            def worker() -> None:
                successes = 0
                failures = 0
                failure_msgs = []
                for idx, fname in enumerate(all_files, start=1):
                    self.after(0, lambda f=fname: self.active_file_var.set(f"Converting: {f}"))
                    input_abs_path = os.path.join(PROJECT_ROOT, "Sites", self.site_var.get(), env_folder, fname)
                    output_abs_path = make_output_path(fname)
                    try:
                        convert_func(input_abs_path, output_abs_path)  # type: ignore[misc]
                        successes += 1
                    except Exception as exc:
                        failures += 1
                        failure_msgs.append(f"{fname}: {str(exc)}")
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
            input_abs_path = os.path.join(PROJECT_ROOT, "Sites", self.site_var.get(), env_folder, json_file_name)
            if not os.path.exists(input_abs_path):
                messagebox.showerror("Error", f"Input JSON not found: {input_abs_path}")
                self.status_var.set("Failed.")
                return
            output_abs_path = make_output_path(json_file_name)
            try:
                convert_func(input_abs_path, output_abs_path)  # type: ignore[misc]
                self.status_var.set(f"Done: {os.path.relpath(output_abs_path, PROJECT_ROOT)}")
                messagebox.showinfo("Success", f"CSV created:\n{output_abs_path}")
            except Exception as exc:
                messagebox.showerror("Conversion failed", str(exc))
                self.status_var.set("Failed.")
        finally:
            self.run_button.configure(state=tk.NORMAL)

    def on_open_output_folder(self) -> None:
        env_folder = self.env_var.get()
        script_label = self.script_var.get()
        if not env_folder:
            messagebox.showerror("Error", "Please select a TechEx Environment.")
            return
        if not script_label:
            messagebox.showerror("Error", "Please select a Script.")
            return

        if script_label == "Stream Information":
            subfolder = "StreamInfo-CSVs"
        else:
            subfolder = "Input-Output-CSVs"

        target_dir = os.path.join(PROJECT_ROOT, "Sites", self.site_var.get(), env_folder, subfolder)
        try:
            os.makedirs(target_dir, exist_ok=True)
        except Exception as exc:
            messagebox.showerror("Error", f"Cannot create/access folder:\n{target_dir}\n\n{exc}")
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(target_dir)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", target_dir])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", target_dir])
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to open folder:\n{target_dir}\n\n{exc}")


def main() -> int:
    _hide_windows_console_if_present()
    _ensure_environment_structure()
    _load_conversion_functions_from_meipass()
    _update_script_mapping()
    app = TxEdgeGUI()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())


