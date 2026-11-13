# Spec 02 — Protocolo MCP e Contratos de API

## 1. Servidor MCP (`mcp-server/onecoder_mcp.py`)

- **Transporte:** `stdio` com mensagens JSON-RPC 2.0 delimitadas por quebra de linha (`\n`).
- **Versão do protocolo:** `2024-11-05`
- **Identificação (`serverInfo`):** `{"name": "onecoder-empresa", "version": "0.2.0"}`
- **Métodos JSON-RPC suportados:**
  - `initialize`: retorna `protocolVersion`, `capabilities.tools`, `serverInfo` e `instructions`.
  - `notifications/initialized`: ignorado sem resposta (`None`), conforme especificação JSON-RPC para notificações.
  - `ping`: retorna `{}`.
  - `tools/list`: lista as 5 ferramentas registradas com `name`, `description` e `inputSchema`.
  - `tools/call`: valida e executa a ferramenta pelo nome, retornando `content` (`type: "text"`, JSON serializado) e `isError`.

---

## 2. Contrato das 5 Ferramentas MCP

| Ferramenta | Perfil | Parâmetros (`inputSchema`) | Endpoints Dokploy Chamados |
| :--- | :--- | :--- | :--- |
| `consultar_catalogo_empresa` | `dev` / `admin` | Nenhum (`{}`) | `GET /api/project.all`, `GET /api/server.all` |
| `diagnosticar_sistema_cliente` | `dev` / `admin` | `applicationId` (string, obrigatório) | `GET /api/application.one?applicationId=...`, `GET /api/deployment.all?applicationId=...`, `GET /api/previewDeployment.all?applicationId=...` |
| `subir_branch_dominio_teste` | `dev` / `admin` | `environmentId`, `appName`, `branch` (obrigatórios); `serverId`, `port` (opcional, padrão `3000`) | `POST /api/application.create`, `POST /api/domain.create`, `POST /api/application.deploy` |
| `criar_novo_sistema` | `dev` / `admin` | `projectName`, `appName` (obrigatórios); `description`, `testSubdomain`, `port` (opcional, padrão `3000`) | `POST /api/project.create`, (`GET /api/project.all` fallback), `POST /api/application.create`, `POST /api/domain.create` |
| `deploy_producao_main` | **Apenas `admin`** | `serviceType` (`application` \| `compose`), `serviceId`, `confirmMainMerge` (boolean) | `POST /api/application.deploy` ou `POST /api/compose.deploy` |

### Detalhes de Comportamento Importantes

1. **Sanitização DNS em `subir_branch_dominio_teste` e `criar_novo_sistema`:**
   - A função `sanitize_slug` converte para minúsculas, substitui caracteres fora de `[a-z0-9-]` por `-`, colapsa múltiplos hífens e limita a 40 caracteres (fallback `"preview"`).
   - Host gerado para branch: `<branch-slug>-<app-slug>.${ONECODER_PREVIEW_DOMAIN}`.
   - O domínio é criado com `"https": true` e `"certificateType": "letsencrypt"`.
2. **Trava RBAC em `deploy_producao_main`:**
   - Verifica `ONECODER_ROLE` (padrão `"dev"`).
   - Se `ONECODER_ROLE != "admin"`, retorna `{"bloqueado": true, "motivo": "..."}` sem chamar nenhum endpoint de deploy.
3. **Auditoria local (`append_audit_log`):**
   - As ferramentas `subir_branch_dominio_teste`, `criar_novo_sistema` e `deploy_producao_main` registram JSON Lines em `~/.config/onecoder/audit.log` contendo `timestamp` (UTC ISO 8601), `role`, `action` e `details`.

---

## 3. Contratos do Gateway de IA (`central-server/litellm_config.yaml`)

| Alias da Empresa | Modelo Upstream | Provedor |
| :--- | :--- | :--- |
| `gemma-4-31b` | `openrouter/google/gemma-4-31b-it` | OpenRouter |
| `gemma-4-26b` | `openrouter/google/gemma-4-26b-a4b-it` | OpenRouter |
| `gemma-4-free` | `openrouter/google/gemma-4-31b-it:free` | OpenRouter (Free) |
| `gemma-4-studio` | `gemini/gemma-4-31b-it` | Google AI Studio |

### Geração de Virtual Keys (`central-server/create-dev-key.sh`)

Envia `POST ${LITELLM_URL}/key/generate` com header `Authorization: Bearer ${LITELLM_MASTER_KEY}`:
```json
{
  "key_alias": "dev-<nome>",
  "max_budget": 15.0,
  "budget_duration": "30d",
  "models": ["gemma-4-31b", "gemma-4-26b", "gemma-4-free", "gemma-4-studio"],
  "metadata": {
    "developer": "<nome>",
    "role": "dev",
    "managed_by": "onecoder"
  }
}
```
