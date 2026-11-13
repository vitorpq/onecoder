---
status: accepted
---

# 0002 — Orquestracao Multi-VPS com Dokploy e Rede Privada Tailscale

Decidimos orquestrar os builds e deploys de todas as VPS de clientes a partir de uma unica instancia **Dokploy** na VPS Central comunicando-se via rede privada **Tailscale** (com firewall UFW fechando a porta 22 publica), em vez de manter arquivos `.github/workflows` e chaves SSH distribuidos por repositorio ou nos computadores dos desenvolvedores.

## Considered Options

- **GitHub Actions + Secrets SSH por repositorio:** Exige criar e manter YAML de CI/CD em cada projeto, espalha chaves SSH privadas de clientes pelos repositorios e obriga deixar a porta SSH (22) exposta na internet publica para runners com IPs dinamicos.
- **Dokploy + Tailscale (escolhida):** Conecta o GitHub uma unica vez, padroniza Docker/Compose com Traefik e HTTPS automatico (Let's Encrypt) e restringe o acesso SSH exclusivamente ao Control Plane pela interface `tailscale0`.

## Consequences

- Todas as aplicacoes de clientes passam a adotar containers Docker (`Dockerfile` ou `docker-compose.yml`).
- Cada nova VPS de cliente precisa ser provisionada uma unica vez via `scripts/bootstrap-client-vps.sh` e registrada como *Remote Server* no Dokploy usando seu IP privado Tailscale.
