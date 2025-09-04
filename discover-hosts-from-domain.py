import requests
import json


domain = "notion.com"
url = f"https://crt.sh/?q=%25.{domain}&output=json"

resp = requests.get(url, timeout=10)
if resp.status_code != 200:
    print(f"Error fetching data from crt.sh: {resp.status_code}")
    exit(1)

# parse JSON response from crt.sh
hosts = set()
for entry in resp.json():
    name = entry.get("name_value", "")
    for sub in name.split("\n"):
        if sub.endswith(domain):
            # clean up wildcard entries
            hosts.add(sub.lstrip("*.").strip().lower())

print(f"Total unique subdomains found: {len(hosts)}")
print(f"Listed subdomains: {sorted(hosts)}")

# scan for .well-known/mcp.json
for host in sorted(hosts):
    mcp_url = f"https://{host}/.well-known/mcp.json"
    
    #print("\n" + "*" * 50 + "\n")
    #print(f"* Checking {mcp_url} ...")
    
    try:
        mcp_resp = requests.get(
            mcp_url, 
            timeout=5, 
            allow_redirects=True,
            headers={"Accept": "application/json, */*;q=0.7", "User-Agent": "mcp-check/0.1"},
        )
    except requests.RequestException as e:
        print(f"{mcp_url} request error: {e}")
        continue

    if mcp_resp.status_code != 200:
        print(f"No mcp.json (status {mcp_resp.status_code})")
        continue

    # quick checks to avoid HTML masquerading as JSON
    content_type = (mcp_resp.headers.get("Content-Type") or "").lower()
    body = mcp_resp.content
    
    # heuristic check for HTML content in body
    body_snippet = body[:512].lstrip().lower()
    looks_like_html = body_snippet.startswith(b"<html") or body_snippet.startswith(b"<!doctype html")

    if looks_like_html:
        print(f"{mcp_url} looks like HTML, skipping")
        continue

    # heuristic check for JSON content in body
    looks_like_json = body_snippet.startswith(b"{") or body_snippet.startswith(b"[")
    if "json" not in content_type and not looks_like_json:
        print(f"{mcp_url} content-type is not JSON ({content_type}), skipping")
        continue

    # final proof attempt to parse JSON
    try:
        mcp_data = mcp_resp.json()
    except ValueError:
        print("Response is not valid JSON")
        continue

    # finally found mcp.json
    print(f"Found mcp.json at {mcp_url}")
    print(f"MCP endpoint: {mcp_data.get("endpoint")}")

    
    #print(json.dumps(data, indent=2, ensure_ascii=False))