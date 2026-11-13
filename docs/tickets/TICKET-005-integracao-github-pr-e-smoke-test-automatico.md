# TICKET-005 — Integração com Pull Request no GitHub e Smoke Test Pós-Deploy

- **Prioridade:** Baixa (DX)
- **Status:** Concluido

## Contexto e Problema
Ao rodar `subir_branch_dominio_teste`, a URL `https://<branch>-<app>.teste.vitor.one` é retornada apenas no chat/terminal de quem disparou o deploy. O revisor do Pull Request no GitHub e o cliente não recebem o link automaticamente, e não há validação automática de que o container respondeu HTTP 200 após subir.

## Solução Proposta
1. Após `POST /api/application.deploy` no fluxo de preview, aguardar o status de deploy concluir (polling em `/api/deployment.all`) e realizar um smoke test HTTP (`GET` na raiz ou `/health`) na URL gerada.
2. Se houver token do GitHub configurado (`GITHUB_TOKEN`) e a branch estiver associada a um PR aberto, publicar ou atualizar um comentário no PR com:
   - Link clicável do ambiente de teste (`https://...`).
   - Resultado do smoke test HTTP (status code e latência).

## Arquivos Afetados
- [mcp-server/onecoder_mcp.py](../../mcp-server/onecoder_mcp.py)
- [bin/onecoder](../../bin/onecoder)

## Critérios de Aceite
- O retorno de `subir_branch_dominio_teste` inclui o resultado do healthcheck HTTP (`ok`/`falha` + status code).
- Caso exista PR aberto e credencial GitHub configurada, o link de preview aparece automaticamente nos comentários do PR.

## Como Verificar
- Simular o deploy de uma branch associada a um PR de teste e confirmar o comentário postado + verificação do status HTTP.
