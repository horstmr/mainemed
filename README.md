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
login e sem servidor: ditado pela Web Speech API do navegador, três consultas
fictícias de exemplo, prontuário em modo demonstração (gerado localmente,
sem IA) e, opcionalmente, geração real via API direto do navegador com uma
chave informada pelo usuário (recomende chave de um workspace com limite de
gasto). Para publicar: **Settings → Pages → Deploy from a branch → `main` /
(root)** — a página fica em `https://horstmr.github.io/mainemed/web/`.
Alternativa: baixar o arquivo e abrir localmente (o modo demonstração
funciona offline).

Diferença de privacidade honesta: o ditado da versão web passa pelo serviço
de voz do navegador; a transcrição 100% local é exclusividade do app de Mac.

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
