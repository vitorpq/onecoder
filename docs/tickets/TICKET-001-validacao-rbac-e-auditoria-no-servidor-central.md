# TICKET-001 — Validação RBAC e Auditoria no Servidor Central

- **Prioridade:** Alta (Segurança)
- **Status:** Concluido
- **ADRs relacionados:** [ADR-0003](../adr/0003-agente-operacional-via-mcp-stdio-zero-dependencias.md), [ADR-0004](../adr/0004-governanca-de-deploy-preview-livre-producao-restrita.md)

## Contexto e Problema
Atualmente, o arquivo `~/.config/onecoder/config.env` no PC do desenvolvedor armazena `ONECODER_ROLE` e `ONECODER_DOKPLOY_KEY` localmente, e o log `~/.config/onecoder/audit.log` é gravado apenas na máquina cliente. Isso significa que:
1. Um usuário com a `ONECODER_DOKPLOY_KEY` poderia chamar a API do Dokploy diretamente ou alterar `ONECODER_ROLE=admin` no próprio `.env`.
2. A auditoria fica fragmentada nos computadores individuais dos desenvolvedores.

## Solução Proposta
Criar um pequeno serviço proxy/API (`central-server/onecoder-control-api`) na VPS Central (no mesmo `docker-compose.yml` do LiteLLM):
1. Guardar a `DOKPLOY_API_KEY` exclusivamente na VPS Central.
2. O desenvolvedor envia apenas sua `ONECODER_AI_KEY` (Virtual Key do LiteLLM) no header `Authorization: Bearer ...`.
3. O proxy consulta `GET /key/info` no LiteLLM interno para obter `metadata.role` (`dev` ou `admin`) e `metadata.developer`.
4. Aplicar a trava de segurança (`dev` só executa catálogo, diagnóstico, criação e preview; `admin` pode acionar produção) e gravar a auditoria centralizada no Postgres ou em volume persistente na VPS Central.
5. Atualizar `mcp-server/onecoder_mcp.py` e `bin/onecoder` para apontar para esse endpoint central em vez de exigir `ONECODER_DOKPLOY_KEY` no PC do dev.

## Arquivos Afetados
- `central-server/docker-compose.yml`
- `mcp-server/onecoder_mcp.py`
- `bin/onecoder`

## Critérios de Aceite
- Desenvolvedores não recebem mais a `x-api-key` mestra do Dokploy durante `onecoder login`.
- Alterar `ONECODER_ROLE=admin` localmente não concede permissão de deploy em produção.
- Todas as ações ficam registradas com `developer`, `timestamp` e `action` na VPS Central.

## Como Verificar
- Tentar acionar `deploy_producao_main` usando uma Virtual Key com `metadata.role = "dev"` e confirmar resposta HTTP `403 Forbidden` vinda do servidor central.
- Verificar o registro da tentativa negada no log central de auditoria.
