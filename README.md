# MaineMed

Documentação clínica para consultório: grava a consulta, transcreve
**localmente** com Whisper (MLX, GPU dos chips Apple M) e gera o prontuário
estruturado via API da Anthropic. O áudio nunca sai do Mac — só a transcrição
em texto é enviada na etapa de redação do prontuário, o que simplifica a
conversa de LGPD com clínicas.

**Download (Mac com chip Apple, M1+):**
[`MaineMed-macOS-arm64.zip`](https://github.com/horstmr/mainemed/releases/latest)
— passo a passo de instalação em [INSTALACAO-MAC.md](INSTALACAO-MAC.md).

## Arquitetura

| Etapa | Onde roda | Tecnologia |
|---|---|---|
| Gravação (16 kHz mono) | local | `sounddevice` (PortAudio) |
| Transcrição | local (GPU do chip M) | `mlx-whisper` — modelo baixado do Hugging Face na 1ª utilização, para `~/Library/Application Support/MaineMed/models` |
| Prontuário | API Anthropic | modelo `claude-opus-5` (configurável para `claude-sonnet-5`) |
| Exportação | local | `python-docx` / `reportlab` |

O áudio é passado ao Whisper como array numpy — **não há ffmpeg no bundle**.

Dados do usuário ficam em `~/Library/Application Support/MaineMed/`:
`config.json` (chave da API, permissão 600), `models/`, `logs/` e
`consultas/` — uma pasta por consulta com proveniência separada de máquina e
humano (`transcricao-original`, `transcricao-revisada`, `prontuario-gerado`,
`prontuario-final`, `consulta.json`); ver `src/mainemed/provenancia.py` e
[ROADMAP.md](ROADMAP.md).

## Versão web (MVP de demonstração)

[`web/index.html`](web/index.html) — página estática, arquivo único, sem
login e sem servidor:

- **Ditado** pela Web Speech API (Chrome/Edge/Safari), com bip de início/fim e
  medidor de nível; a página detecta Brave (remove o serviço de voz) e Firefox
  (não o implementa) e explica as alternativas (Windows+H, 🎤 do teclado);
- **Transcrição local experimental (Whisper)**: grava com MediaRecorder e
  transcreve no próprio navegador via transformers.js (`whisper-base`
  quantizado, WebGPU com fallback WASM) — funciona até em Brave/Firefox, sem
  chave e sem o áudio sair da máquina; o modelo (~80 MB) baixa na primeira
  utilização, com barra de progresso, e fica no cache;
- **Quatro fichas gineco-obstétricas fictícias** (retrato ilustrativo, ficha
  completa e consulta de exemplo);
- **Prontuário** em modo demonstração (local, sem IA) ou real via API direto
  do navegador com chave do usuário (recomende chave de workspace com limite
  de gasto);
- **Importação de documentos**: modo IA (foto/PDF via API) e OCR local
  experimental (Tesseract, ~15 MB sob demanda, imagem não sai do navegador).

Para publicar: **Settings → Pages → Deploy from a branch → `main` / (root)**
— a página fica em `https://horstmr.github.io/mainemed/web/`. Alternativa:
baixar o arquivo e abrir localmente (o modo demonstração funciona offline;
os modos com download de motor via CDN precisam de internet).

Diferença de privacidade honesta: o ditado nativo passa pelo serviço de voz
do navegador; o Whisper local do navegador e o do app de Mac processam tudo
na máquina.

## Desenvolvimento (em um Mac com chip M)

```sh
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python -m mainemed.main
```

## Build e distribuição (GitHub Actions)

O workflow [`build-macos.yml`](.github/workflows/build-macos.yml) roda num
runner `macos-15` (Apple Silicon), builda com PyInstaller, assina ad-hoc,
valida o bundle (`--selfcheck`), zipa com `ditto` e publica uma Release.

Dispara em push na `main`, por tag `mainemed-v*` ou manualmente na aba
**Actions → MaineMed macOS → Run workflow**.

### Por que essas escolhas de empacotamento

- **Runner macOS arm64 obrigatório** — PyInstaller não cross-compila.
- **`NSMicrophoneUsageDescription` no Info.plist** — sem a chave o macOS não
  pede permissão e o microfone grava silêncio, sem erro algum.
- **Assinatura ad-hoc, sem hardened runtime** — não há conta Apple Developer;
  o usuário passa uma vez pelo Gatekeeper (ver INSTALACAO-MAC.md).
- **`ditto -c -k --keepParent`** — zip comum destrói symlinks/assinatura do
  `.app` (o clássico "o aplicativo está danificado").
- **Modelos fora do bundle** — app assinado não pode escrever em si mesmo.
