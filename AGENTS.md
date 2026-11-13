# AGENTS.md — Guia de Continuidade para Agentes de IA

Este repositório implementa a plataforma **onecoder** (Gateway de IA centralizado com LiteLLM + Gemma 4, Servidor MCP operacional e automação de deploy multi-VPS com Dokploy + Tailscale).

## 1. Leitura Obrigatória Antes de Alterar Código

Siga esta ordem para entender o domínio, decisões já tomadas, contratos e backlog:

1. **Vocabulário do Domínio:** Leia [CONTEXT.md](./CONTEXT.md) e use estritamente os termos canônicos definidos lá.
2. **Decisões Arquiteturais (ADRs):** Leia [docs/adr/](./docs/adr/) antes de propor mudanças estruturais:
   - [0001-gateway-ia-central-via-apis-serverless.md](./docs/adr/0001-gateway-ia-central-via-apis-serverless.md)
   - [0002-orquestracao-multi-vps-com-dokploy-e-tailscale.md](./docs/adr/0002-orquestracao-multi-vps-com-dokploy-e-tailscale.md)
   - [0003-agente-operacional-via-mcp-stdio-zero-dependencias.md](./docs/adr/0003-agente-operacional-via-mcp-stdio-zero-dependencias.md)
   - [0004-governanca-de-deploy-preview-livre-producao-restrita.md](./docs/adr/0004-governanca-de-deploy-preview-livre-producao-restrita.md)
3. **Especificações e Runbook de Diagnóstico:**
   - [01-arquitetura-e-fluxos.md](./docs/specs/01-arquitetura-e-fluxos.md)
   - [02-protocolo-mcp-e-contratos-api.md](./docs/specs/02-protocolo-mcp-e-contratos-api.md)
   - [03-guia-de-diagnostico-e-runbook.md](./docs/specs/03-guia-de-diagnostico-e-runbook.md)
4. **Backlog de Evolução:** Veja [docs/tickets/README.md](./docs/tickets/README.md) para escolher o próximo ticket.

---

## 2. Regras Inegociáveis do Projeto

- **Zero dependências externas no servidor MCP e na CLI dos devs:** [mcp-server/onecoder_mcp.py](./mcp-server/onecoder_mcp.py) deve usar apenas a biblioteca padrão do Python 3, e [bin/onecoder](./bin/onecoder) apenas Bash + ferramentas padrão (`curl`, `python3`, `git`).
- **Segurança Zero-SSH para devs:** Nunca gere nem distribua chaves SSH de VPS de clientes para máquinas de desenvolvedores.
- **Governança Dev vs Admin:** Nunca remova a trava que impede `ONECODER_ROLE=dev` de executar deploy direto em produção (`main`).
- **Documentação viva:** Ao implementar um ticket de `docs/tickets/`, atualize o status do ticket, as specs afetadas em `docs/specs/` e crie um novo ADR em `docs/adr/` se houver mudança arquitetural relevante.

---

## 3. Como Trabalhar em um Ticket

1. Abra o ticket desejado em `docs/tickets/TICKET-*.md`.
2. Leia todos os arquivos listados na seção **Arquivos Afetados**.
3. Implemente a mudança respeitando os **Critérios de Aceite**.
4. Execute os passos da seção **Como Verificar** do ticket além das verificações globais abaixo.
5. Atualize o status do ticket no próprio arquivo e em [docs/tickets/README.md](./docs/tickets/README.md).

---

## 4. Verificação Obrigatória Após Qualquer Edição

Execute sempre antes de finalizar uma tarefa:

```bash
bash -n bin/onecoder central-server/setup-central-vps.sh central-server/create-dev-key.sh scripts/bootstrap-client-vps.sh
./mcp-server/onecoder_mcp.py --self-test
./bin/onecoder --help
python3 -m json.tool central-server/company-catalog.json >/dev/null
```
