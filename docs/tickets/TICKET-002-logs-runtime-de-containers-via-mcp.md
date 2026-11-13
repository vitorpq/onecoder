# TICKET-002 — Leitura de Logs Runtime de Containers via MCP

- **Prioridade:** Alta (Diagnóstico)
- **Status:** Aberto

## Contexto e Problema
Atualmente a ferramenta `diagnosticar_sistema_cliente` em [mcp-server/onecoder_mcp.py](../../mcp-server/onecoder_mcp.py) consulta `/api/application.one`, `/api/deployment.all` e `/api/previewDeployment.all`. Isso retorna o status e o histórico de builds/deploys, mas não traz os logs de execução (`stdout`/`stderr`) do container em tempo real (ex: um erro 500 de banco de dados ou exceção de runtime após o deploy já ter sido concluído).

## Solução Proposta
1. Mapear o endpoint de leitura de logs de container disponível na versão instalada do Dokploy (`/swagger` na VPS Central) ou expor uma ação controlada no serviço central (conectado via Tailscale/Docker socket apenas leitura).
2. Criar uma nova ferramenta MCP `ler_logs_container_tempo_real` aceitando `applicationId`, `tailLines` (padrão `100`, máximo `500`) e filtro opcional `search`.
3. Redigir/mascarar automaticamente padrões sensíveis (`PASSWORD`, `SECRET`, `TOKEN`, `Bearer `) antes de retornar os logs para o contexto da LLM.

## Arquivos Afetados
- [mcp-server/onecoder_mcp.py](../../mcp-server/onecoder_mcp.py)
- [docs/specs/02-protocolo-mcp-e-contratos-api.md](../specs/02-protocolo-mcp-e-contratos-api.md)

## Critérios de Aceite
- A ferramenta `ler_logs_container_tempo_real` aparece em `tools/list` e no `--self-test`.
- Solicitar no VS Code / OpenCode *"leia os últimos logs de erro do sistema X"* retorna o traceback real sem acesso SSH.
- Credenciais comuns em variáveis/linhas de log são mascaradas antes de chegar ao modelo de IA.

## Como Verificar
- Executar `./mcp-server/onecoder_mcp.py --self-test` e validar o schema da nova ferramenta.
- Testar contra uma aplicação com erro proposital no Dokploy e confirmar retorno das últimas `tailLines`.
