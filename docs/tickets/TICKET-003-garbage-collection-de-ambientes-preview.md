# TICKET-003 — Garbage Collection de Ambientes Preview

- **Prioridade:** Média (Custo/Operação)
- **Status:** Concluido

## Contexto e Problema
A ferramenta `subir_branch_dominio_teste` e o comando `onecoder deploy --preview` criam uma aplicação dedicada e um domínio `*.teste.vitor.one` no Dokploy para cada branch testada. Sem limpeza automática, containers antigos de branches já mergeadas ou abandonadas continuam consumindo RAM, CPU e disco no servidor de homologação.

## Solução Proposta
1. Adotar um prefixo/tag padrão ou metadado de criação nos previews criados pelo `onecoder`.
2. Criar um script/cron na VPS Central (`central-server/cleanup-previews.py`) que:
   - Lista aplicações de preview no Dokploy.
   - Verifica se a branch ainda existe no repositório Git ou se ultrapassou o TTL configurável (ex: 7 dias sem deploy).
   - Remove a aplicação e o domínio de preview via API do Dokploy (`application.delete` / `domain.delete`).
3. Opcionalmente expor a ferramenta MCP `remover_ambiente_teste` para o próprio dev encerrar o preview após terminar o teste.

## Arquivos Afetados
- `central-server/cleanup-previews.py` (novo)
- [mcp-server/onecoder_mcp.py](../../mcp-server/onecoder_mcp.py)

## Critérios de Aceite
- Ambientes de teste inativos além do TTL são removidos automaticamente sem afetar aplicações de produção (`main`).
- Modo `--dry-run` lista exatamente o que seria removido antes de apagar qualquer serviço.

## Como Verificar
- Executar `python3 central-server/cleanup-previews.py --dry-run` e validar que apenas previews expirados são selecionados.
