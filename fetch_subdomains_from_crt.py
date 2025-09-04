import requests
import logging

logging.basicConfig(level=logging.INFO)

# function to retrieve a list of subdomains from crt.sh
def get_subdomains_from_crt(domain):
    domains = set()
    url = f"https://crt.sh/?q=%25.{domain}&output=json"
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        logging.error(f"Error fetching data from crt.sh: {resp.status_code}")
        return set()

    for entry in resp.json():
        name = entry.get("name_value", "")
        for sub in name.split("\n"):
            if sub.endswith(domain):
                # clean up wildcard entries
                domains.add(sub.lstrip("*.").strip().lower())

    return domains