"""
Common utilities and types used across the project.
"""
from __future__ import annotations
import hashlib, json, pathlib, time
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, Optional

DATA_DIR = pathlib.Path("data")
RUNS_DIR = DATA_DIR / "runs"
SUMMARIES_DIR = DATA_DIR / "summaries"
REPORTS_DIR = pathlib.Path("reports")

DEFAULT_TIMEOUT = 10.0  # seconds
USER_AGENT = "mcp-server-trends/0.1 (+https://github.com/phunold/MCP-server-trends)"

def ensure_dir(p: pathlib.Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def now_iso() -> str:
    # UTC ISO8601 zulu
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def write_jsonl(path: pathlib.Path, rows: Iterable[Dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def read_jsonl(path: pathlib.Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)

@dataclass
class ScanResult:
    run_ts: str
    seed_source: str           # "tranco" | "registry"
    domain: str
    url: str
    status: int
    has_manifest: bool
    bytes: Optional[int] = None
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    sha256: Optional[str] = None
    auth: Optional[str] = None                 # "none" | "api_key" | "oauth2" | "unknown"
    tls_grade: Optional[str] = None            # placeholder grade
    exposure_flags: Optional[list[str]] = None
    manifest_sample: Optional[Dict[str, Any]] = None
    notes: Optional[list[str]] = None

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)