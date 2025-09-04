import requests
import json
import logging
import sys
logging.basicConfig(level=logging.INFO)
#logging.basicConfig(level=logging.DEBUG)



# function to scan for .well-known/mcp.json
def fetch_mcp_json(host):
    mcp_url = f"https://{host}/.well-known/mcp.json"

    try:
        http_response = requests.get(
            mcp_url, 
            timeout=5, 
            allow_redirects=True,
            headers={"Accept": "application/json, */*;q=0.7", "User-Agent": "mcp-check/0.1"},
        )
    
    except requests.RequestException as e:
        logging.debug(f"{mcp_url} request error: {e}")
        return None

    if http_response.status_code != 200:
        logging.debug(f"No mcp.json (status {http_response.status_code})")
        return None

    return http_response

# function to validate and parse mcp.json
def validate_and_parse_mcp_json(http_response):

    # quick checks to avoid HTML masquerading as JSON
    content_type = (http_response.headers.get("Content-Type") or "").lower()
    content = http_response.content

    # heuristic check for HTML content in body
    body_snippet = content[:512].lstrip().lower()
    looks_like_html = body_snippet.startswith(b"<html") or body_snippet.startswith(b"<!doctype html")

    if looks_like_html:
        logging.debug(f"{http_response.url} looks like HTML, skipping")
        return None

    # heuristic check for JSON content in body
    looks_like_json = body_snippet.startswith(b"{") or body_snippet.startswith(b"[")
    if "json" not in content_type and not looks_like_json:
        logging.debug(f"{http_response.url} content-type is not JSON ({content_type}), skipping")
        return None

    # final proof attempt to parse JSON
    try:
        mcp_content = http_response.json()
    except ValueError:
        logging.debug("Response is not valid JSON")
        return None

    return mcp_content

#
# main()
#

mydomain = "notion.com"  # replace with your target domain
mcp_response = None

# only check apex domain and www. host for mcp.json
mcp_response = fetch_mcp_json(mydomain)
if not mcp_response:
    mcp_response = fetch_mcp_json("www." + mydomain)

if not mcp_response:
    logging.info(f"No mcp.json found at {mydomain} or www.{mydomain}")
    sys.exit(0)

mcp_data = validate_and_parse_mcp_json(mcp_response)
if mcp_data:
    logging.info(f"Found mcp.json at {mcp_response.url}")
    logging.debug(json.dumps(mcp_data, indent=2))
else:
    logging.info(f"No valid mcp.json found at {mcp_response.url}")
    sys.exit(0)