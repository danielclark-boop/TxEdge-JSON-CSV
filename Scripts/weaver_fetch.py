import os
import json
from datetime import datetime
from typing import List, Dict, Optional

# Local import
from weaver import Core


def _log(msg: str, log_file: Optional[str], console: bool) -> None:
    timestamped = f"[{datetime.utcnow().isoformat()}Z] {msg}"
    if console:
        print(timestamped)
    if log_file:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(timestamped + "\n")
        except Exception:
            pass


def _try_connect_core(addresses: List[str], token: str, verify_https: bool = True, delay_ms: int = 10, log_file: Optional[str] = None, console: bool = False) -> tuple[Core, str]:
    last_exc = None
    for addr in addresses:
        try:
            _log(f"Trying core: {addr}", log_file, console)
            core = Core(address=addr, token=token, verifyHTTPS=verify_https, defaultCallDelayMillis=delay_ms, bypassHttpConfirmation=True)
            _log(f"Connected. Core version: {core.version}", log_file, console)
            return core, addr
        except Exception as e:
            last_exc = e
            _log(f"Failed core {addr}: {e}", log_file, console)
            continue
    if last_exc:
        raise last_exc
    raise RuntimeError("No core addresses provided")


def fetch_edges_configs(cores: List[str], token: str, verify_https: bool, delay_ms: int, output_dir: str, log_to_console: bool = False, log_file_path: Optional[str] = None) -> Dict:
    """
    Connect to the first healthy Core in the list, fetch online edges, then
    fetch each edge's full config JSON and write to output_dir as <edgeName>-config.json.

    Returns: { saved: [paths], edge_core_map: { edgeId: coreAddress } }
    """
    if not cores:
        raise ValueError("No core addresses provided")
    core, used_addr = _try_connect_core(cores, token, verify_https=verify_https, delay_ms=delay_ms, log_file=log_file_path, console=log_to_console)

    saved_paths: List[str] = []
    edge_core_map: Dict[str, str] = {}

    _log("Fetching edges: online=true&limit=-1", log_file_path, log_to_console)
    try:
        edges = core.GetEdges(jsonQuery="online=true&limit=-1", enableCache=False)
    except Exception as e:
        _log(f"Edge fetch failed: {e}", log_file_path, log_to_console)
        # Try next cores if available
        remaining = [c for c in cores if c != used_addr]
        if not remaining:
            raise
        _log("Retrying with next core...", log_file_path, log_to_console)
        core, used_addr = _try_connect_core(remaining, token, verify_https=verify_https, delay_ms=delay_ms, log_file=log_file_path, console=log_to_console)
        edges = core.GetEdges(jsonQuery="online=true&limit=-1", enableCache=False)
    _log(f"Found {len(edges)} edges", log_file_path, log_to_console)
    for edge in edges:
        try:
            _log(f"Fetching config for edge: {edge.name} ({edge._id})", log_file_path, log_to_console)
            resp = core.GetEdgeById(edge._id, enableCache=False)
            raw = json.loads(resp.__repr__()) if hasattr(resp, "__repr__") else json.loads(resp.__str__()) if hasattr(resp, "__str__") else None
        except Exception:
            # Fallback to API response text
            api_resp = core.GetEdgeById(edge._id)
            raw_text = api_resp.text
            raw = json.loads(raw_text)

        # Save mapping of edge->core
        edge_core_map[edge._id] = core.coreAddress

        # Determine file name
        edge_name = edge.name or edge._id
        base_no_ext = f"{edge_name}-config"
        path = os.path.join(output_dir, f"{base_no_ext}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw, f, indent=2)
        saved_paths.append(path)
        _log(f"Saved: {path}", log_file_path, log_to_console)

    _log("Fetch complete", log_file_path, log_to_console)
    return {"saved": saved_paths, "edge_core_map": edge_core_map}


