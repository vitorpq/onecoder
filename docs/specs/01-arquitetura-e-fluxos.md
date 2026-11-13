# Spec 01 — Arquitetura e Fluxos do Sistema

## 1. Mapa de Módulos

| Módulo | Caminho | Responsabilidade |
| :--- | :--- | :--- |
| **Control Plane (IA + Deploy)** | [central-server/](../../central-server/) | Provisiona Dokploy + Tailscale + LiteLLM Proxy + Postgres e armazena o `company-catalog.json`. |
| **Provisionamento de Clientes** | [scripts/bootstrap-client-vps.sh](../../scripts/bootstrap-client-vps.sh) | Prepara VPS limpa de cliente (Docker, Tailscale, chave SSH do Dokploy, UFW). |
| **Agente Operacional (MCP)** | [mcp-server/onecoder_mcp.py](../../mcp-server/onecoder_mcp.py) | Servidor MCP JSON-RPC 2.0 via `stdio` que conecta VS Code e OpenCode ao catálogo e ao Dokploy. |
| **CLI do Desenvolvedor** | [bin/onecoder](../../bin/onecoder) | Gerencia login local, configuração de OpenCode/Aider/VS Code, servidor MCP e deploys. |

---

## 2. Fluxo 1 — Onboarding de Desenvolvedor

```mermaid
sequenceDiagram
    actor Admin as Admin (VPS Central)
    participant KeyScript as create-dev-key.sh
    participant LiteLLM as LiteLLM Proxy (:4000)
    actor Dev as Desenvolvedor (PC Local)
    participant CLI as bin/onecoder

    Admin->>KeyScript: ./create-dev-key.sh joao 15 dev
    KeyScript->>LiteLLM: POST /key/generate (max_budget=15, budget_duration="30d")
    LiteLLM-->>KeyScript: Retorna Virtual Key (sk-...)
    KeyScript-->>Admin: Imprime comando "onecoder login ..."
    Admin-->>Dev: Envia comando pronto

    Dev->>CLI: onecoder login --ai-url ... --ai-key ... --dokploy-url ... --dokploy-key ... --role dev
    CLI->>CLI: Grava ~/.config/onecoder/config.env (chmod 600)
    CLI->>CLI: Configura ~/.aider.conf.yml
    CLI->>CLI: Configura ~/.config/opencode/opencode.json (provider + mcp)
    CLI->>CLI: Gera ~/.config/onecoder/vscode-mcp.json
```

---

## 3. Fluxo 2 — Onboarding de VPS de Cliente (Zero-SSH para Devs)

```mermaid
sequenceDiagram
    actor Admin as Admin
    participant VPS as VPS do Cliente (Ubuntu/Debian)
    participant TS as Rede Tailscale
    participant Dokploy as Dokploy Central

    Admin->>VPS: bootstrap-client-vps.sh --tailscale-key ... --hostname cliente-acme-prod --dokploy-pubkey ... --lock-ssh
    VPS->>VPS: Instala Docker Engine + Compose
    VPS->>TS: tailscale up --authkey ... --hostname ... --ssh
    VPS->>VPS: Adiciona dokploy-pubkey em /root/.ssh/authorized_keys
    VPS->>VPS: Configura UFW (libera 80/443 e tailscale0; fecha porta 22 publica)
    VPS-->>Admin: Exibe IP privado Tailscale (100.x.x.x)
    Admin->>Dokploy: Cadastra Remote Server com o IP Tailscale
```

---

## 4. Fluxo 3 — Diagnóstico e Ambiente de Teste por Branch (VS Code / OpenCode)

```mermaid
sequenceDiagram
    actor Dev as Dev (VS Code / OpenCode)
    participant LLM as LiteLLM Proxy (Gemma 4)
    participant MCP as onecoder mcp (onecoder_mcp.py)
    participant Dokploy as Dokploy API

    Dev->>LLM: "Erro 500 no cliente X. Veja os deploys e suba minha branch fix/boleto em teste."
    LLM->>MCP: tools/call consultar_catalogo_empresa
    MCP->>Dokploy: GET /api/project.all + /api/server.all
    MCP-->>LLM: Catalogo + IDs reais do Dokploy

    LLM->>MCP: tools/call diagnosticar_sistema_cliente (applicationId)
    MCP->>Dokploy: GET /api/application.one + /api/deployment.all + /api/previewDeployment.all
    MCP-->>LLM: Configuracao + ultimos 10 deploys

    LLM->>MCP: tools/call subir_branch_dominio_teste (environmentId, appName, branch)
    MCP->>Dokploy: POST /api/application.create -> POST /api/domain.create -> POST /api/application.deploy
    MCP-->>LLM: url_teste = https://fix-boleto-api-acme.teste.vitor.one
    LLM-->>Dev: Explica a causa do erro, edita codigo local e entrega a URL de teste
```

---

## 5. Arquivos de Configuração e Variáveis

### 5.1 `~/.config/onecoder/config.env` (PC do Dev, `chmod 600`)

| Variável | Descrição | Exemplo |
| :--- | :--- | :--- |
| `ONECODER_AI_URL` | URL base do LiteLLM Proxy (sem `/v1`) | `https://ia.vitor.one` |
| `ONECODER_AI_KEY` | Virtual Key individual do dev | `sk-...` |
| `ONECODER_DOKPLOY_URL` | URL base do painel Dokploy | `https://deploy.vitor.one` |
| `ONECODER_DOKPLOY_KEY` | API Key usada no header `x-api-key` | `...` |
| `ONECODER_DEFAULT_MODEL` | Modelo padrão no `onecoder code` | `gemma-4-31b` |
| `ONECODER_ROLE` | Perfil de permissão (`dev` ou `admin`) | `dev` |
| `ONECODER_PREVIEW_DOMAIN` | Domínio coringa para ambientes de teste | `teste.vitor.one` |

### 5.2 `.onecoder.json` (Raiz do repositório do projeto)

Template em [templates/.onecoder.example.json](../../templates/.onecoder.example.json):
```json
{
  "client": "nome-do-cliente",
  "type": "application",
  "id": "applicationId-ou-composeId-no-dokploy"
}
```

### 5.3 `central-server/company-catalog.json`

Armazena `company`, `engineering_rules`, `stack_standards` e `clients` (cada cliente com `name`, `vps_hostname`, `tailscale_ip` e lista `systems`). Pode ser sobrescrito via variável `ONECODER_CATALOG_PATH`.
