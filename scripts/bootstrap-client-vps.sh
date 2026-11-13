#!/usr/bin/env bash
set -euo pipefail

# Prepara uma VPS limpa de cliente (Ubuntu/Debian) para deploy via Dokploy + Tailscale.

TAILSCALE_KEY=""
DOKPLOY_PUBKEY=""
CLIENT_HOSTNAME=""
LOCK_SSH=false

usage() {
  cat <<'EOF'
Uso: bootstrap-client-vps.sh --tailscale-key <tskey> --hostname <nome-vps> [opcoes]

Opcoes:
  --tailscale-key <key>     Auth key do Tailscale (ex: tskey-auth-...)
  --hostname <nome>         Nome desta VPS na rede Tailscale (ex: cliente-acme-prod)
  --dokploy-pubkey <pubkey> Chave SSH publica do servidor central Dokploy (opcional)
  --lock-ssh                Fecha a porta 22 publica no UFW (mantem SSH apenas via Tailscale)
  -h, --help                Exibe esta ajuda
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tailscale-key)
      TAILSCALE_KEY="${2:-}"
      shift 2
      ;;
    --dokploy-pubkey)
      DOKPLOY_PUBKEY="${2:-}"
      shift 2
      ;;
    --hostname)
      CLIENT_HOSTNAME="${2:-}"
      shift 2
      ;;
    --lock-ssh)
      LOCK_SSH=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Erro: opcao desconhecida '$1'." >&2
      usage
      exit 1
      ;;
  esac
done

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Erro: execute como root (ex: sudo $0 ...)." >&2
  exit 1
fi

if [[ -z "${TAILSCALE_KEY}" || -z "${CLIENT_HOSTNAME}" ]]; then
  echo "Erro: --tailscale-key e --hostname sao obrigatorios." >&2
  usage
  exit 1
fi

echo "==> [1/5] Instalando Docker Engine e Docker Compose..."
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
else
  echo "Docker ja instalado."
fi

echo "==> [2/5] Instalando e conectando Tailscale..."
if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
tailscale up --authkey="${TAILSCALE_KEY}" --hostname="${CLIENT_HOSTNAME}" --ssh

if [[ -n "${DOKPLOY_PUBKEY}" ]]; then
  echo "==> [3/5] Configurando chave SSH exclusiva do servidor central Dokploy..."
  mkdir -p /root/.ssh
  chmod 700 /root/.ssh
  touch /root/.ssh/authorized_keys
  chmod 600 /root/.ssh/authorized_keys
  if ! grep -Fqx "${DOKPLOY_PUBKEY}" /root/.ssh/authorized_keys; then
    printf '%s\n' "${DOKPLOY_PUBKEY}" >> /root/.ssh/authorized_keys
  fi
else
  echo "==> [3/5] Nenhuma --dokploy-pubkey informada; pulando authorized_keys."
fi

echo "==> [4/5] Configurando firewall UFW..."
if ! command -v ufw >/dev/null 2>&1; then
  apt-get update -y && apt-get install -y ufw
fi

ufw --force default deny incoming
ufw --force default allow outgoing
ufw allow 80/tcp comment "HTTP publico"
ufw allow 443/tcp comment "HTTPS publico"
ufw allow in on tailscale0 comment "Rede privada da empresa (Tailscale)"

if [[ "${LOCK_SSH}" == "true" ]]; then
  ufw delete allow 22/tcp 2>/dev/null || true
  ufw delete allow OpenSSH 2>/dev/null || true
  echo "Porta 22 publica fechada; SSH liberado apenas pela rede Tailscale."
else
  ufw allow 22/tcp comment "SSH (use --lock-ssh para restringir apenas ao Tailscale)"
fi

ufw --force enable

echo "==> [5/5] Concluido!"
TAILSCALE_IP="$(tailscale ip -4 | head -n1)"
echo ""
echo "VPS '${CLIENT_HOSTNAME}' pronta para receber deploys!"
echo "  IP Tailscale (privado): ${TAILSCALE_IP}"
echo ""
echo "Proximo passo no painel do Dokploy (Remote Servers -> Add Server):"
echo "  - Name: ${CLIENT_HOSTNAME}"
echo "  - IP Address: ${TAILSCALE_IP}"
echo "  - Username: root"
echo "  - Port: 22"
