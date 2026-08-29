"""Convert a Bilibili JSON cookie export to yt-dlp's Netscape format."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable


def _as_cookie_list(payload: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Return cookie records and optional exported domain metadata."""
    domains: list[str] = []
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        info = payload.get("cookie_info")
        if isinstance(info, dict):
            records = info.get("cookies") or []
            if isinstance(info.get("domains"), list):
                domains = [str(item) for item in info["domains"]]
        else:
            records = payload.get("cookies") or payload.get("data") or []
    else:
        records = []

    if not isinstance(records, list):
        records = []
    return [item for item in records if isinstance(item, dict)], domains


def _number(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _domain(record: dict[str, Any], domains: list[str]) -> str:
    value = str(record.get("domain") or "").strip()
    if value:
        return value
    # This export stores a list of supported domains separately from records.
    # Authentication cookies are intentionally scoped to Bilibili only.
    if domains and all(domain.endswith("bilibili.com") for domain in domains):
        return domains[0]
    return ".bilibili.com"


def _netscape_lines(records: Iterable[dict[str, Any]], domains: list[str]) -> list[str]:
    lines = ["# Netscape HTTP Cookie File", "# Generated from Bilibili cookies.json; values are not logged."]
    written = 0
    for record in records:
        name = str(record.get("name") or "").strip()
        value = str(record.get("value") or "")
        domain = _domain(record, domains)
        if not name or not value or not domain.endswith("bilibili.com"):
            continue
        if any(char in value for char in "\r\n\t"):
            raise ValueError("cookie value contains an unsupported control character")
        include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
        secure = "TRUE" if record.get("secure") in (True, 1, "1", "true", "TRUE") else "FALSE"
        expires = _number(
            record.get("expirationDate", record.get("expires", record.get("expiration", 0)))
        )
        path = str(record.get("path") or "/")
        lines.append("\t".join((domain, include_subdomains, path, secure, str(expires), name, value)))
        written += 1
    if not written:
        raise ValueError("no usable Bilibili cookies found")
    return lines


def convert(content: str) -> str:
    stripped = content.lstrip("\ufeff \t\r\n")
    if not stripped:
        raise ValueError("cookie content is empty")
    if not stripped.startswith(("{", "[")):
        if "# Netscape HTTP Cookie File" in stripped or "\t" in stripped:
            return content.rstrip("\r\n") + "\n"
        raise ValueError("cookie content is neither Netscape nor JSON format")
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError("cookie JSON is invalid") from exc
    records, domains = _as_cookie_list(payload)
    return "\n".join(_netscape_lines(records, domains)) + "\n"


def main() -> int:
    destination = Path(sys.argv[1] if len(sys.argv) > 1 else "cookies.txt")
    content = os.environ.get("BILIBILI_COOKIE_CONTENT", "")
    try:
        destination.write_text(convert(content), encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"cookie preparation failed: {exc}", file=sys.stderr)
        return 1
    print("repository cookie prepared (format validated; values hidden)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
