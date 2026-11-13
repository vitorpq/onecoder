# TICKET-004 — Sincronização Automática do Catálogo da Empresa

- **Prioridade:** Média (Experiência do Dev)
- **Status:** Aberto

## Contexto e Problema
Hoje o arquivo [central-server/company-catalog.json](../../central-server/company-catalog.json) exige manutenção manual para manter nomes de clientes, IPs Tailscale, stacks e `dokploy_application_id` atualizados. Quando novos clientes entram, o catálogo estático pode ficar defasado em relação ao Dokploy.

## Solução Proposta
1. Criar um script `central-server/sync-catalog.py` que consulta `/api/project.all` e `/api/server.all` no Dokploy e mescla automaticamente com os metadados de negócio (nome amigável do cliente, descrição de arquitetura, regras de stack) preservados no `company-catalog.json`.
2. Adicionar um cache curto em memória/arquivo no `onecoder_mcp.py` para que `consultar_catalogo_empresa` responda rapidamente mesmo com dezenas de clientes cadastrados.

## Arquivos Afetados
- `central-server/sync-catalog.py` (novo)
- [central-server/company-catalog.json](../../central-server/company-catalog.json)
- [mcp-server/onecoder_mcp.py](../../mcp-server/onecoder_mcp.py)

## Critérios de Aceite
- Rodar `sync-catalog.py` atualiza IDs, domínios e servidores reais sem apagar anotações manuais de arquitetura já preenchidas no JSON.

## Como Verificar
- Executar `sync-catalog.py` contra o Dokploy (ou fixture JSON simulada) e validar diff resultante com `python3 -m json.tool`.
