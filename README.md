# Spotify Linker Bot

[![CI](https://github.com/FarhadKhakzad/spotify-linker/actions/workflows/ci.yml/badge.svg)](https://github.com/FarhadKhakzad/spotify-linker/actions/workflows/ci.yml)

> Available in: [English](README.md) · [فارسی](README.fa.md)

Spotify Linker Bot keeps a Telegram channel in sync with Spotify by detecting track mentions and replying with the matching Spotify link. The project is being built step-by-step with production-friendly tooling.

## Key Capabilities

- FastAPI application that exposes a Telegram webhook endpoint.
- Spotify Web API client that performs robust track searches.
- Configuration layer powered by Pydantic Settings with dotenv support.
- Comprehensive automated tests (async-friendly, 100% coverage) and CI via GitHub Actions.

## Quick Start

### Requirements

- Python 3.11 or newer
- [Poetry](https://python-poetry.org/) for dependency management *(or `pip` with `requirements.txt` for a minimal setup)*

### Installation

```bash
poetry install
cp env.example .env  # fill in the secrets afterwards
```

> Prefer English copy? Use `.env.template`, which mirrors the same keys with English descriptions. Both files are interchangeable—pick whichever language you prefer.

<details>
<summary>Prefer pip over Poetry?</summary>

```bash
python -m venv .venv
.venv\Scripts\activate  # on Windows
source .venv/bin/activate  # on macOS/Linux
pip install -r requirements.txt
# optional: pip install -r requirements-dev.txt  # tooling like pytest & ruff
cp env.example .env
# (alternatively) cp .env.template .env
```

</details>

### Local Development

```bash
poetry run uvicorn spotify_linker.main:app --reload
```

<details>
<summary>Running without Poetry</summary>

```bash
uvicorn spotify_linker.main:app --reload
```

</details>

### Quality Gates

```bash
poetry run ruff check .
poetry run pylint src tests
poetry run pytest
```

<details>
<summary>Commands without Poetry</summary>

```bash
# make sure requirements-dev.txt (or equivalent tools) is installed
ruff check .
pylint src tests
pytest
```

</details>

`pytest` is configured to emit coverage statistics so you can keep the 100 % target in sight.

## Configuration Reference

Copy `env.example` (or `.env.template`) to `.env` and set the following variables:

| Variable | Required | Description |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token issued by BotFather. |
| `TELEGRAM_CHANNEL_ID` | ✅ | Numeric channel identifier (negative for channels). |
| `SPOTIFY_CLIENT_ID` | ✅ | Application client ID from the Spotify Developer Dashboard. |
| `SPOTIFY_CLIENT_SECRET` | ✅ | Client secret used during the client-credentials flow. |
| `SPOTIFY_REDIRECT_URI` | ➖ | Reserved for future OAuth scenarios. |

> **Security tip:** never commit `.env` or real credentials. Use password managers or your hosting platform’s secret store.

## Roadmap

1. ✅ Project scaffolding, settings management, CI + linting.
2. ✅ Telegram webhook endpoint and logging.
3. ✅ Spotify client with client-credentials token handling.
4. ✅ Parsing Telegram messages into normalized track candidates.
5. ✅ High-fidelity Spotify search and response formatting.
6. ⏭ Deployment automation and HTTPS webhook configuration.

## Contributing

We welcome contributions! Please read the full workflow in [CONTRIBUTING.md](CONTRIBUTING.md). It covers branching, quality checks, commit style, and the bilingual documentation policy.

For Persian-speaking contributors a localized quick reference is available in [README.fa.md](README.fa.md).

## License

This project is released under the MIT License. See [`LICENSE`](LICENSE) for details.
