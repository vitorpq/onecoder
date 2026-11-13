---
status: accepted
---

# 0003 — Agente Operacional via MCP `stdio` com Zero Dependencias Externas

Decidimos implementar o servidor MCP (`mcp-server/onecoder_mcp.py`) sobre **JSON-RPC 2.0 via `stdio`** usando exclusivamente a biblioteca padrao do **Python 3**, em vez de adotar SDKs externos em Node.js/Python ou publicar um servidor HTTP remoto logo na fase inicial.

## Considered Options

- **SDK oficial MCP (`mcp` Python ou `@modelcontextprotocol/sdk` Node):** Exige gerenciar ambientes virtuais (`uv`/`.venv`) ou `node_modules` na maquina de cada desenvolvedor, aumentando o atrito de instalacao e suporte.
- **Servidor MCP remoto via HTTP/SSE na VPS Central:** Centraliza ainda mais a execucao, mas exige autenticacao HTTP por sessao e suporte consistente nos clientes (VS Code / OpenCode) antes de validarmos os fluxos operacionais.
- **Python 3 stdlib via `stdio` (escolhida):** Roda imediatamente em macOS e Linux sem instalar pacotes extras, e e suportado nativamente tanto pelo OpenCode (`mcp.onecoder-empresa`) quanto pelo VS Code (`.vscode/mcp.json`).

## Consequences

- Na arquitetura atual, o servidor MCP roda localmente na maquina do dev e utiliza as credenciais salvas em `~/.config/onecoder/config.env`. A migracao da camada de autenticacao/RBAC para um endpoint central na VPS da empresa esta planejada no `TICKET-001`.
