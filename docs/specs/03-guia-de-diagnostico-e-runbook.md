# Spec 03 — Guia de Diagnóstico e Runbook Operacional

Este runbook cobre o diagnóstico de falhas na própria plataforma **onecoder** (PC do desenvolvedor, Servidor Central, Servidor MCP e VPS de clientes).

---

## 1. Diagnóstico Rápido no PC do Desenvolvedor

Execute em ordem:

```bash
# 1. Verifica MCP local, Gateway de IA (LiteLLM) e API do Dokploy
onecoder doctor

# 2. Testa o servidor MCP isolado (sem rede)
./mcp-server/onecoder_mcp.py --self-test

# 3. Inspeciona variaveis salvas localmente (cuidado: exibe chaves)
cat ~/.config/onecoder/config.env
```

---

## 2. Problemas no Gateway de IA (LiteLLM Proxy)

### Sintoma: `onecoder doctor` falha em `/v1/models` ou agente retorna `401 Unauthorized`
1. **No PC do dev:** Confirme que `ONECODER_AI_URL` não possui `/v1` no final dentro de `~/.config/onecoder/config.env` (o script acrescenta `/v1` automaticamente).
2. **Na VPS Central:** Verifique se os containers estão saudáveis:
   ```bash
   docker compose -f central-server/docker-compose.yml ps
   docker compose -f central-server/docker-compose.yml logs --tail=100 litellm
   ```
3. **Orçamento mensal estourado (`BudgetExceededError`):**
   Consulte o gasto da Virtual Key do dev na VPS Central:
   ```bash
   source central-server/.env
   curl -sS -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
     "http://localhost:${LITELLM_PORT:-4000}/key/info?key=SUA_VIRTUAL_KEY"
   ```
   Ou gere uma nova chave/aumente o limite pelo painel admin do LiteLLM (`http://<IP>:4000/ui`).

### Sintoma: Erro `429` ou falha de provedor upstream (OpenRouter / AI Studio)
- O modelo `gemma-4-free` (`:free` no OpenRouter) e o `gemma-4-studio` têm limites estritos de requisições por minuto.
- **Solução imediata:** No PC do dev, troque temporariamente para o modelo pago de baixo custo:
  ```bash
  onecoder code gemma-4-26b
  ```
- **Na VPS Central:** Valide se `OPENROUTER_API_KEY` e `GEMINI_API_KEY` em `central-server/.env` possuem créditos/permissão e reinicie o serviço após editar:
  ```bash
  docker compose -f central-server/docker-compose.yml --env-file central-server/.env up -d --force-recreate litellm
  ```

---

## 3. Problemas no Servidor MCP (`onecoder-mcp`) no VS Code / OpenCode

### Sintoma: VS Code ou OpenCode não enxerga as ferramentas `onecoder-empresa`
1. Confirme que `bin/onecoder` está no `PATH` e executável:
   ```bash
   which onecoder
   ls -l ~/.config/opencode/opencode.json .vscode/mcp.json
   ```
2. Se estiver em um repositório novo no VS Code, rode:
   ```bash
   onecoder setup-vscode
   ```
3. **Teste manual do protocolo JSON-RPC via `stdio`:**
   ```bash
   printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n' | onecoder mcp
   ```
   Deve imprimir dois objetos JSON válidos (um com `serverInfo` e outro listando as 5 ferramentas).

### Sintoma: Ferramenta MCP retorna `"Dokploy nao configurado"` ou `"Erro HTTP 401"`
- O `onecoder mcp` carrega `~/.config/onecoder/config.env`. Rode `onecoder login` novamente garantindo que `--dokploy-url` (sem `/api` no final) e `--dokploy-key` (`x-api-key` gerada no perfil do Dokploy em `/settings/profile`) estejam corretos.

### Auditoria de ações executadas pelo MCP
Consulte o histórico local de criações e deploys disparados pelo MCP:
```bash
cat ~/.config/onecoder/audit.log
```

---

## 4. Problemas de Deploy e Rede nas VPS de Clientes

### Sintoma: Dokploy não consegue conectar na VPS do cliente
1. **Na VPS Central (ou via painel Tailscale):** Verifique se a VPS do cliente está online na malha privada:
   ```bash
   tailscale status
   tailscale ping <hostname-ou-ip-tailscale>
   ```
2. **Na VPS do cliente:** Verifique:
   - Status do Docker e UFW:
     ```bash
     systemctl status docker
     ufw status verbose
     ```
     Confirme que `tailscale0` está liberado no UFW e que `80/tcp` e `443/tcp` estão abertos.
   - Presença da chave pública do Dokploy:
     ```bash
     cat /root/.ssh/authorized_keys
     ```

### Sintoma: Domínio de teste (`*.teste.vitor.one`) não abre ou falha HTTPS
1. Confirme no provedor DNS que existe um registro `A` wildcard (`*.teste.vitor.one`) apontando para o IP público da VPS onde os containers de preview estão rodando.
2. Confirme que as portas `80` e `443` não estão bloqueadas pelo firewall do provedor cloud (AWS Security Group, Hetzner Firewall, Oracle Ingress Rules, etc.) — o Let's Encrypt exige porta `80` ou `443` acessível externamente para emitir o certificado.
3. Valide no Dokploy se o `port` informado em `subir_branch_dominio_teste` (padrão `3000`) corresponde à porta em que o container realmente escuta internamente.
