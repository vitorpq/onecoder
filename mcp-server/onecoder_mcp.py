#!/usr/bin/env python3
"""Servidor MCP da empresa (onecoder-mcp) via stdio JSON-RPC 2.0.

Conecta o VS Code e o OpenCode ao catalogo central de sistemas da empresa e
a API do Dokploy para diagnostico sem SSH, criacao de ambientes de teste por
branch e deploy controlado entre 'dev' e 'admin'.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "onecoder-empresa", "version": "0.2.0"}
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG_PATH = REPO_ROOT / "central-server" / "company-catalog.json"

SERVER_INSTRUCTIONS = (
    "Voce e o Assistente Operacional Central da empresa. "
    "Use 'consultar_catalogo_empresa' para descobrir clientes, sistemas, VPSs e IDs no Dokploy. "
    "Use 'diagnosticar_sistema_cliente' para investigar erros 500 e falhas de deploy sem pedir SSH. "
    "Devs podem criar livremente ambientes de teste por branch com 'subir_branch_dominio_teste'. "
    "Deploy direto em producao (main) via 'deploy_producao_main' e restrito ao perfil 'admin'."
)


def env_config() -> Dict[str, str]:
    """Lê variaveis de configuracao ativas no ambiente."""
    return {
        "control_url": os.environ.get(
            "ONECODER_CONTROL_URL", os.environ.get("ONECODER_DOKPLOY_URL", "")
        ).rstrip("/"),
        "ai_key": os.environ.get("ONECODER_AI_KEY", ""),
        "dokploy_key": os.environ.get("ONECODER_DOKPLOY_KEY", ""),
        "role": os.environ.get("ONECODER_ROLE", "dev").strip().lower() or "dev",
        "preview_domain": os.environ.get("ONECODER_PREVIEW_DOMAIN", "teste.vitor.one").strip(),
        "catalog_path": os.environ.get("ONECODER_CATALOG_PATH", str(DEFAULT_CATALOG_PATH)),
    }


def dokploy_request(
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    action: str = "",
) -> Any:
    """Executa uma requisicao HTTP contra a Control API (ou Dokploy legado)."""
    cfg = env_config()
    if not cfg["control_url"] or (not cfg["ai_key"] and not cfg["dokploy_key"]):
        raise RuntimeError(
            "Control Plane nao configurado (ONECODER_CONTROL_URL / ONECODER_AI_KEY). "
            "Execute 'onecoder login' com as credenciais da empresa."
        )

    url = f"{cfg['control_url']}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "accept": "application/json",
    }
    if cfg["ai_key"]:
        headers["Authorization"] = f"Bearer {cfg['ai_key']}"
    else:
        headers["x-api-key"] = cfg["dokploy_key"]
    if action:
        headers["X-Onecoder-Action"] = action
    if data is not None:
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Erro HTTP {exc.code} em {path}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Falha de conexao com Dokploy ({url}): {exc.reason}") from exc


def sanitize_slug(value: str) -> str:
    """Normaliza nome de branch/app para uso seguro em subdominio DNS."""
    slug = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:40] or "preview"


def append_audit_log(action: str, details: Dict[str, Any]) -> None:
    """Registra acoes sensiveis em ~/.config/onecoder/audit.log."""
    config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "onecoder"
    config_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": env_config()["role"],
        "action": action,
        "details": details,
    }
    with (config_dir / "audit.log").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


_CATALOG_CACHE: Dict[str, Any] = {"path": "", "expires_at": 0.0, "data": None}
_CATALOG_CACHE_TTL_SECONDS = 60.0


def _read_catalog_cached(catalog_file: Path) -> Any:
    import time

    now = time.monotonic()
    key = str(catalog_file)
    if (
        _CATALOG_CACHE["path"] == key
        and _CATALOG_CACHE["data"] is not None
        and now < _CATALOG_CACHE["expires_at"]
    ):
        return _CATALOG_CACHE["data"]

    data = json.loads(catalog_file.read_text(encoding="utf-8"))
    _CATALOG_CACHE["path"] = key
    _CATALOG_CACHE["data"] = data
    _CATALOG_CACHE["expires_at"] = now + _CATALOG_CACHE_TTL_SECONDS
    return data


def tool_consultar_catalogo_empresa(_args: Dict[str, Any]) -> Dict[str, Any]:
    """Retorna o catalogo estatico da empresa combinado com projetos e VPSs do Dokploy."""
    cfg = env_config()
    result: Dict[str, Any] = {
        "perfil_atual": cfg["role"],
        "preview_domain": cfg["preview_domain"],
        "catalogo_empresa": None,
        "dokploy_projetos": None,
        "dokploy_servidores": None,
    }

    catalog_file = Path(cfg["catalog_path"])
    if catalog_file.exists():
        result["catalogo_empresa"] = _read_catalog_cached(catalog_file)
    else:
        result["catalogo_empresa"] = {"aviso": f"Arquivo {catalog_file} nao encontrado."}

    if cfg["control_url"] and (cfg["ai_key"] or cfg["dokploy_key"]):
        try:
            result["dokploy_projetos"] = dokploy_request("GET", "/api/project.all")
        except Exception as exc:
            result["dokploy_projetos"] = {"erro": str(exc)}
        try:
            result["dokploy_servidores"] = dokploy_request("GET", "/api/server.all")
        except Exception as exc:
            result["dokploy_servidores"] = {"erro": str(exc)}
    else:
        result["dokploy_aviso"] = "Credenciais do Dokploy nao definidas; exibindo apenas catalogo local."

    return result


def tool_diagnosticar_sistema_cliente(args: Dict[str, Any]) -> Dict[str, Any]:
    """Busca configuracao, historico de deploys e previews de uma aplicacao no Dokploy."""
    app_id = (args.get("applicationId") or "").strip()
    if not app_id:
        raise ValueError("Parametro obrigatorio 'applicationId' nao informado.")

    query = urllib.parse.urlencode({"applicationId": app_id})
    app_info = dokploy_request("GET", f"/api/application.one?{query}")
    deployments = dokploy_request("GET", f"/api/deployment.all?{query}")

    try:
        previews = dokploy_request("GET", f"/api/previewDeployment.all?{query}")
    except Exception as exc:
        previews = {"aviso": f"Nao foi possivel consultar previewDeployment.all: {exc}"}

    recent_deployments = deployments[:10] if isinstance(deployments, list) else deployments
    return {
        "application": app_info,
        "ultimos_deploys": recent_deployments,
        "preview_deployments": previews,
    }


def redact_sensitive_logs(text: str) -> str:
    """Mascara credenciais comuns (PASSWORD, SECRET, TOKEN, Bearer) antes de enviar ao modelo."""
    redacted = re.sub(
        r"(?i)\b(PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY)\s*([=:])\s*\S+",
        r"\1\2***REDACTED***",
        text,
    )
    redacted = re.sub(r"(?i)(Bearer\s+)[A-Za-z0-9._\-]+", r"\1***REDACTED***", redacted)
    return redacted


def tool_ler_logs_container_tempo_real(args: Dict[str, Any]) -> Dict[str, Any]:
    """Le os logs de runtime (stdout/stderr) de um container via Dokploy/Control API."""
    app_id = (args.get("applicationId") or "").strip()
    if not app_id:
        raise ValueError("Parametro obrigatorio 'applicationId' nao informado.")

    tail_lines = int(args.get("tailLines") or 100)
    tail_lines = max(1, min(500, tail_lines))
    search = (args.get("search") or "").strip()

    query = urllib.parse.urlencode({"applicationId": app_id, "tail": tail_lines})
    raw_resp = dokploy_request("GET", f"/api/application.readLogs?{query}")

    if isinstance(raw_resp, dict):
        logs_text = str(raw_resp.get("logs") or raw_resp.get("data") or raw_resp)
    elif isinstance(raw_resp, list):
        logs_text = "\n".join(str(line) for line in raw_resp)
    else:
        logs_text = str(raw_resp)

    lines = logs_text.splitlines()
    if search:
        search_lower = search.lower()
        lines = [line for line in lines if search_lower in line.lower()]
    lines = lines[-tail_lines:]

    return {
        "applicationId": app_id,
        "tailLines": tail_lines,
        "search": search or None,
        "totalLines": len(lines),
        "logs": redact_sensitive_logs("\n".join(lines)),
    }


def tool_subir_branch_dominio_teste(args: Dict[str, Any]) -> Dict[str, Any]:
    """Cria uma aplicacao de preview para uma branch e publica em dominio de teste."""
    env_id = (args.get("environmentId") or "").strip()
    app_name = (args.get("appName") or "").strip()
    branch = (args.get("branch") or "").strip()
    server_id = (args.get("serverId") or "").strip()
    port = int(args.get("port") or 3000)

    if not env_id or not app_name or not branch:
        raise ValueError("Parametros obrigatorios: 'environmentId', 'appName' e 'branch'.")

    cfg = env_config()
    branch_slug = sanitize_slug(branch)
    app_slug = sanitize_slug(app_name)
    preview_name = f"{app_slug}-{branch_slug}"
    host = f"{branch_slug}-{app_slug}.{cfg['preview_domain']}"

    create_payload: Dict[str, Any] = {
        "name": preview_name,
        "environmentId": env_id,
    }
    if server_id:
        create_payload["serverId"] = server_id

    created = dokploy_request("POST", "/api/application.create", create_payload)
    new_app_id = created.get("applicationId") or created.get("id")
    if not new_app_id:
        raise RuntimeError(f"Dokploy nao retornou applicationId ao criar preview: {created}")

    domain_payload = {
        "host": host,
        "applicationId": new_app_id,
        "port": port,
        "https": True,
        "certificateType": "letsencrypt",
    }
    domain_resp = dokploy_request("POST", "/api/domain.create", domain_payload)
    deploy_resp = dokploy_request("POST", "/api/application.deploy", {"applicationId": new_app_id})

    append_audit_log(
        "subir_branch_dominio_teste",
        {"branch": branch, "host": host, "applicationId": new_app_id},
    )

    preview_url = f"https://{host}"
    smoke_test = run_preview_smoke_test(preview_url)
    github_pr = post_github_pr_comment(branch, preview_url, smoke_test)

    return {
        "status": "ambiente_de_teste_iniciado",
        "branch": branch,
        "url_teste": preview_url,
        "applicationId": new_app_id,
        "domain": domain_resp,
        "deploy": deploy_resp,
        "smoke_test": smoke_test,
        "github_pr": github_pr,
        "observacao": "Valide a branch nesta URL antes de abrir Pull Request para a main.",
    }


def run_preview_smoke_test(url: str, timeout_s: int = 10) -> Dict[str, Any]:
    """Executa um smoke test HTTP GET na URL de preview gerada."""
    import time

    start = time.monotonic()
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            latency_ms = round((time.monotonic() - start) * 1000, 1)
            return {
                "status": "ok" if 200 <= resp.status < 400 else "falha",
                "http_status": resp.status,
                "latency_ms": latency_ms,
            }
    except urllib.error.HTTPError as exc:
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        return {
            "status": "falha",
            "http_status": exc.code,
            "latency_ms": latency_ms,
            "error": str(exc),
        }
    except Exception as exc:
        latency_ms = round((time.monotonic() - start) * 1000, 1)
        return {
            "status": "falha",
            "http_status": None,
            "latency_ms": latency_ms,
            "error": str(exc),
        }


def post_github_pr_comment(
    branch: str, preview_url: str, smoke_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Publica comentario com a URL de preview no PR aberto no GitHub, se configurado."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not token or not repo:
        return {"status": "skipped", "reason": "GITHUB_TOKEN ou GITHUB_REPOSITORY nao configurado."}

    owner = repo.split("/")[0]
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }
    pulls_url = (
        f"https://api.github.com/repos/{repo}/pulls?"
        + urllib.parse.urlencode({"head": f"{owner}:{branch}", "state": "open"})
    )
    try:
        req = urllib.request.Request(pulls_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            pulls = json.loads(resp.read().decode("utf-8"))
        if not isinstance(pulls, list) or not pulls:
            return {"status": "skipped", "reason": f"Nenhum PR aberto para branch '{branch}'."}

        pr_number = pulls[0]["number"]
        body_text = (
            f"### Ambiente de Preview (onecoder)\n"
            f"- **URL:** {preview_url}\n"
            f"- **Smoke Test:** `{smoke_result.get('status')}` "
            f"(HTTP {smoke_result.get('http_status')}, {smoke_result.get('latency_ms')} ms)\n"
        )
        comment_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
        comment_req = urllib.request.Request(
            comment_url,
            data=json.dumps({"body": body_text}).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(comment_req, timeout=10) as cresp:
            cdata = json.loads(cresp.read().decode("utf-8"))
        return {"status": "commented", "pr_number": pr_number, "comment_url": cdata.get("html_url")}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def tool_remover_ambiente_teste(args: Dict[str, Any]) -> Dict[str, Any]:
    """Remove um ambiente de teste (preview) apos o encerramento da validacao."""
    app_id = (args.get("applicationId") or "").strip()
    if not app_id:
        raise ValueError("Parametro obrigatorio 'applicationId' nao informado.")

    resp = dokploy_request("POST", "/api/application.delete", {"applicationId": app_id})
    append_audit_log("remover_ambiente_teste", {"applicationId": app_id})
    return {
        "status": "ambiente_de_teste_removido",
        "applicationId": app_id,
        "dokploy": resp,
    }


def tool_criar_novo_sistema(args: Dict[str, Any]) -> Dict[str, Any]:
    """Cria um novo projeto + aplicacao + dominio inicial de homologacao no Dokploy."""
    project_name = (args.get("projectName") or "").strip()
    description = (args.get("description") or "").strip()
    app_name = (args.get("appName") or "").strip()
    test_subdomain = (args.get("testSubdomain") or "").strip()
    port = int(args.get("port") or 3000)

    if not project_name or not app_name:
        raise ValueError("Parametros obrigatorios: 'projectName' e 'appName'.")

    project = dokploy_request(
        "POST",
        "/api/project.create",
        {"name": project_name, "description": description},
    )

    env_id = project.get("environmentId")
    if not env_id:
        envs = project.get("environments") or []
        if envs and isinstance(envs, list):
            env_id = envs[0].get("environmentId")
    if not env_id and project.get("projectId"):
        # Fallback: busca o projeto recem-criado para obter o environmentId padrao
        all_projects = dokploy_request("GET", "/api/project.all")
        if isinstance(all_projects, list):
            for proj in all_projects:
                if proj.get("projectId") == project.get("projectId"):
                    envs = proj.get("environments") or []
                    if envs:
                        env_id = envs[0].get("environmentId")
                    break

    if not env_id:
        raise RuntimeError(f"Nao foi possivel identificar o environmentId criado: {project}")

    app = dokploy_request(
        "POST",
        "/api/application.create",
        {"name": app_name, "environmentId": env_id},
    )
    app_id = app.get("applicationId") or app.get("id")
    if not app_id:
        raise RuntimeError(f"Dokploy nao retornou applicationId: {app}")

    cfg = env_config()
    sub = sanitize_slug(test_subdomain or f"{project_name}-{app_name}")
    host = f"{sub}.{cfg['preview_domain']}"
    domain = dokploy_request(
        "POST",
        "/api/domain.create",
        {
            "host": host,
            "applicationId": app_id,
            "port": port,
            "https": True,
            "certificateType": "letsencrypt",
        },
    )

    append_audit_log(
        "criar_novo_sistema",
        {"projectName": project_name, "appName": app_name, "applicationId": app_id, "host": host},
    )

    return {
        "status": "sistema_criado",
        "projectId": project.get("projectId"),
        "environmentId": env_id,
        "applicationId": app_id,
        "url_homologacao": f"https://{host}",
        "domain": domain,
    }


def tool_deploy_producao_main(args: Dict[str, Any]) -> Dict[str, Any]:
    """Dispara deploy de producao (restrito ao perfil admin)."""
    cfg = env_config()
    if cfg["role"] != "admin":
        return {
            "bloqueado": True,
            "motivo": (
                f"Acesso negado para o perfil '{cfg['role']}'. "
                "Devs devem validar alteracoes em dominios de teste via 'subir_branch_dominio_teste' "
                "e abrir Pull Request para a branch 'main' (ou solicitar deploy por um usuario 'admin')."
            ),
        }

    service_type = (args.get("serviceType") or "").strip().lower()
    service_id = (args.get("serviceId") or "").strip()
    confirm_main_merge = bool(args.get("confirmMainMerge"))

    if not confirm_main_merge:
        raise ValueError("Defina 'confirmMainMerge': true para confirmar deploy em producao.")
    if service_type not in ("application", "compose") or not service_id:
        raise ValueError("Parametros invalidos: 'serviceType' ('application'|'compose') e 'serviceId' sao obrigatorios.")

    if service_type == "application":
        resp = dokploy_request(
            "POST",
            "/api/application.deploy",
            {"applicationId": service_id},
            action="deploy_producao_main",
        )
    else:
        resp = dokploy_request(
            "POST",
            "/api/compose.deploy",
            {"composeId": service_id},
            action="deploy_producao_main",
        )

    append_audit_log(
        "deploy_producao_main",
        {"serviceType": service_type, "serviceId": service_id},
    )

    return {
        "status": "deploy_producao_iniciado",
        "serviceType": service_type,
        "serviceId": service_id,
        "dokploy_response": resp,
    }


TOOLS: List[Dict[str, Any]] = [
    {
        "name": "consultar_catalogo_empresa",
        "description": (
            "Consulta o catalogo central de clientes, sistemas, VPSs (Tailscale), "
            "regras de engenharia e lista em tempo real os projetos/servidores no Dokploy."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "handler": tool_consultar_catalogo_empresa,
    },
    {
        "name": "diagnosticar_sistema_cliente",
        "description": (
            "Consulta configuracoes, historico de deploys recentes e preview deployments de uma aplicacao "
            "no Dokploy para diagnosticar erros em VPS de clientes sem usar SSH."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "applicationId": {
                    "type": "string",
                    "description": "ID da aplicacao no Dokploy (applicationId).",
                }
            },
            "required": ["applicationId"],
            "additionalProperties": False,
        },
        "handler": tool_diagnosticar_sistema_cliente,
    },
    {
        "name": "ler_logs_container_tempo_real",
        "description": (
            "Le os logs de runtime (stdout/stderr) de um container no Dokploy com mascaramento "
            "automatico de credenciais sensiveis."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "applicationId": {
                    "type": "string",
                    "description": "ID da aplicacao no Dokploy (applicationId).",
                },
                "tailLines": {
                    "type": "integer",
                    "description": "Quantidade de linhas finais a retornar (padrao 100, maximo 500).",
                },
                "search": {
                    "type": "string",
                    "description": "Filtro textual opcional para buscar termos especificos nos logs.",
                },
            },
            "required": ["applicationId"],
            "additionalProperties": False,
        },
        "handler": tool_ler_logs_container_tempo_real,
    },
    {
        "name": "subir_branch_dominio_teste",
        "description": (
            "Cria um ambiente isolado para uma branch e publica automaticamente em um subdominio "
            "de teste (*.teste.vitor.one) com HTTPS para validacao antes do merge na main."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "environmentId": {"type": "string", "description": "ID do environment no Dokploy."},
                "appName": {"type": "string", "description": "Nome base da aplicacao (ex: api-acme)."},
                "branch": {"type": "string", "description": "Nome da branch Git (ex: fix/erro-boleto)."},
                "serverId": {"type": "string", "description": "ID opcional da VPS de homologacao/cliente."},
                "port": {"type": "integer", "description": "Porta interna do container (padrao: 3000)."},
            },
            "required": ["environmentId", "appName", "branch"],
            "additionalProperties": False,
        },
        "handler": tool_subir_branch_dominio_teste,
    },
    {
        "name": "remover_ambiente_teste",
        "description": "Remove um ambiente de teste (preview) no Dokploy apos concluir a validacao da branch.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "applicationId": {
                    "type": "string",
                    "description": "ID da aplicacao de preview no Dokploy (applicationId).",
                }
            },
            "required": ["applicationId"],
            "additionalProperties": False,
        },
        "handler": tool_remover_ambiente_teste,
    },
    {
        "name": "criar_novo_sistema",
        "description": (
            "Cria um novo projeto e aplicacao no Dokploy ja vinculados a um dominio inicial de "
            "homologacao em *.teste.vitor.one."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectName": {"type": "string", "description": "Nome do projeto/cliente no Dokploy."},
                "description": {"type": "string", "description": "Descricao curta do sistema."},
                "appName": {"type": "string", "description": "Nome da aplicacao inicial."},
                "testSubdomain": {"type": "string", "description": "Subdominio opcional de homologacao."},
                "port": {"type": "integer", "description": "Porta interna da aplicacao (padrao: 3000)."},
            },
            "required": ["projectName", "appName"],
            "additionalProperties": False,
        },
        "handler": tool_criar_novo_sistema,
    },
    {
        "name": "deploy_producao_main",
        "description": (
            "Dispara deploy de producao (branch main) no Dokploy. Bloqueado automaticamente para "
            "perfil 'dev'; exige ONECODER_ROLE=admin e confirmMainMerge=true."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "serviceType": {
                    "type": "string",
                    "enum": ["application", "compose"],
                    "description": "Tipo do servico no Dokploy.",
                },
                "serviceId": {"type": "string", "description": "applicationId ou composeId."},
                "confirmMainMerge": {
                    "type": "boolean",
                    "description": "Confirmacao explicita de que o codigo ja foi revisado/merged na main.",
                },
            },
            "required": ["serviceType", "serviceId", "confirmMainMerge"],
            "additionalProperties": False,
        },
        "handler": tool_deploy_producao_main,
    },
]

TOOL_MAP = {t["name"]: t for t in TOOLS}


def handle_message(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Processa uma mensagem JSON-RPC 2.0 e retorna a resposta (ou None para notificacoes)."""
    method = msg.get("method")
    msg_id = msg.get("id")
    params = msg.get("params") or {}

    if method == "notifications/initialized" or msg_id is None:
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
                "instructions": SERVER_INSTRUCTIONS,
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    if method == "tools/list":
        public_tools = [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["inputSchema"],
            }
            for t in TOOLS
        ]
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": public_tools}}

    if method == "tools/call":
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        tool = TOOL_MAP.get(name)
        if not tool:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Ferramenta desconhecida: {name}"},
            }
        try:
            output = tool["handler"](arguments)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(output, indent=2, ensure_ascii=False),
                        }
                    ],
                    "isError": False,
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": f"Erro ao executar '{name}': {exc}"}],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Metodo JSON-RPC nao suportado: {method}"},
    }


def run_self_test() -> int:
    """Valida o handshake initialize, tools/list e a trava de seguranca dev vs admin."""
    init_resp = handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init_resp and init_resp["result"]["serverInfo"]["name"] == "onecoder-empresa"

    list_resp = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools = list_resp["result"]["tools"] if list_resp else []
    names = [t["name"] for t in tools]
    assert len(names) == 7, f"Esperado 7 ferramentas, encontrado {len(names)}: {names}"

    os.environ["ONECODER_ROLE"] = "dev"
    guard_resp = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "deploy_producao_main",
                "arguments": {
                    "serviceType": "application",
                    "serviceId": "app-123",
                    "confirmMainMerge": True,
                },
            },
        }
    )
    payload = json.loads(guard_resp["result"]["content"][0]["text"])
    assert payload.get("bloqueado") is True, "Perfil dev deveria ser bloqueado na producao"

    print(f"Self-test OK! {len(names)} ferramentas MCP validadas: {', '.join(names)}")
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        return run_self_test()

    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"JSON invalido: {exc}"},
            }
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()
            continue

        resp = handle_message(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
