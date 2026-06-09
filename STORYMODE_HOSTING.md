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

[settings.tts]
voice_choice = "GoogleTranslate"
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

## Notas

- O texto da história default é inglês (gTTS en). Para PT-BR, ajustar a língua do gTTS /
  usar outro provider de voz.
- A mesma coerção `thread_post` string→lista vale para a fila (`--from-queue`) e payloads
  Devvit — `main._coerce_thread_post`.
- Caminho de screenshots (`storymodemethod=0` ou modo comentários) continua existindo e
  segue exigindo navegador + login; não use em hosting sem conta descartável.
