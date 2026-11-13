#!/usr/bin/env bash
set -euo pipefail

# Gera uma Virtual Key no LiteLLM para um desenvolvedor com limite mensal de gastos.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 <nome-do-dev> [limite-mensal-usd] [role: dev|admin]" >&2
  echo "Exemplo: $0 joao 15 dev" >&2
  exit 1
fi

DEV_NAME="$1"
MAX_BUDGET="${2:-15}"
DEV_ROLE="${3:-dev}"

if [[ "${DEV_ROLE}" != "dev" && "${DEV_ROLE}" != "admin" ]]; then
  echo "Erro: role deve ser 'dev' ou 'admin'." >&2
  exit 1
fi

if [[ -f "${SCRIPT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${SCRIPT_DIR}/.env"
  set +a
fi

LITELLM_URL="${LITELLM_URL:-http://localhost:${LITELLM_PORT:-4000}}"
MASTER_KEY="${LITELLM_MASTER_KEY:-}"

if [[ -z "${MASTER_KEY}" ]]; then
  echo "Erro: LITELLM_MASTER_KEY nao definida no ambiente ou em ${SCRIPT_DIR}/.env." >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
  echo "Erro: 'curl' e 'python3' sao necessarios." >&2
  exit 1
fi

PAYLOAD="$(python3 - "$DEV_NAME" "$MAX_BUDGET" "$DEV_ROLE" <<'PY'
import json
import sys

dev_name = sys.argv[1]
max_budget = float(sys.argv[2])
role = sys.argv[3]

print(json.dumps({
    "key_alias": f"dev-{dev_name}",
    "max_budget": max_budget,
    "budget_duration": "30d",
    "models": ["gemma-4-31b", "gemma-4-26b", "gemma-4-free", "gemma-4-studio"],
    "metadata": {
        "developer": dev_name,
        "role": role,
        "managed_by": "onecoder",
    },
}))
PY
)"

RESPONSE="$(curl -fsS -X POST "${LITELLM_URL%/}/key/generate" \
  -H "Authorization: Bearer ${MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d "${PAYLOAD}")"

DEV_KEY="$(python3 - "$RESPONSE" <<'PY'
import json
import sys

data = json.loads(sys.argv[1])
key = data.get("key") or ""
if not key:
    sys.stderr.write("Resposta inesperada do LiteLLM: " + sys.argv[1] + "\n")
    sys.exit(1)
print(key)
PY
)"

PUBLIC_AI_URL="${ONECODER_PUBLIC_AI_URL:-https://ia.vitor.one}"
PUBLIC_DOKPLOY_URL="${ONECODER_PUBLIC_DOKPLOY_URL:-https://deploy.vitor.one}"
PREVIEW_DOMAIN="${ONECODER_PREVIEW_DOMAIN:-teste.vitor.one}"

echo ""
echo "Virtual Key gerada com sucesso para '${DEV_NAME}' (perfil: ${DEV_ROLE}, limite: US$ ${MAX_BUDGET}/30d):"
echo "  Key: ${DEV_KEY}"
echo ""
echo "Envie este comando para o desenvolvedor rodar no PC dele:"
echo "  onecoder login --ai-url \"${PUBLIC_AI_URL}\" --ai-key \"${DEV_KEY}\" --dokploy-url \"${PUBLIC_DOKPLOY_URL}\" --dokploy-key \"<CHAVE_DOKPLOY>\" --role \"${DEV_ROLE}\" --preview-domain \"${PREVIEW_DOMAIN}\""
