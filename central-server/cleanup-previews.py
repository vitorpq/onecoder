#!/usr/bin/env python3
"""Garbage collection de ambientes de preview expirados no Dokploy."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


PROTECTED_BRANCHES = {"main", "master", "prod", "production"}


def dokploy_request(
    base_url: str, api_key: str, method: str, path: str, payload: Optional[Dict[str, Any]] = None
) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"accept": "application/json", "x-api-key": api_key}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(normalized)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def is_preview_app(app: Dict[str, Any], preview_domain: str) -> bool:
    branch = str(app.get("branch") or "").strip().lower()
    if branch in PROTECTED_BRANCHES:
        return False

    name = str(app.get("name") or app.get("appName") or "").strip().lower()
    if name.startswith("preview-"):
        return True

    domains = app.get("domains") or []
    if isinstance(domains, list):
        for dom in domains:
            host = str(dom.get("host") or "").strip().lower() if isinstance(dom, dict) else ""
            if host.endswith(f".{preview_domain}"):
                return True
    return False


def find_expired_previews(
    projects: List[Dict[str, Any]], ttl_days: int, preview_domain: str, now: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    current_time = now or datetime.now(timezone.utc)
    cutoff = current_time - timedelta(days=ttl_days)
    expired: List[Dict[str, Any]] = []

    for project in projects:
        environments = project.get("environments") or []
        for env in environments:
            apps = env.get("applications") or []
            for app in apps:
                if not isinstance(app, dict) or not is_preview_app(app, preview_domain):
                    continue
                ts = parse_iso_datetime(app.get("updatedAt") or app.get("createdAt"))
                if ts is not None and ts < cutoff:
                    expired.append(
                        {
                            "applicationId": app.get("applicationId"),
                            "name": app.get("name") or app.get("appName"),
                            "branch": app.get("branch"),
                            "updatedAt": ts.isoformat(),
                        }
                    )
    return expired


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove ambientes de preview expirados no Dokploy.")
    parser.add_argument("--dry-run", action="store_true", help="Apenas lista os previews que seriam removidos.")
    parser.add_argument(
        "--ttl-days",
        type=int,
        default=int(os.environ.get("PREVIEW_TTL_DAYS", "7")),
        help="TTL em dias para considerar um preview expirado (padrao: 7).",
    )
    args = parser.parse_args()

    base_url = os.environ.get("DOKPLOY_URL") or os.environ.get("ONECODER_DOKPLOY_URL", "")
    api_key = os.environ.get("DOKPLOY_API_KEY") or os.environ.get("ONECODER_DOKPLOY_KEY", "")
    preview_domain = os.environ.get("PREVIEW_DOMAIN", "teste.vitor.one").strip().lower()

    if not base_url or not api_key:
        print("Erro: defina DOKPLOY_URL e DOKPLOY_API_KEY.", file=sys.stderr)
        return 1

    try:
        projects = dokploy_request(base_url, api_key, "GET", "/api/project.all")
    except urllib.error.URLError as exc:
        print(f"Erro ao consultar Dokploy: {exc}", file=sys.stderr)
        return 1

    if not isinstance(projects, list):
        print("Resposta inesperada de /api/project.all.", file=sys.stderr)
        return 1

    expired = find_expired_previews(projects, args.ttl_days, preview_domain)
    if not expired:
        print(f"Nenhum preview expirado encontrado (TTL: {args.ttl_days} dias).")
        return 0

    for item in expired:
        if args.dry_run:
            print(f"[DRY-RUN] Removeria preview: {item['name']} ({item['applicationId']}) - branch={item['branch']} updatedAt={item['updatedAt']}")
        else:
            dokploy_request(base_url, api_key, "POST", "/api/application.delete", {"applicationId": item["applicationId"]})
            print(f"[REMOVIDO] Preview: {item['name']} ({item['applicationId']})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
