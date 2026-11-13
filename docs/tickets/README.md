# Backlog de Evolução — onecoder

Tickets estruturados para endurecimento de segurança, observabilidade, automação de previews e sincronização de catálogo.

| Ticket | Prioridade | Status | Resumo |
| :--- | :--- | :--- | :--- |
| [TICKET-001](./TICKET-001-validacao-rbac-e-auditoria-no-servidor-central.md) | Alta (Segurança) | Concluido | Mover validação `dev` vs `admin`, chave do Dokploy e `audit.log` para o servidor central |
| [TICKET-002](./TICKET-002-logs-runtime-de-containers-via-mcp.md) | Alta (Diagnóstico) | Concluido | Adicionar leitura de logs em tempo real (`stdout`/`stderr`) de containers via MCP |
| [TICKET-003](./TICKET-003-garbage-collection-de-ambientes-preview.md) | Média (Custo/Ops) | Concluido | Garbage collection automático de ambientes de teste após merge na `main` ou TTL |
| [TICKET-004](./TICKET-004-sincronizacao-automatica-do-catalogo.md) | Média (DX) | Concluido | Sincronizar e enriquecer `company-catalog.json` automaticamente a partir do Dokploy |
| [TICKET-005](./TICKET-005-integracao-github-pr-e-smoke-test-automatico.md) | Baixa (DX) | Concluido | Healthcheck pós-deploy de preview e comentário automático com URL no Pull Request |
