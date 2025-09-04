from tranco import Tranco
import requests
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import time

# setup logging
logging.basicConfig(level=logging.INFO)

# configuration
TOPX = 10000  # number of top domains to process from Tranco list
OUTPUT_FILE = "mcp_results.jsonl"  # each line is a JSON object
MAX_WORKERS = 32

def check_mcp_json(domain):
    """
    Checks for the presence of a .well-known/mcp.json file on the given domain and www subdomain.

    Returns:
        List[dict]: Each dict contains:
            - domain (str): The domain used for the request (domain or www.domain).
            - mcp_url (str): The URL where mcp.json was found.
            - mcp (dict): The parsed JSON content of mcp.json
    """
    for host in [domain, f"www.{domain}"]:
        mcp_url = f"https://{host}/.well-known/mcp.json"
        try:
            resp = requests.get(
                mcp_url,
                timeout=2,
                allow_redirects=True,
                headers={"Accept": "application/json, */*;q=0.7", "User-Agent": "mcp-check/0.1"}
            )
        except requests.RequestException as e:
            logging.debug(f"{mcp_url} request error: {e}")
            continue

        if resp.status_code != 200:
            logging.debug(f"No mcp.json at {mcp_url} (status {resp.status_code})")
            continue

        content_type = (resp.headers.get("Content-Type") or "").lower()
        body = resp.content
        body_snippet = body[:512].strip()

        # heuristic check for HTML content in body
        looks_like_html = body_snippet.startswith(b"<html") or body_snippet.startswith(b"<!doctype html")
        if looks_like_html:
            logging.debug(f"{mcp_url} looks like HTML, skipping")
            continue

        # heuristic check for JSON content in body
        looks_like_json = body_snippet.startswith(b"{") or body_snippet.startswith(b"[")
        if "json" not in content_type and not looks_like_json:
            logging.debug(f"{mcp_url} content-type is not JSON ({content_type}), skipping")
            continue

        try:
            mcp_data = resp.json()
        except (ValueError, requests.exceptions.JSONDecodeError):
            logging.debug(f"Response from {mcp_url} is not valid JSON")
            continue

        # immediately return upon finding the first valid mcp.json
        logging.info(f"Found valid mcp.json at {mcp_url}")
        return {
            "domain": domain,
            "mcp_url": mcp_url,
            "mcp": mcp_data
        }

    # If no valid mcp.json found on either host, return None
    return None

def main():
    # get domains from Tranco list
    # reference: https://tranco-list.eu/
    t = Tranco(cache=True, cache_dir='.tranco')
    latest_list = t.list()
    domains = latest_list.top(TOPX)
    logging.info(f"Loaded {len(domains)} domains from Tranco list.")
    start_time = time.time()
    processed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor, open(OUTPUT_FILE, "w") as out:
        future_to_domain = {executor.submit(check_mcp_json, domain): domain for domain in domains}
        for future in as_completed(future_to_domain):
            result = future.result()
            processed += 1
            if result:
                out.write(json.dumps(result, ensure_ascii=False) + "\n")
            if processed % 10 == 0:
                elapsed = time.time() - start_time
                logging.info(f"Processed {processed} domains in {elapsed:.2f} seconds ({processed/elapsed:.2f} domains/sec)")

    elapsed = time.time() - start_time
    logging.info(f"Results written to {OUTPUT_FILE}")
    logging.info(f"Processed {processed} domains in {elapsed:.2f} seconds ({processed/elapsed:.2f} domains/sec)")

if __name__ == "__main__":
    main()