#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."

echo "→ Verificando login Cloudflare..."
npx wrangler whoami

echo "→ Instalando dependências..."
npm install

echo "→ Deploy (Worker + container Flask GUI)..."
npx wrangler deploy

echo ""
echo "Pronto. URL: https://redditmaker-studio.<seu-subdominio>.workers.dev"
