# RedditMaker Studio — app Devvit

Envia threads do Reddit para a fila do Studio (`/api/devvit/ingest`). O render continua na sua máquina com `python main.py --from-queue`.

## Pré-requisitos

1. Conta em [developers.reddit.com](https://developers.reddit.com)
2. `STUDIO_INGEST_SECRET` configurado no Studio (Wrangler / `.env`)
3. Migration Supabase `studio_render_queue` aplicada

## Instalação

```bash
cd devvit
npm install
```

Crie o app no portal Reddit (ou use o link `npm create devvit@latest` que o painel fornece).

## Configuração do app (no subreddit)

Nas configurações do app instalado:

| Campo | Valor |
|--------|--------|
| **studioUrl** | `https://redditmaker-studio.tech-760.workers.dev` |
| **ingestSecret** | Mesmo valor de `STUDIO_INGEST_SECRET` no servidor |

Em `devvit.json`, o domínio do Studio já está na allow-list HTTP. Para outro host, adicione em `permissions.http.domains`.

## Uso

1. Instale o app em um subreddit de teste
2. Abra um post → menu **⋯** → **Enviar para RedditMaker Studio**
3. Confira a fila em [Fila de render](/queue) no Studio
4. Na máquina com FFmpeg:

```bash
python main.py --from-queue
```

## Playtest local

```bash
npm run dev
```

## Domínio local

Para testar contra `http://127.0.0.1:4000`, use ngrok ou adicione o túnel em `devvit.json` → `permissions.http.domains` (Devvit exige HTTPS na produção).
