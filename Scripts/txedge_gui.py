#!/usr/bin/env python3
import os
import sys
import tkinter.font as tkfont
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import json

# Make sibling scripts importable and import conversion functions
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.append(SCRIPTS_DIR)
try:
    from txedge_to_csv import convert_txedge_to_csv  # type: ignore
    from txedge_to_csv_streams_sources import convert_streams_sources  # type: ignore
    from editable_exports import convert_stream_edit, convert_input_edit, convert_output_edit  # type: ignore
except Exception:
    # If running in an unusual environment (e.g., frozen onefile), load later with a fallback
    convert_txedge_to_csv = None  # type: ignore
    convert_streams_sources = None  # type: ignore
    convert_stream_edit = None  # type: ignore
    convert_input_edit = None  # type: ignore
    convert_output_edit = None  # type: ignore


if getattr(sys, "frozen", False):
    PROJECT_ROOT = os.path.dirname(sys.executable)
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FOLDERS = ["TDP", "D2C", "FTS"]
SCRIPT_LABEL_TO_FUNC = {
    "Stream Information": convert_streams_sources,
    "Input/Output Information": convert_txedge_to_csv,
    "Create Editable CSVs": None,  # Handled specially: runs all three edit exporters
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
# Only include keys that look like sites (contain at least one known environment)
if SITE_ENV_CONFIG:
    SITE_OPTIONS = sorted([
        k for k, v in SITE_ENV_CONFIG.items()
        if isinstance(v, dict) and any(env in v for env in ("TDP", "D2C", "FTS"))
    ])
else:
    SITE_OPTIONS = ["Pico", "Tempe"]


def list_json_files(site_folder: str, env_folder: str) -> list:
    env_path = os.path.join(PROJECT_ROOT, "Sites", site_folder, env_folder)
    try:
        files = sorted(
            [f for f in os.listdir(env_path) if f.lower().endswith(".json")]
        )
    except FileNotFoundError:
        files = []
    return files


def list_import_csvs(site_folder: str, env_folder: str, import_type: str) -> list:
    base = os.path.join(PROJECT_ROOT, "Sites", site_folder, env_folder, "Editable-CSVs")
    sub = "Streams" if import_type == "Update Streams" else ("Sources" if import_type == "Update Inputs" else "Outputs")
    target = os.path.join(base, sub)
    try:
        files = sorted([f for f in os.listdir(target) if f.lower().endswith(".csv")])
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
    global convert_txedge_to_csv, convert_streams_sources, convert_stream_edit, convert_input_edit, convert_output_edit
    if (
        (convert_txedge_to_csv is not None)
        and (convert_streams_sources is not None)
        and (convert_stream_edit is not None)
        and (convert_input_edit is not None)
        and (convert_output_edit is not None)
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
        # editable_exports.py
        ee_mod_path = os.path.join(base_dir, "Scripts", "editable_exports.py")
        if (convert_stream_edit is None or convert_input_edit is None or convert_output_edit is None) and os.path.exists(ee_mod_path):
            spec3 = importlib.util.spec_from_file_location("editable_exports", ee_mod_path)
            if spec3 and spec3.loader:
                module3 = importlib.util.module_from_spec(spec3)
                spec3.loader.exec_module(module3)  # type: ignore[attr-defined]
                convert_stream_edit = getattr(module3, "convert_stream_edit", None)
                convert_input_edit = getattr(module3, "convert_input_edit", None)
                convert_output_edit = getattr(module3, "convert_output_edit", None)
    except Exception:
        # Non-fatal; handled by UI error message later
        pass


def _update_script_mapping() -> None:
    """Refresh mapping after late imports in frozen builds."""
    SCRIPT_LABEL_TO_FUNC["Stream Information"] = convert_streams_sources  # type: ignore[index]
    SCRIPT_LABEL_TO_FUNC["Input/Output Information"] = convert_txedge_to_csv  # type: ignore[index]
    SCRIPT_LABEL_TO_FUNC["Create Editable CSVs"] = None  # type: ignore[index]


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
                os.makedirs(os.path.join(base_dir, "Editable-CSVs", "Streams"), exist_ok=True)
                os.makedirs(os.path.join(base_dir, "Editable-CSVs", "Sources"), exist_ok=True)
                os.makedirs(os.path.join(base_dir, "Editable-CSVs", "Outputs"), exist_ok=True)
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

        # Mode selector row
        mode_frame = ttk.Frame(self, padding=(16, 16))
        mode_frame.grid(row=0, column=0, sticky="ew")
        mode_frame.grid_columnconfigure(0, weight=1)
        mode_frame.grid_columnconfigure(1, weight=1)
        self.mode_var = tk.StringVar(value="")
        self.export_button = ttk.Button(mode_frame, text="Export", command=self.on_select_export)
        self.import_button = ttk.Button(mode_frame, text="Import", command=self.on_select_import)
        self.sheets_button = ttk.Button(mode_frame, text="Google Sheets", command=self.on_select_sheets)
        self.export_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.import_button.grid(row=0, column=1, sticky="ew", padx=(8, 8))
        self.sheets_button.grid(row=0, column=2, sticky="ew")

        container = ttk.Frame(self, padding=16)
        container.grid(row=1, column=0, sticky="nsew")

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

        # Conversion Type
        ttk.Label(container, text="Conversion Type").grid(row=4, column=0, sticky="w")
        self.script_var = tk.StringVar(value="Stream Information")
        self.script_combo = ttk.Combobox(container, textvariable=self.script_var, values=list(SCRIPT_LABEL_TO_FUNC.keys()), state="readonly", width=int(round(30 * scale_factor)))
        self.script_combo.grid(row=5, column=0, sticky="ew", pady=(0, 8))

        # File Label (JSON/CSV depending on script)
        self.file_label = ttk.Label(container, text="JSON File")
        self.file_label.grid(row=6, column=0, sticky="w", pady=(12, 0))
        refresh_btn = ttk.Button(container, text="Refresh", command=self._refresh_json_options)
        # Place Refresh at column 2 to allow Fetch button to sit to its left at column 1
        refresh_btn.grid(row=6, column=2, sticky="w", padx=(8, 0))
        self.json_var = tk.StringVar(value="")
        self.json_combo = ttk.Combobox(container, textvariable=self.json_var, values=[], state="readonly", width=int(round(50 * scale_factor)))
        self.json_combo.grid(row=7, column=0, sticky="ew", pady=(4, 12))

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

        # Debug mode
        self.debug_var = tk.BooleanVar(value=False)
        self.debug_checkbox = ttk.Checkbutton(container, text="Debug (console + log)", variable=self.debug_var)
        self.debug_checkbox.grid(row=12, column=0, sticky="w")

        # Fetch button next to Refresh (left of it)
        self.fetch_button = ttk.Button(container, text="Fetch from Core", command=self.on_fetch_from_core)
        self.fetch_button.grid(row=6, column=1, sticky="w", padx=(8, 8))

        # Status
        self.status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(container, textvariable=self.status_var, foreground="#555")
        self.status_label.grid(row=13, column=0, sticky="w", pady=(8, 0))

        # React to conversion type changes to update file list
        self.script_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_json_options())

        # Track and hide content until a mode is selected
        self._shared_widgets = [self.progress, self.active_file_label, self.run_button, self.status_label]
        self._export_widgets = [
            # Site/env and export-specific controls
            self.site_combo, self.env_combo,
            self.script_combo,
            self.file_label, refresh_btn, self.json_combo,
            self.convert_all_checkbox,
            self.debug_checkbox, self.fetch_button,
            self.open_folder_button,
        ]
        # Include labels for site/env/conversion
        # Retrieve label widgets via grid_slaves filtering by row/column
        for w in container.grid_slaves():
            if isinstance(w, ttk.Label) and w.cget("text") in ("Site", "TechEx Environment", "Conversion Type"):
                self._export_widgets.append(w)

        self._hide_widgets(self._export_widgets + self._shared_widgets)
        self._import_frame = None
        self._sheets_frame = None

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
                log_path = os.path.join(PROJECT_ROOT, "weaver_fetch.log") if self.debug_var.get() else None
                verify_https = SITE_ENV_CONFIG[site][env].get("verifyHTTPS", True)
                result = fetch_edges_configs(cores=cores, token=token, verify_https=verify_https, delay_ms=10, output_dir=target_dir, log_to_console=self.debug_var.get(), log_file_path=log_path)
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

    def _hide_widgets(self, widgets: list) -> None:
        for w in widgets:
            try:
                w.grid_remove()
            except Exception:
                pass

    def _show_widgets(self, widgets: list) -> None:
        for w in widgets:
            try:
                w.grid()
            except Exception:
                pass

    def on_select_export(self) -> None:
        self.mode_var.set("export")
        # Hide import UI if present
        if self._import_frame is not None:
            try:
                self._import_frame.grid_remove()
            except Exception:
                pass
        if self._sheets_frame is not None:
            try:
                self._sheets_frame.grid_remove()
            except Exception:
                pass
        self._show_widgets(self._export_widgets + self._shared_widgets)
        self._refresh_json_options()

    def on_select_import(self) -> None:
        self.mode_var.set("import")
        # Password gate
        pw = simpledialog.askstring("Authentication", "Enter Import password:", show='*')
        if pw != "RF36111":
            messagebox.showerror("Access denied", "Incorrect password.")
            self.mode_var.set("")
            return
        # Hide export UI, show shared + import frame
        self._hide_widgets(self._export_widgets)
        self._show_widgets(self._shared_widgets)
        if self._import_frame is None:
            self._build_import_ui(parent=self.children[list(self.children.keys())[1]])
        try:
            self._import_frame.grid()
        except Exception:
            pass

    def _build_import_ui(self, parent: ttk.Frame) -> None:
        # Build minimal import controls: Site/Env selectors for import context
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=0, sticky="nsew")
        ttk.Label(frame, text="Site").grid(row=0, column=0, sticky="w")
        self.import_site_var = tk.StringVar(value=self.site_var.get())
        self.import_site_combo = ttk.Combobox(frame, textvariable=self.import_site_var, values=SITE_OPTIONS, state="readonly")
        self.import_site_combo.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(frame, text="TechEx Environment").grid(row=2, column=0, sticky="w")
        self.import_env_var = tk.StringVar(value=self.env_var.get())
        self.import_env_combo = ttk.Combobox(frame, textvariable=self.import_env_var, values=ENV_FOLDERS, state="readonly")
        self.import_env_combo.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        # Import Type
        ttk.Label(frame, text="Import Type").grid(row=4, column=0, sticky="w")
        self.import_type_var = tk.StringVar(value="Update Streams")
        self.import_type_combo = ttk.Combobox(frame, textvariable=self.import_type_var, values=["Update Streams", "Update Inputs", "Update Outputs"], state="readonly")
        self.import_type_combo.grid(row=5, column=0, sticky="ew", pady=(0, 8))
        self.import_type_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_import_files())

        # Import file selector with Refresh and View buttons
        ttk.Label(frame, text="Import CSV").grid(row=6, column=0, sticky="w")
        self.import_refresh_btn = ttk.Button(frame, text="Refresh", command=self._refresh_import_files)
        self.import_refresh_btn.grid(row=6, column=2, sticky="w", padx=(8, 0))
        self.import_view_btn = ttk.Button(frame, text="View Import Directory", command=self.on_open_import_folder)
        self.import_view_btn.grid(row=6, column=1, sticky="w", padx=(8, 8))
        self.import_file_var = tk.StringVar(value="")
        self.import_file_combo = ttk.Combobox(frame, textvariable=self.import_file_var, values=[], state="readonly", width=60)
        self.import_file_combo.grid(row=7, column=0, sticky="ew", pady=(4, 12))

        # Debug for import
        self.import_debug_var = tk.BooleanVar(value=False)
        self.import_debug_checkbox = ttk.Checkbutton(frame, text="Debug (import)", variable=self.import_debug_var)
        self.import_debug_checkbox.grid(row=8, column=0, sticky="w")

        # Bind changes
        self.import_site_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_import_files())
        self.import_env_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_import_files())
        self._refresh_import_files()
        self._import_frame = frame

    def on_select_sheets(self) -> None:
        self.mode_var.set("sheets")
        # Hide export/import widgets
        self._hide_widgets(self._export_widgets + self._shared_widgets)
        if self._import_frame is not None:
            try:
                self._import_frame.grid_remove()
            except Exception:
                pass
        if self._sheets_frame is None:
            self._build_sheets_ui(parent=self.children[list(self.children.keys())[1]])
        try:
            self._sheets_frame.grid()
        except Exception:
            pass

    def _build_sheets_ui(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=0, sticky="nsew")
        # Site & Env
        ttk.Label(frame, text="Site").grid(row=0, column=0, sticky="w")
        self.sheets_site_var = tk.StringVar(value=self.site_var.get())
        self.sheets_site_combo = ttk.Combobox(frame, textvariable=self.sheets_site_var, values=SITE_OPTIONS, state="readonly")
        self.sheets_site_combo.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(frame, text="TechEx Environment").grid(row=2, column=0, sticky="w")
        self.sheets_env_var = tk.StringVar(value=self.env_var.get())
        self.sheets_env_combo = ttk.Combobox(frame, textvariable=self.sheets_env_var, values=ENV_FOLDERS, state="readonly")
        self.sheets_env_combo.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        # File list with checkboxes (Streams/Sources/Outputs together)
        ttk.Label(frame, text="Editable CSVs (Streams/Sources/Outputs)").grid(row=4, column=0, sticky="w")
        list_container = ttk.Frame(frame)
        list_container.grid(row=5, column=0, sticky="nsew")
        frame.grid_rowconfigure(5, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        canvas = tk.Canvas(list_container, height=220)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        self.files_inner = ttk.Frame(canvas)
        self.files_inner.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.files_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)

        self._sheets_file_vars: dict[str, tk.BooleanVar] = {}
        def refresh_files():
            for w in list(self.files_inner.children.values()):
                try:
                    w.destroy()
                except Exception:
                    pass
            site = self.sheets_site_var.get()
            env = self.sheets_env_var.get()
            base = os.path.join(PROJECT_ROOT, "Sites", site, env, "Editable-CSVs")
            subfolders = ["Streams", "Sources", "Outputs"]
            files = []
            for sf in subfolders:
                path = os.path.join(base, sf)
                try:
                    for f in os.listdir(path):
                        if f.lower().endswith('.csv'):
                            files.append((sf, os.path.join(path, f)))
                except FileNotFoundError:
                    continue
            for sf, fp in sorted(files, key=lambda x: os.path.basename(x[1]).lower()):
                var = tk.BooleanVar(value=False)
                self._sheets_file_vars[fp] = var
                cb = ttk.Checkbutton(self.files_inner, text=f"{sf}/" + os.path.basename(fp), variable=var)
                cb.pack(anchor="w")
        refresh_files()
        self.sheets_site_combo.bind("<<ComboboxSelected>>", lambda e: refresh_files())
        self.sheets_env_combo.bind("<<ComboboxSelected>>", lambda e: refresh_files())

        # Action buttons
        btns = ttk.Frame(frame)
        btns.grid(row=6, column=0, sticky="ew", pady=(8, 0))
        push_btn = ttk.Button(btns, text="Push to Sheets", command=self._on_sheets_push)
        pull_btn = ttk.Button(btns, text="Update from Sheets", command=self._on_sheets_pull)
        push_btn.grid(row=0, column=0, sticky="w")
        pull_btn.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self._sheets_frame = frame

    def _get_sheets_config(self, site: str) -> tuple[str, str]:
        site_cfg = SITE_ENV_CONFIG.get(site, {})
        url = site_cfg.get("SheetsURL") or SITE_ENV_CONFIG.get("SheetsURL")
        key = SITE_ENV_CONFIG.get("SheetsAPIkey", "")
        return url, key

    def _collect_selected_files(self) -> list[str]:
        return [fp for fp, var in self._sheets_file_vars.items() if var.get()]

    def _on_sheets_push(self) -> None:
        site = self.sheets_site_var.get()
        url, key = self._get_sheets_config(site)
        if not url or not key:
            messagebox.showerror("Missing config", "SheetsURL or SheetsAPIkey is missing in site_env_config.json")
            return
        try:
            from sheets_bridge import push_csv_files_to_sheets  # type: ignore
        except Exception as exc:
            messagebox.showerror("Error", f"sheets_bridge not available: {exc}")
            return
        files = self._collect_selected_files()
        if not files:
            messagebox.showerror("Error", "No CSV files selected.")
            return
        res = push_csv_files_to_sheets(url, key, files)
        if not res.get("success"):
            messagebox.showerror("Push failed", json.dumps(res, indent=2))
        else:
            count = len(self._collect_selected_files())
            messagebox.showinfo("Success", f"Successfully Pushed {count} file(s) to Google Sheets")

    def _on_sheets_pull(self) -> None:
        site = self.sheets_site_var.get()
        env = self.sheets_env_var.get()
        url, key = self._get_sheets_config(site)
        if not url or not key:
            messagebox.showerror("Missing config", "SheetsURL or SheetsAPIkey is missing in site_env_config.json")
            return
        try:
            from sheets_bridge import pull_csvs_from_sheets_to_files  # type: ignore
        except Exception as exc:
            messagebox.showerror("Error", f"sheets_bridge not available: {exc}")
            return
        files = self._collect_selected_files()
        if not files:
            messagebox.showerror("Error", "No CSV files selected.")
            return
        # Map tab names to file paths (tab = file name without .csv)
        tab_to_file = {}
        for fp in files:
            name = os.path.splitext(os.path.basename(fp))[0]
            tab_to_file[name] = fp
        res = pull_csvs_from_sheets_to_files(url, key, tab_to_file)
        if not res.get("success"):
            messagebox.showerror("Pull failed", json.dumps(res, indent=2))
        else:
            count = len(res.get("written", []))
            messagebox.showinfo("Success", f"Successfully Pulled {count} file(s) from Google Sheets")

    def _refresh_import_files(self) -> None:
        site = getattr(self, 'import_site_var', tk.StringVar(value="")).get()
        env = getattr(self, 'import_env_var', tk.StringVar(value="")).get()
        itype = getattr(self, 'import_type_var', tk.StringVar(value="Update Streams")).get()
        files = list_import_csvs(site, env, itype)
        if hasattr(self, 'import_file_combo'):
            self.import_file_combo["values"] = files
            self.import_file_var.set(files[0] if files else "")

    def _refresh_json_options(self) -> None:
        if self.mode_var.get() != "export":
            return
        env_folder = self.env_var.get()
        site_folder = self.site_var.get()
        script_label = self.script_var.get()
        files = list_json_files(site_folder, env_folder)
        self.file_label.configure(text="JSON File")
        self.convert_all_checkbox.configure(text="Convert ALL TechEx JSON Files")
        self.json_combo["values"] = files
        self.json_var.set(files[0] if files else "")

    def on_run_clicked(self) -> None:
        if self.mode_var.get() == "import":
            return self._on_run_import()
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

        # Resolve conversion function (with lazy import fallback for editable exports)
        convert_func = SCRIPT_LABEL_TO_FUNC.get(script_label)
        if convert_func is None:
            if script_label == "Create Editable CSVs":
                # Special case handled elsewhere; no single function required
                convert_func = None
            elif script_label in ("Stream Edit", "Input Edit", "Output Edit"):
                try:
                    from editable_exports import convert_stream_edit as _cse, convert_input_edit as _cie, convert_output_edit as _coe  # type: ignore
                    SCRIPT_LABEL_TO_FUNC["Stream Edit"] = _cse
                    SCRIPT_LABEL_TO_FUNC["Input Edit"] = _cie
                    SCRIPT_LABEL_TO_FUNC["Output Edit"] = _coe
                    convert_func = SCRIPT_LABEL_TO_FUNC.get(script_label)
                except Exception as _e:
                    messagebox.showerror("Error", f"Missing editable export converters: {str(_e)}")
                    return
            if convert_func is None and script_label != "Create Editable CSVs":
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
                subfolder = "StreamInfo-CSVs"
            elif script_label == "Input/Output Information":
                output_base = trimmed_base
                subfolder = "Input-Output-CSVs"
            elif script_label == "Create Editable CSVs":
                # This path is not used directly; multi-export builds specific names
                output_base = trimmed_base
                subfolder = os.path.join("Editable-CSVs")
            else:
                output_base = trimmed_base
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
                    try:
                        if script_label == "Create Editable CSVs":
                            self._run_all_edit_exports(input_abs_path, env_folder)
                        else:
                            output_abs_path = make_output_path(fname)
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
            try:
                if script_label == "Create Editable CSVs":
                    self._run_all_edit_exports(input_abs_path, env_folder)
                    self.status_var.set("Done: Editable CSVs created")
                    messagebox.showinfo("Success", f"Editable CSVs created for:\n{json_file_name}")
                else:
                    output_abs_path = make_output_path(json_file_name)
                    convert_func(input_abs_path, output_abs_path)  # type: ignore[misc]
                    self.status_var.set(f"Done: {os.path.relpath(output_abs_path, PROJECT_ROOT)}")
                    messagebox.showinfo("Success", f"CSV created:\n{output_abs_path}")
            except Exception as exc:
                messagebox.showerror("Conversion failed", str(exc))
                self.status_var.set("Failed.")
        finally:
            self.run_button.configure(state=tk.NORMAL)

    def _run_all_edit_exports(self, input_abs_path: str, env_folder: str) -> None:
        # Lazy import to ensure availability
        try:
            from editable_exports import convert_stream_edit as _cse, convert_input_edit as _cie, convert_output_edit as _coe  # type: ignore
        except Exception as _e:
            raise RuntimeError(f"Editable export converters not available: {_e}")
        base_no_ext = os.path.splitext(os.path.basename(input_abs_path))[0]
        base_lower = base_no_ext.lower()
        trimmed_base = base_no_ext[:-len("-config")] if base_lower.endswith("-config") else base_no_ext
        site = self.site_var.get()
        # Streams
        out_dir = os.path.join(PROJECT_ROOT, "Sites", site, env_folder, "Editable-CSVs", "Streams")
        os.makedirs(out_dir, exist_ok=True)
        _cse(input_abs_path, os.path.join(out_dir, f"{trimmed_base}-Streams.csv"))
        # Sources
        out_dir = os.path.join(PROJECT_ROOT, "Sites", site, env_folder, "Editable-CSVs", "Sources")
        os.makedirs(out_dir, exist_ok=True)
        _cie(input_abs_path, os.path.join(out_dir, f"{trimmed_base}-Sources.csv"))
        # Outputs
        out_dir = os.path.join(PROJECT_ROOT, "Sites", site, env_folder, "Editable-CSVs", "Outputs")
        os.makedirs(out_dir, exist_ok=True)
        _coe(input_abs_path, os.path.join(out_dir, f"{trimmed_base}-Outputs.csv"))

    def _on_run_import(self) -> None:
        site = self.import_site_var.get()
        env = self.import_env_var.get()
        itype = self.import_type_var.get()
        csv_name = self.import_file_var.get()
        if not site or not env or not itype or not csv_name:
            messagebox.showerror("Error", "Please select Site, Environment, Import Type and a CSV file.")
            return
        # Import lazily
        try:
            from import_editables import import_streams, import_sources, import_outputs, _connect_core  # type: ignore
        except Exception as exc:
            messagebox.showerror("Error", f"Import module not available: {exc}")
            return
        # Prepare paths
        sub = "Streams" if itype == "Update Streams" else ("Sources" if itype == "Update Inputs" else "Outputs")
        target_dir = os.path.join(PROJECT_ROOT, "Sites", site, env, "Editable-CSVs", sub)
        csv_path = os.path.join(target_dir, csv_name)
        if not os.path.exists(csv_path):
            messagebox.showerror("Error", f"CSV not found: {csv_path}")
            return
        # Read first row to determine edge id (mwedge)
        edge_id = None
        try:
            import csv as _csv
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = _csv.DictReader(f)
                for row in reader:
                    edge_id = row.get("mwedge")
                    if edge_id:
                        break
        except Exception:
            pass
        if not edge_id:
            messagebox.showerror("Error", "Cannot determine edge id (mwedge) from the CSV.")
            return
        # Connect to core
        cores = SITE_ENV_CONFIG.get(site, {}).get(env, {}).get("cores", [])
        token = SITE_ENV_CONFIG.get(site, {}).get(env, {}).get("token", "")
        verify_https = SITE_ENV_CONFIG.get(site, {}).get(env, {}).get("verifyHTTPS", True)
        if not cores or not token:
            messagebox.showerror("Error", "Missing cores or token in site_env_config.json for the selected Site/Environment.")
            return
        self.status_var.set("Importing...")
        self.run_button.configure(state=tk.DISABLED)
        self.update_idletasks()

        def worker() -> None:
            try:
                core, used_addr = _connect_core(cores, token, verify_https, 10, os.path.join(PROJECT_ROOT, "weaver_import.log") if self.import_debug_var.get() else None)
                logp = os.path.join(PROJECT_ROOT, "weaver_import.log") if self.import_debug_var.get() else None
                if itype == "Update Streams":
                    summary = import_streams(csv_path, core, edge_id, logp)
                elif itype == "Update Inputs":
                    summary = import_sources(csv_path, core, edge_id, logp)
                else:
                    summary = import_outputs(csv_path, core, edge_id, logp)
                self.after(0, lambda: messagebox.showinfo("Import complete", f"Created: {summary.get('created',0)}\nUpdated: {summary.get('updated',0)}\nSkipped: {summary.get('skipped',0)}\nFailed: {summary.get('failed',0)}"))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Import failed", str(exc)))
            finally:
                self.after(0, lambda: self.run_button.configure(state=tk.NORMAL))
                self.after(0, lambda: self.status_var.set(""))

        threading.Thread(target=worker, daemon=True).start()

    def on_open_import_folder(self) -> None:
        site = self.import_site_var.get()
        env = self.import_env_var.get()
        itype = self.import_type_var.get()
        sub = "Streams" if itype == "Update Streams" else ("Sources" if itype == "Update Inputs" else "Outputs")
        target_dir = os.path.join(PROJECT_ROOT, "Sites", site, env, "Editable-CSVs", sub)
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
        elif script_label == "Input/Output Information":
            subfolder = "Input-Output-CSVs"
        elif script_label == "Stream Edit":
            subfolder = os.path.join("Editable-CSVs", "Streams")
        elif script_label == "Input Edit":
            subfolder = os.path.join("Editable-CSVs", "Sources")
        elif script_label == "Output Edit":
            subfolder = os.path.join("Editable-CSVs", "Outputs")
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


