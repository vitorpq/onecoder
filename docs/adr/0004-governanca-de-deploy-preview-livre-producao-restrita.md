---
status: accepted
---

# 0004 — Governanca de Deploy: Preview Livre para Devs e Producao Restrita a Admin

Decidimos permitir que qualquer desenvolvedor (`ONECODER_ROLE=dev`) publique branches livremente em dominios temporarios de teste (`*.teste.vitor.one`), enquanto o acionamento direto de deploy em producao (`main`) e bloqueado para `dev` e restrito ao fluxo de Pull Request aprovado ou ao perfil `admin` (com registro em log de auditoria).

## Considered Options

- **Acesso irrestrito a producao via chat/CLI:** Rapido, mas aumenta o risco de um comando ou prompt impreciso sobrescrever o sistema em producao de um cliente sem validacao previa.
- **Bloqueio total de deploy para devs:** Mantem producao segura, mas devolve a friccao e o gargalo de o dev depender do Tech Lead apenas para subir uma branch de teste para validacao.
- **Preview livre + Producao restrita (escolhida):** Garante autonomia total para testar correcoes e novas features em HTTPS isolado antes de abrir PR para a `main`.

## Consequences

- Exige configuracao de DNS wildcard (`*.teste.vitor.one`) apontando para o servidor de homologacao/preview.
- Na implementacao atual (cliente local), a trava `ONECODER_ROLE` e o `audit.log` residem no PC do desenvolvedor; o endurecimento server-side dessa regra esta especificado no `TICKET-001`.
