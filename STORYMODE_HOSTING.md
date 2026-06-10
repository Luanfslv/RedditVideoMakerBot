# Story-mode hosting (sem Reddit API, sem navegador, sem login)

Modo de operação que **destrava a hospedagem**: renderiza vídeos só com a *história*
(título + texto), sem screenshots do Reddit. Resultado:

- **Sem Chromium / Playwright browser** — `storymodemethod=1` faz o render no PIL local
  (`utils/imagenarator.py`) e retorna antes de abrir navegador (`screenshot_downloader.py:62`).
- **Sem login no Reddit** — o login de navegador (e o risco de ban da conta) só existe no
  caminho de screenshots, que não roda neste modo.
- **Sem Reddit Data API / OAuth / app** — o texto entra por JSON local via `--from-text`,
  então não precisa de `client_id`/`client_secret` (que falharam no registro) nem de
  endpoints `.json` (que retornam HTTP 403 de IP de servidor em 2026).
- **Sem chave de TTS** — `voice_choice = "GoogleTranslate"` (gTTS) é grátis e sem auth.

Roda em qualquer container com Python 3.10–3.12 + `ffmpeg`. Dependências de navegador
podem ser puladas (`playwright install` não é necessário neste modo).

## Config (já aplicado em `config.toml`)

```toml
[settings]
storymode = true
storymodemethod = 1

[settings.background]
background_audio_volume = 0   # 0 = sem música de fundo (não baixa lofi do YouTube)

[settings.tts]
voice_choice = "googletranslate"   # minúsculo: precisa bater com options do template
```

### Por que o validador exige creds mesmo no story-mode

`check_toml` valida o `config.toml` inteiro no boot, ANTES de despachar `--from-text`.
Campo obrigatório vazio dispara `input()` → `EOFError` em headless. Por isso o story-mode
precisa de **placeholders** que passem na validação (nunca usados, sem PRAW):

```toml
[reddit.creds]
client_id = "storyhostplaceholder"            # 12–30 chars
client_secret = "storyhostplaceholdersecret00" # 20–40 chars
username = "storyhost"                          # 3–20 chars
password = "storyhostpass"                      # >= 8 chars
2fa = false
refresh_token = ""                              # precisa existir como chave
```

## Entrada: JSON local

`video_creation/data/story_sample.json`:

```json
{
  "id": "story-demo-001",
  "title": "Título do post",
  "text": "História completa em texto corrido. Cada frase vira uma cena.",
  "is_nsfw": false
}
```

Campos: `title` e `text` obrigatórios. `id` opcional (gera slug do título se faltar).
O `text` é fatiado em sentenças por `spacy` (`posttextparser`) — uma imagem + um áudio
por frase.

## Rodar

```bash
python main.py --from-text video_creation/data/story_sample.json
```

Saída em `results/`.

## Dependências mínimas pra hospedar

- `pip install -r requirements.txt` (ou ao menos: `gTTS`, `spacy`, `ffmpeg-python`,
  `moviepy`, `Pillow`, `rich`, `toml`, `playwright` — o pacote pip, sem baixar o browser).
- `python -m spacy download en_core_web_sm` (modelo de sentença; auto-baixa no 1º run).
- `ffmpeg` no PATH (o repo tenta instalar via `utils/ffmpeg_install.py`).
- Rede só para: gTTS (áudio) e download do vídeo/áudio de fundo (YouTube) — cacheável.

## Fundo (background)

Por padrão `download_background_video` baixa do YouTube via `yt_dlp` (minecraft, ~grande).
Para evitar isso em hosting/CI, coloque seu próprio arquivo no caminho exato esperado —
o download é pulado se o arquivo já existir:

```
assets/backgrounds/video/<credit>-<filename>     # ex.: bbswitzer-parkour.mp4
assets/backgrounds/audio/<credit>-<filename>     # só se background_audio_volume != 0
```

`<credit>` e `<filename>` vêm de `utils/background_videos.json` / `background_audios.json`.

## Compatibilidade de ffmpeg (corrigido)

- **Encoder**: era `h264_nvenc` (GPU NVIDIA) → trocado para `libx264` (CPU, universal).
  NVENC falha em Mac e na maioria dos servidores sem GPU NVIDIA.
- **drawtext**: o watermark de crédito usa o filtro `drawtext` (exige `libfreetype`).
  Agora é opcional (`final_video._ffmpeg_has_filter`) — se o ffmpeg não tiver, o render
  segue e só pula o watermark, em vez de morrer.

## Peso de dependências (corrigido)

`torch` + `transformers` (~2GB) eram importados no boot (via `ai_methods` no topo de
`subreddit.py`) mesmo sem usar AI sort. Agora são **lazy** (só no branch `ai_similarity`).
Hosting story-mode não precisa instalar torch/transformers.

## Notas

- O texto da história default é inglês (gTTS en). Para PT-BR, ajustar a língua do gTTS /
  usar outro provider de voz.
- A mesma coerção `thread_post` string→lista vale para a fila (`--from-queue`) e payloads
  Devvit — `main._coerce_thread_post`.
- Caminho de screenshots (`storymodemethod=0` ou modo comentários) continua existindo e
  segue exigindo navegador + login; não use em hosting sem conta descartável.

## Verificado

Render real concluído nesta máquina (macOS, ffmpeg 8.0.1, Python 3.11, sem
torch/transformers): `python main.py --from-text video_creation/data/story_sample.json`
→ `results/AskReddit/AITA for telling my brother the truth at dinner.mp4`
(1080×1920, h264+aac, 52s). Card de título + cards de frase + narração gTTS, tudo local.
