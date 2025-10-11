import os
import json
from typing import List, Dict

# Local import
from weaver import Core


def _try_connect_core(addresses: List[str], token: str, verify_https: bool = True, delay_ms: int = 10) -> Core:
    last_exc = None
    for addr in addresses:
        try:
            core = Core(address=addr, token=token, verifyHTTPS=verify_https, defaultCallDelayMillis=delay_ms, bypassHttpConfirmation=True)
            # Basic probe to ensure token/addr is valid
            _ = core.version
            return core
        except Exception as e:
            last_exc = e
            continue
    if last_exc:
        raise last_exc
    raise RuntimeError("No core addresses provided")


def fetch_edges_configs(cores: List[str], token: str, verify_https: bool, delay_ms: int, output_dir: str) -> Dict:
    """
    Connect to the first healthy Core in the list, fetch online edges, then
    fetch each edge's full config JSON and write to output_dir as <edgeName>-config.json.

    Returns: { saved: [paths], edge_core_map: { edgeId: coreAddress } }
    """
    if not cores:
        raise ValueError("No core addresses provided")
    core = _try_connect_core(cores, token, verify_https=verify_https, delay_ms=delay_ms)

    saved_paths: List[str] = []
    edge_core_map: Dict[str, str] = {}

    edges = core.GetEdges(jsonQuery="online=true&limit=-1", enableCache=False)
    for edge in edges:
        try:
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

    return {"saved": saved_paths, "edge_core_map": edge_core_map}


