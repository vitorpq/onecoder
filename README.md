# onecoder — IA Operacional Central (Gemma 4 + MCP) & Deploy Zero-SSH

Plataforma interna para sua empresa de TI unificar:
1. **IA Centralizada (LiteLLM Proxy + Gemma 4):** Todos os devs usam **Gemma 4 (31B / 26B MoE)** diretamente do **VS Code** ou do **OpenCode**, com uma unica conta da empresa, chaves individuais e limite mensal de gastos.
2. **IA Operacional via MCP (`onecoder-mcp`):** A IA conhece o catalogo de sistemas e clientes da empresa, investiga erros em VPS de clientes sem SSH, cria novos sistemas e sobe branches em dominios de teste (`*.teste.vitor.one`).
3. **Deploy Zero-SSH e Zero-Workflow (Dokploy + Tailscale):** Um servidor central orquestra builds e deploys em todas as VPS dos clientes via rede privada Tailscale, com trava de permissao entre `dev` (livre em dominios de teste) e `admin` (producao/`main`).

---

## Estrutura do Repositorio

```text
onecoder/
├── bin/onecoder                         # CLI dos devs (login, code, mcp, setup-vscode, init, projects, deploy, doctor)
├── mcp-server/
│   └── onecoder_mcp.py                  # Servidor MCP (stdio JSON-RPC) que conecta a IA ao catalogo e ao Dokploy
├── central-server/
│   ├── company-catalog.json           # Catalogo central de clientes, sistemas e regras da empresa
│   ├── docker-compose.yml             # Stack LiteLLM Proxy + Postgres
│   ├── litellm_config.yaml            # Aliases do Gemma 4 (31B, 26B MoE, Free, AI Studio)
│   ├── .env.example                   # Variaveis da VPS Central
│   ├── setup-central-vps.sh           # Provisiona Dokploy + Tailscale + LiteLLM na VPS Central
│   └── create-dev-key.sh              # Gera Virtual Key com perfil (dev/admin) e orcamento mensal
├── scripts/
│   └── bootstrap-client-vps.sh        # Prepara qualquer VPS limpa de cliente em 1 comando
└── templates/
    └── .onecoder.example.json           # Exemplo de vinculo de um projeto com o Dokploy
```

---

## Parte 1 — Subir a VPS Central da Empresa (1 unica vez)

1. Copie este repositorio para a VPS central e execute:
   ```bash
   sudo ./central-server/setup-central-vps.sh
   ```
2. Edite `central-server/.env` com suas chaves reais (`LITELLM_MASTER_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`) e suba o proxy:
   ```bash
   docker compose -f central-server/docker-compose.yml --env-file central-server/.env up -d
   ```
3. Personalize `central-server/company-catalog.json` com os clientes, VPSs e padroes da sua empresa.
4. No painel do Dokploy (`http://<IP>:3000`), configure:
   - Dominio HTTPS para o Dokploy (`https://deploy.vitor.one`) e para o LiteLLM (`https://ia.vitor.one`).
   - DNS wildcard `*.teste.vitor.one` apontando para o servidor de homologacao/preview.
   - Integracao com o **GitHub App** da empresa (para deploys automaticos ao aprovar/mergir na `main`).
5. Gere a chave individual de cada dev (ou admin):
   ```bash
   ./central-server/create-dev-key.sh joao 15 dev
   ./central-server/create-dev-key.sh vitor 30 admin
   ```

---

## Parte 2 — Provisionar uma VPS de Cliente (1 comando por cliente)

Em qualquer VPS nova de cliente (Ubuntu/Debian), execute como `root`:

```bash
./scripts/bootstrap-client-vps.sh \
  --tailscale-key "tskey-auth-SEU_TOKEN" \
  --hostname "cliente-acme-prod" \
  --dokploy-pubkey "ssh-ed25519 AAAA... dokploy-central" \
  --lock-ssh
```

---

## Parte 3 — Fluxo Diario do Desenvolvedor (VS Code + OpenCode)

1. **Instalar a CLI no PC do dev:**
   ```bash
   chmod +x bin/onecoder mcp-server/onecoder_mcp.py
   sudo ln -sf "$(pwd)/bin/onecoder" /usr/local/bin/onecoder
   ```
2. **Fazer login (1 unica vez):**
   ```bash
   onecoder login \
     --ai-url "https://ia.vitor.one" \
     --ai-key "sk-virtual-key-do-dev" \
     --dokploy-url "https://deploy.vitor.one" \
     --dokploy-key "api-key-do-dokploy" \
     --role "dev" \
     --preview-domain "teste.vitor.one"
   ```
   Isso configura automaticamente:
   - **OpenCode** (`~/.config/opencode/opencode.json`) com o modelo **Gemma 4** + o servidor MCP **`onecoder-empresa`**.
   - **Aider** (`~/.aider.conf.yml`).
   - Template MCP para **VS Code** (`~/.config/onecoder/vscode-mcp.json`).

3. **Ativar no VS Code dentro de qualquer projeto:**
   ```bash
   onecoder setup-vscode
   ```
   Isso cria `.vscode/mcp.json` e `.vscode/settings.json` conectando o VS Code ao servidor MCP `onecoder-empresa`.

4. **O que o dev pode pedir no chat do VS Code ou do OpenCode (`onecoder code`):**
   * *"Consulte o catalogo da empresa e me diga onde roda a API do cliente X."* -> usa `consultar_catalogo_empresa`
   * *"O sistema do cliente X esta dando erro 500, veja os ultimos deploys e o status na VPS."* -> usa `diagnosticar_sistema_cliente`
   * *"Suba minha branch `fix/erro-boleto` em um dominio de teste para validarmos antes do merge."* -> usa `subir_branch_dominio_teste`
   * *"Crie um novo projeto no Dokploy para o servico de relatorios."* -> usa `criar_novo_sistema`

---

## Controle de Permissao: Teste (`dev`) vs Producao (`admin`)

* **Perfil `dev` (padrao):** Pode consultar o catalogo, diagnosticar erros sem SSH, criar sistemas e publicar qualquer branch em dominios de teste (`*.teste.vitor.one`) usando o chat ou `onecoder deploy --preview <branch>`. Tentativas de acionar `deploy_producao_main` ou `onecoder deploy` em producao sao bloqueadas automaticamente.
* **Perfil `admin`:** Pode aprovar merges na `main` (onde o webhook do Dokploy atualiza a VPS do cliente) ou acionar `deploy_producao_main` / `onecoder deploy`, com registro em `~/.config/onecoder/audit.log`.

---

## Documentacao de Arquitetura, Specs, Diagnostico e Backlog

* **Linguagem do Dominio:** [CONTEXT.md](./CONTEXT.md)
* **Decisoes Arquiteturais (ADRs):**
  * [0001 — Gateway de IA Central via APIs Serverless](./docs/adr/0001-gateway-ia-central-via-apis-serverless.md)
  * [0002 — Orquestracao Multi-VPS com Dokploy e Tailscale](./docs/adr/0002-orquestracao-multi-vps-com-dokploy-e-tailscale.md)
  * [0003 — Agente Operacional via MCP stdio Zero Dependencias](./docs/adr/0003-agente-operacional-via-mcp-stdio-zero-dependencias.md)
  * [0004 — Governanca de Deploy (Preview Livre vs Producao Restrita)](./docs/adr/0004-governanca-de-deploy-preview-livre-producao-restrita.md)
* **Especificacoes Tecnicas e Diagnostico:**
  * [01 — Arquitetura e Fluxos](./docs/specs/01-arquitetura-e-fluxos.md)
  * [02 — Protocolo MCP e Contratos de API](./docs/specs/02-protocolo-mcp-e-contratos-api.md)
  * [03 — Guia de Diagnostico e Runbook Operacional](./docs/specs/03-guia-de-diagnostico-e-runbook.md)
* **Backlog de Evolucao (Tickets):**
  * [Indice de Tickets](./docs/tickets/README.md)
