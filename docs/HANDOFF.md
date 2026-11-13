# Handoff — onecoder

## Current State

- **Git Repository:** `git@github.com:vitorpq/onecoder.git`
- **Branch / Base Commit:** `main` @ `a3e9887` (`feat: bootstrap onecoder platform and docs`)
- **Primary Domain:** `vitor.one` (`ia.vitor.one`, `deploy.vitor.one`, `*.teste.vitor.one`)

## Key References (Read Before Making Changes)

- **Agent Entry Point & Rules:** [AGENTS.md](../AGENTS.md) (mirrored via [CLAUDE.md](../CLAUDE.md))
- **Domain Glossary:** [CONTEXT.md](../CONTEXT.md)
- **Architecture Decisions (ADRs):** [docs/adr/](./adr/) (`0001` through `0004`)
- **Specs & Diagnostic Runbook:** [docs/specs/](./specs/) (`01-arquitetura-e-fluxos.md`, `02-protocolo-mcp-e-contratos-api.md`, `03-guia-de-diagnostico-e-runbook.md`)
- **Backlog Tickets:** [docs/tickets/README.md](./tickets/README.md) (`TICKET-001` through `TICKET-005`)

## What Was Built & Verified

- **Control Plane Stack:** [central-server/](../central-server/) (`docker-compose.yml`, `litellm_config.yaml`, `.env.example`, `company-catalog.json`, `setup-central-vps.sh`, `create-dev-key.sh`).
- **Client VPS Bootstrap:** [scripts/bootstrap-client-vps.sh](../scripts/bootstrap-client-vps.sh).
- **MCP Server (Python 3 stdlib, stdio JSON-RPC 2.0):** [mcp-server/onecoder_mcp.py](../mcp-server/onecoder_mcp.py).
- **Developer CLI:** [bin/onecoder](../bin/onecoder) and [templates/.onecoder.example.json](../templates/.onecoder.example.json).
- **Verified offline checks:** `bash -n`, `./mcp-server/onecoder_mcp.py --self-test`, `./bin/onecoder --help`, and `python3 -m json.tool` on JSON configs all pass.
- **Not yet run against live infra:** Central VPS provisioning, Dokploy REST calls, Tailscale mesh, and LiteLLM upstream requests remain untested until deployed on the target VPS.

## Suggested Next Steps

1. Provision the Control Plane VPS (`central-server/setup-central-vps.sh`) and verify real endpoints (`ia.vitor.one`, `deploy.vitor.one`, wildcard `*.teste.vitor.one`).
2. Prioritize [TICKET-001](./tickets/TICKET-001-validacao-rbac-e-auditoria-no-servidor-central.md) (move Dokploy credentials, RBAC check, and audit log from developer machines to the Control Plane) and [TICKET-002](./tickets/TICKET-002-logs-runtime-de-containers-via-mcp.md) (container runtime log reading via MCP).

## Suggested Skills

- **`tdd`**: Use when implementing `TICKET-001` through `TICKET-005` or adding unit/integration tests for `onecoder_mcp.py` and central API services.
- **`codebase-design`**: Use when designing the Control Plane proxy service in `TICKET-001` so `onecoder_mcp.py` and `bin/onecoder` keep clean module boundaries.
- **`domain-modeling`**: Use if introducing new domain concepts or changing terminology in `CONTEXT.md` / `docs/adr/`.
- **`diagnosing-bugs`**: Use when troubleshooting live deployments, Tailscale connectivity, Dokploy API responses, or LiteLLM proxy errors alongside `docs/specs/03-guia-de-diagnostico-e-runbook.md`.
- **`code-review`**: Use before merging or pushing changes implementing any backlog ticket.
