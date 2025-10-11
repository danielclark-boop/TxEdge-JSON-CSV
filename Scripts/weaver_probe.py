import os
import json
from typing import List, Dict, Optional
from datetime import datetime

from weaver import Core

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)
CONFIG_PATH = os.path.join(SCRIPTS_DIR, "site_env_config.json")
LOG_PATH = os.path.join(PROJECT_ROOT, "weaver_probe.log")


def log(msg: str, console: bool = True) -> None:
	line = f"[{datetime.utcnow().isoformat()}Z] {msg}"
	if console:
		print(line)
	try:
		with open(LOG_PATH, "a", encoding="utf-8") as f:
			f.write(line + "\n")
	except Exception:
		pass


def load_config() -> dict:
	try:
		with open(CONFIG_PATH, "r", encoding="utf-8") as f:
			return json.load(f)
	except Exception as e:
		raise RuntimeError(f"Failed to load config: {CONFIG_PATH}: {e}")


def try_core(addr: str, token: str, verify_https: bool, delay_ms: int) -> Optional[Core]:
	try:
		log(f"Trying core: {addr}")
		core = Core(address=addr, token=token, verifyHTTPS=verify_https, defaultCallDelayMillis=delay_ms, bypassHttpConfirmation=True)
		log(f"Connected. Core version: {core.version}")
		return core
	except Exception as e:
		log(f"Failed core {addr}: {e}")
		return None


def probe(site: str, env: str, delay_ms: int = 10) -> int:
	cfg = load_config()
	if site not in cfg:
		raise RuntimeError(f"Site not found in config: {site}")
	if env not in cfg[site]:
		raise RuntimeError(f"Env not found in config for site {site}: {env}")
	entry = cfg[site][env]
	cores: List[str] = entry.get("cores", [])
	token: str = entry.get("token", "")
	verify_https: bool = entry.get("verifyHTTPS", True)
	if not cores or not token:
		raise RuntimeError("Missing 'cores' or 'token' in site_env_config.json")

	core_used: Optional[str] = None
	core_obj: Optional[Core] = None
	for addr in cores:
		core_obj = try_core(addr, token, verify_https, delay_ms)
		if core_obj:
			core_used = addr
			break
	if not core_obj:
		raise RuntimeError("No cores reachable")

	log("Fetching edges: online=true&limit=-1")
	edges = core_obj.GetEdges(jsonQuery="online=true&limit=-1", enableCache=False)
	log(f"Found {len(edges)} edges")
	for e in edges:
		log(f"Edge: {e.name} ({e._id}) @ core {core_used}")
	return 0


if __name__ == "__main__":
	# Defaults for quick test; change as needed or run via: python3 Scripts/weaver_probe.py Pico TDP
	import sys
	args = sys.argv[1:]
	if len(args) >= 2:
		site = args[0]
		env = args[1]
	else:
		print("Usage: python3 Scripts/weaver_probe.py <Site> <Env>")
		sys.exit(1)
	try:
		code = probe(site, env)
		sys.exit(code)
	except Exception as ex:
		log(f"Probe failed: {ex}")
		sys.exit(2)
