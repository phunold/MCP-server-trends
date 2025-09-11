.PHONY: demo-data run-app remote-scan

demo-data:
	uv run jobs/init_demo_data.py --out-dir data/runs/`date -u +%F`

run-app:
	uv run streamlit run app/Home.py

remote-scan:
	uv run jobs/scan_remotes.py --run-dir data/runs/`date -u +%F` --out data/runs/`date -u +%F`/remote_scan.jsonl
