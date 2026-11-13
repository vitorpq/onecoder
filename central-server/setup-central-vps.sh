#!/usr/bin/env bash
set -euo pipefail

# Provisiona a VPS Central da empresa com Dokploy, Tailscale e LiteLLM Proxy.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Erro: execute este script como root (ex: sudo $0)." >&2
  exit 1
fi

echo "==> [1/4] Verificando Tailscale..."
if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL https://tailscale.com/install.sh | sh
else
  echo "Tailscale ja instalado."
fi

if ! tailscale status >/dev/null 2>&1; then
  echo "Tailscale ainda nao conectado. Execute 'tailscale up --ssh' apos concluir."
fi

echo "==> [2/4] Verificando Dokploy (e Docker)..."
if ! command -v docker >/dev/null 2>&1 || ! docker service ls 2>/dev/null | grep -q "dokploy"; then
  curl -sSL https://dokploy.com/install.sh | sh
else
  echo "Dokploy ja esta em execucao."
fi

echo "==> [3/4] Preparando arquivo .env do LiteLLM..."
if [[ ! -f "${SCRIPT_DIR}/.env" ]]; then
  cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
  echo "Arquivo ${SCRIPT_DIR}/.env criado a partir de .env.example."
  echo "ATENCAO: Edite ${SCRIPT_DIR}/.env com suas chaves reais (OPENROUTER_API_KEY, GEMINI_API_KEY, LITELLM_MASTER_KEY) e rode este script novamente ou execute 'docker compose up -d'."
fi

echo "==> [4/4] Subindo LiteLLM Proxy..."
docker compose -f "${SCRIPT_DIR}/docker-compose.yml" --env-file "${SCRIPT_DIR}/.env" up -d

echo ""
echo "Setup da VPS Central concluido!"
echo "- Painel Dokploy: http://<IP_DA_VPS>:3000"
echo "- Gateway IA (LiteLLM): http://<IP_DA_VPS>:4000"
echo "- Proximo passo: gere chaves individuais para os devs com ./create-dev-key.sh <nome> <limite_usd>"
