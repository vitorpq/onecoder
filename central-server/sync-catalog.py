#!/usr/bin/env python3
"""Sincroniza central-server/company-catalog.json com projetos e servidores do Dokploy."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_CATALOG = Path(__file__).resolve().parent / "company-catalog.json"


def dokploy_get(base_url: str, api_key: str, path: str) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    req = urllib.request.Request(
        url,
        headers={"accept": "application/json", "x-api-key": api_key},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else []


def merge_catalog(
    existing: Dict[str, Any], projects: List[Dict[str, Any]], servers: List[Dict[str, Any]]
) -> Dict[str, Any]:
    merged = dict(existing)
    existing_clients = {
        c.get("dokploy_project_id") or c.get("name"): c
        for c in (existing.get("clients") or [])
        if isinstance(c, dict)
    }

    server_map = {
        s.get("serverId"): {
            "serverId": s.get("serverId"),
            "name": s.get("name"),
            "ipAddress": s.get("ipAddress"),
        }
        for s in servers
        if isinstance(s, dict) and s.get("serverId")
    }
    if server_map:
        merged["servers"] = list(server_map.values())

    updated_clients: List[Dict[str, Any]] = []
    seen_keys = set()

    for proj in projects:
        if not isinstance(proj, dict):
            continue
        proj_id = proj.get("projectId")
        proj_name = proj.get("name")
        key = proj_id or proj_name
        if not key:
            continue
        seen_keys.add(key)

        base_client = dict(existing_clients.get(key, {}))
        base_client["dokploy_project_id"] = proj_id
        base_client.setdefault("name", proj_name)
        base_client.setdefault("friendly_name", proj_name)

        apps_out: List[Dict[str, Any]] = []
        for env in proj.get("environments") or []:
            for app in env.get("applications") or []:
                if not isinstance(app, dict):
                    continue
                domains = [
                    d.get("host")
                    for d in (app.get("domains") or [])
                    if isinstance(d, dict) and d.get("host")
                ]
                apps_out.append(
                    {
                        "dokploy_application_id": app.get("applicationId"),
                        "name": app.get("name") or app.get("appName"),
                        "branch": app.get("branch"),
                        "serverId": app.get("serverId"),
                        "domains": domains,
                    }
                )
        base_client["applications"] = apps_out
        updated_clients.append(base_client)

    for key, client in existing_clients.items():
        if key not in seen_keys:
            updated_clients.append(client)

    merged["clients"] = updated_clients
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description="Sincroniza company-catalog.json com o Dokploy.")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG), help="Caminho para company-catalog.json.")
    parser.add_argument("--dry-run", action="store_true", help="Exibe o JSON resultante sem gravar em disco.")
    parser.add_argument("--fixture-projects", help="Arquivo JSON simulado de /api/project.all.")
    parser.add_argument("--fixture-servers", help="Arquivo JSON simulado de /api/server.all.")
    args = parser.parse_args()

    catalog_path = Path(args.catalog)
    existing: Dict[str, Any] = {}
    if catalog_path.exists():
        existing = json.loads(catalog_path.read_text(encoding="utf-8"))

    if args.fixture_projects:
        projects = json.loads(Path(args.fixture_projects).read_text(encoding="utf-8"))
        servers = (
            json.loads(Path(args.fixture_servers).read_text(encoding="utf-8"))
            if args.fixture_servers
            else []
        )
    else:
        base_url = os.environ.get("DOKPLOY_URL") or os.environ.get("ONECODER_DOKPLOY_URL", "")
        api_key = os.environ.get("DOKPLOY_API_KEY") or os.environ.get("ONECODER_DOKPLOY_KEY", "")
        if not base_url or not api_key:
            print("Erro: defina DOKPLOY_URL e DOKPLOY_API_KEY (ou use --fixture-projects).", file=sys.stderr)
            return 1
        try:
            projects = dokploy_get(base_url, api_key, "/api/project.all")
            servers = dokploy_get(base_url, api_key, "/api/server.all")
        except urllib.error.URLError as exc:
            print(f"Erro ao consultar Dokploy: {exc}", file=sys.stderr)
            return 1

    merged = merge_catalog(
        existing,
        projects if isinstance(projects, list) else [],
        servers if isinstance(servers, list) else [],
    )
    output = json.dumps(merged, indent=2, ensure_ascii=False) + "\n"

    if args.dry_run:
        print(output, end="")
    else:
        catalog_path.write_text(output, encoding="utf-8")
        print(f"Catalogo sincronizado em {catalog_path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
