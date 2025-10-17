import os
import json
import requests
from typing import List, Dict


def push_csv_to_sheets(webapp_url: str, api_key: str, folder_path: str) -> Dict:
	files_payload = []
	for entry in sorted(os.listdir(folder_path)):
		if not entry.lower().endswith('.csv'):
			continue
		abs_path = os.path.join(folder_path, entry)
		if not os.path.isfile(abs_path):
			continue
		with open(abs_path, 'r', encoding='utf-8') as f:
			csv_text = f.read()
		files_payload.append({"filename": entry, "csv": csv_text})
	if not files_payload:
		return {"success": False, "message": "No CSV files found to upload."}
	payload = {"key": api_key, "files": files_payload}
	try:
		resp = requests.post(webapp_url, json=payload, timeout=(10, 60))
		resp.raise_for_status()
		return resp.json()
	except requests.HTTPError as e:
		return {"success": False, "error": f"HTTP {resp.status_code}", "details": str(e), "body": resp.text if 'resp' in locals() else None}
	except Exception as e:
		return {"success": False, "error": str(e)}


def push_csv_files_to_sheets(webapp_url: str, api_key: str, file_paths: List[str]) -> Dict:
	files_payload = []
	for abs_path in sorted(file_paths):
		if not abs_path.lower().endswith('.csv'):
			continue
		if not os.path.isfile(abs_path):
			continue
		entry = os.path.basename(abs_path)
		with open(abs_path, 'r', encoding='utf-8') as f:
			csv_text = f.read()
		files_payload.append({"filename": entry, "csv": csv_text})
	if not files_payload:
		return {"success": False, "message": "No CSV files found to upload."}
	payload = {"key": api_key, "files": files_payload}
	try:
		resp = requests.post(webapp_url, json=payload, timeout=(10, 60))
		resp.raise_for_status()
		return resp.json()
	except requests.HTTPError as e:
		return {"success": False, "error": f"HTTP {resp.status_code}", "details": str(e), "body": resp.text if 'resp' in locals() else None}
	except Exception as e:
		return {"success": False, "error": str(e)}


def pull_csvs_from_sheets(webapp_url: str, api_key: str, tabs: List[str], output_folder: str) -> Dict:
	if not tabs:
		return {"success": False, "message": "No tabs requested."}
	os.makedirs(output_folder, exist_ok=True)
	params = {"key": api_key, "tabs": ",".join(tabs)}
	try:
		resp = requests.get(webapp_url, params=params, timeout=(10, 60))
		resp.raise_for_status()
		data = resp.json()
		if not data.get("success"):
			return data
		written = []
		for item in data.get("results", []):
			if not item.get("success"):
				continue
			name = item.get("name", "Sheet")
			csv_text = item.get("csv", "")
			fname = f"{name}.csv"
			with open(os.path.join(output_folder, fname), 'w', encoding='utf-8', newline='') as f:
				f.write(csv_text)
			written.append(fname)
		return {"success": True, "written": written, "raw": data}
	except requests.HTTPError as e:
		return {"success": False, "error": f"HTTP {resp.status_code}", "details": str(e), "body": resp.text if 'resp' in locals() else None}
	except Exception as e:
		return {"success": False, "error": str(e)}


def pull_csvs_from_sheets_to_files(webapp_url: str, api_key: str, tab_to_file: Dict[str, str]) -> Dict:
	if not tab_to_file:
		return {"success": False, "message": "No tabs requested."}
	params = {"key": api_key, "tabs": ",".join(sorted(tab_to_file.keys()))}
	try:
		resp = requests.get(webapp_url, params=params, timeout=(10, 60))
		resp.raise_for_status()
		data = resp.json()
		if not data.get("success"):
			return data
		written = []
		for item in data.get("results", []):
			name = item.get("name")
			if not item.get("success") or name not in tab_to_file:
				continue
			csv_text = item.get("csv", "")
			target = tab_to_file[name]
			os.makedirs(os.path.dirname(target), exist_ok=True)
			with open(target, 'w', encoding='utf-8', newline='') as f:
				f.write(csv_text)
			written.append(target)
		return {"success": True, "written": written, "raw": data}
	except requests.HTTPError as e:
		return {"success": False, "error": f"HTTP {resp.status_code}", "details": str(e), "body": resp.text if 'resp' in locals() else None}
	except Exception as e:
		return {"success": False, "error": str(e)}


if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description="Bridge CSVs to Google Sheets Apps Script web app")
	parser.add_argument('--url', required=True, help='Apps Script web app URL')
	parser.add_argument('--key', required=True, help='API key')
	sub = parser.add_subparsers(dest='cmd')
	pushp = sub.add_parser('push')
	pushp.add_argument('--folder', required=True, help='Folder containing CSVs to push')
	pullp = sub.add_parser('pull')
	pullp.add_argument('--tabs', required=True, help='Comma-separated tab names to pull')
	pullp.add_argument('--out', required=True, help='Output folder for CSVs')
	args = parser.parse_args()
	if args.cmd == 'push':
		res = push_csv_to_sheets(args.url, args.key, args.folder)
		print(json.dumps(res, indent=2))
	elif args.cmd == 'pull':
		res = pull_csvs_from_sheets(args.url, args.key, [t.strip() for t in args.tabs.split(',') if t.strip()], args.out)
		print(json.dumps(res, indent=2))
	else:
		parser.print_help()


