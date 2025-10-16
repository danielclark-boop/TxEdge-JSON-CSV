import csv
import json
import os
from typing import Dict, Any, List, Tuple
from datetime import datetime

import weaver
from weaver import Core


def _log(msg: str, log_file: str | None) -> None:
	line = f"[{datetime.utcnow().isoformat()}Z] {msg}"
	print(line)
	if log_file:
		try:
			with open(log_file, "a", encoding="utf-8") as f:
				f.write(line + "\n")
		except Exception:
			pass


def _unflatten(row: Dict[str, str]) -> Dict[str, Any]:
	"""Convert dotted keys to nested dicts and coerce basic types."""
	obj: Dict[str, Any] = {}
	for key, value in row.items():
		if key == "" or value is None:
			continue
		# Skip state entirely
		if key == "state" or key.startswith("state."):
			continue
		parts = key.split(".")
		tgt = obj
		for p in parts[:-1]:
			tgt = tgt.setdefault(p, {})
		leaf = parts[-1]
		# Type coercions
		v: Any = value
		if isinstance(v, str):
			vs = v.strip()
			if vs == "":
				v = None
			elif vs.lower() in ("true", "false"):
				v = vs.lower() == "true"
			else:
				# try int/float, else keep string
				try:
					v = int(vs)
				except Exception:
					try:
						v = float(vs)
					except Exception:
						v = vs
		tgt[leaf] = v
	return obj


def _connect_core(cores: List[str], token: str, verify_https: bool, delay_ms: int, log_file: str | None) -> Tuple[Core, str]:
	last = None
	for addr in cores:
		try:
			_log(f"Connecting core: {addr}", log_file)
			c = Core(address=addr, token=token, verifyHTTPS=verify_https, defaultCallDelayMillis=delay_ms, bypassHttpConfirmation=True)
			# Probe
			_ = c.version
			return c, addr
		except Exception as e:
			last = e
			_log(f"Failed: {addr}: {e}", log_file)
	if last:
		raise last
	raise RuntimeError("No reachable cores")


def import_streams(csv_path: str, core: Core, edge_id: str, log_file: str | None = None) -> Dict[str, int]:
	"""Create/update streams from CSV rows."""
	created = updated = failed = 0
	with open(csv_path, "r", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		for row in reader:
			obj = _unflatten(row)
			obj["mwedge"] = edge_id
			try:
				if obj.get("id"):
					# update
					st = weaver.Stream(core.GetEdgeById(edge_id), obj)
					ok = st.Update()
					updated += 1 if ok else 0
					if not ok:
						failed += 1
				else:
					# create
					st = weaver.Stream(core.GetEdgeById(edge_id), obj)
					st.id = None
					created_obj = core.GetEdgeById(edge_id).CreateStream(st)
					created += 1 if created_obj else 0
			except Exception as e:
				failed += 1
				_log(f"Stream row failed: {e}", log_file)
	return {"created": created, "updated": updated, "failed": failed}


def import_sources(csv_path: str, core: Core, edge_id: str, log_file: str | None = None) -> Dict[str, int]:
	created = updated = failed = 0
	edge = core.GetEdgeById(edge_id)
	with open(csv_path, "r", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		for row in reader:
			obj = _unflatten(row)
			obj["mwedge"] = edge_id
			try:
				if obj.get("id"):
					src = weaver.Source(edge, obj)
					ok = src.Update()
					updated += 1 if ok else 0
					if not ok:
						failed += 1
				else:
					src = weaver.Source(edge, obj)
					src.id = 0
					created_obj = edge.CreateSource(src)
					created += 1 if created_obj else 0
			except Exception as e:
				failed += 1
				_log(f"Source row failed: {e}", log_file)
	return {"created": created, "updated": updated, "failed": failed}


def import_outputs(csv_path: str, core: Core, edge_id: str, log_file: str | None = None) -> Dict[str, int]:
	created = updated = failed = 0
	edge = core.GetEdgeById(edge_id)
	with open(csv_path, "r", encoding="utf-8") as f:
		reader = csv.DictReader(f)
		for row in reader:
			obj = _unflatten(row)
			obj["mwedge"] = edge_id
			try:
				if obj.get("id"):
					outp = weaver.Output(edge, obj)
					ok = outp.Update()
					updated += 1 if ok else 0
					if not ok:
						failed += 1
				else:
					outp = weaver.Output(edge, obj)
					outp.id = 0
					created_obj = edge.CreateOutput(outp)
					created += 1 if created_obj else 0
			except Exception as e:
				failed += 1
				_log(f"Output row failed: {e}", log_file)
	return {"created": created, "updated": updated, "failed": failed}


