#!/usr/bin/env python3
"""Control Plane API proxy for onecoder.

Authenticates developers via LiteLLM Virtual Keys (/key/info), enforces
server-side RBAC (dev vs admin), injects DOKPLOY_API_KEY, and records
centralized audit logs.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


ADMIN_ONLY_ACTIONS = {"deploy_producao_main"}


def get_config() -> Dict[str, str]:
    return {
        "port": os.environ.get("CONTROL_API_PORT", "8080"),
        "litellm_url": os.environ.get("LITELLM_INTERNAL_URL", "http://litellm:4000").rstrip("/"),
        "litellm_master_key": os.environ.get("LITELLM_MASTER_KEY", ""),
        "dokploy_url": os.environ.get("DOKPLOY_URL", "").rstrip("/"),
        "dokploy_api_key": os.environ.get("DOKPLOY_API_KEY", ""),
        "audit_log_path": os.environ.get("AUDIT_LOG_PATH", "/data/audit.log"),
    }


def write_audit_log(
    audit_path: str,
    developer: str,
    role: str,
    action: str,
    method: str,
    path: str,
    status: int,
    allowed: bool,
    detail: str = "",
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "developer": developer,
        "role": role,
        "action": action,
        "method": method,
        "path": path,
        "status": status,
        "allowed": allowed,
    }
    if detail:
        entry["detail"] = detail
    target = Path(audit_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def resolve_virtual_key(token: str, cfg: Dict[str, str]) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    """Validate Virtual Key against LiteLLM /key/info and return (identity, error)."""
    if not token:
        return None, "Missing Bearer token"

    litellm_url = cfg["litellm_url"]
    master_key = cfg["litellm_master_key"]
    if master_key:
        url = f"{litellm_url}/key/info?key={urllib.parse.quote(token, safe='')}"
        auth_header = f"Bearer {master_key}"
    else:
        url = f"{litellm_url}/key/info"
        auth_header = f"Bearer {token}"

    req = urllib.request.Request(
        url,
        headers={"Authorization": auth_header, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return None, f"LiteLLM auth failed (HTTP {exc.code})"
    except Exception as exc:
        return None, f"LiteLLM unreachable: {exc}"

    info = data.get("info") if isinstance(data.get("info"), dict) else data
    metadata = info.get("metadata") if isinstance(info, dict) else {}
    if not isinstance(metadata, dict):
        metadata = {}

    role = str(metadata.get("role", "dev")).strip().lower() or "dev"
    if role not in ("dev", "admin"):
        role = "dev"
    developer = str(metadata.get("developer") or info.get("user_id") or "unknown").strip()
    return {"developer": developer, "role": role}, None


def is_action_allowed(role: str, action: str, method: str, path: str) -> Tuple[bool, str]:
    """Enforce server-side RBAC: dev cannot trigger production deploys."""
    if role == "admin":
        return True, ""
    if action in ADMIN_ONLY_ACTIONS:
        return False, f"Action '{action}' requires role 'admin' (current role: '{role}')"
    if method == "POST" and path.startswith("/api/compose.deploy"):
        return False, f"Endpoint '{path}' requires role 'admin' (current role: '{role}')"
    return True, ""


class ControlAPIHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"[control-api] {self.address_string()} - {format % args}\n")

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_proxy(self, method: str) -> None:
        if self.path == "/health" and method == "GET":
            self._send_json(200, {"status": "ok"})
            return

        if not self.path.startswith("/api/"):
            self._send_json(404, {"error": "Not found"})
            return

        cfg = get_config()
        auth_header = self.headers.get("Authorization", "")
        token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""

        identity, err = resolve_virtual_key(token, cfg)
        if not identity:
            write_audit_log(
                cfg["audit_log_path"],
                developer="anonymous",
                role="none",
                action=self.headers.get("X-Onecoder-Action", "unknown"),
                method=method,
                path=self.path,
                status=401,
                allowed=False,
                detail=err or "Unauthorized",
            )
            self._send_json(401, {"error": err or "Unauthorized"})
            return

        developer = identity["developer"]
        role = identity["role"]
        action = self.headers.get("X-Onecoder-Action", f"{method} {self.path.split('?')[0]}")

        allowed, reason = is_action_allowed(role, action, method, self.path)
        if not allowed:
            write_audit_log(
                cfg["audit_log_path"],
                developer=developer,
                role=role,
                action=action,
                method=method,
                path=self.path,
                status=403,
                allowed=False,
                detail=reason,
            )
            self._send_json(403, {"error": reason})
            return

        if not cfg["dokploy_url"] or not cfg["dokploy_api_key"]:
            self._send_json(500, {"error": "DOKPLOY_URL or DOKPLOY_API_KEY not configured on Control Plane"})
            return

        content_length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(content_length) if content_length > 0 else None

        target_url = f"{cfg['dokploy_url']}{self.path}"
        headers = {
            "x-api-key": cfg["dokploy_api_key"],
            "Accept": "application/json",
        }
        if body is not None:
            headers["Content-Type"] = self.headers.get("Content-Type", "application/json")

        req = urllib.request.Request(target_url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read()
                write_audit_log(
                    cfg["audit_log_path"],
                    developer=developer,
                    role=role,
                    action=action,
                    method=method,
                    path=self.path,
                    status=resp.status,
                    allowed=True,
                )
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(resp_body)))
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as exc:
            err_body = exc.read()
            write_audit_log(
                cfg["audit_log_path"],
                developer=developer,
                role=role,
                action=action,
                method=method,
                path=self.path,
                status=exc.code,
                allowed=True,
                detail=f"Dokploy HTTP {exc.code}",
            )
            self.send_response(exc.code)
            self.send_header("Content-Type", exc.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(err_body)))
            self.end_headers()
            self.wfile.write(err_body)
        except Exception as exc:
            write_audit_log(
                cfg["audit_log_path"],
                developer=developer,
                role=role,
                action=action,
                method=method,
                path=self.path,
                status=502,
                allowed=True,
                detail=str(exc),
            )
            self._send_json(502, {"error": f"Dokploy upstream error: {exc}"})

    def do_GET(self) -> None:
        self._handle_proxy("GET")

    def do_POST(self) -> None:
        self._handle_proxy("POST")


def main() -> int:
    port = int(get_config()["port"])
    server = ThreadingHTTPServer(("0.0.0.0", port), ControlAPIHandler)
    sys.stderr.write(f"[control-api] Listening on 0.0.0.0:{port}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
