# Contributing to Spotify Linker Bot

Thanks for taking the time to contribute! This guide keeps the workflow consistent and efficient for everyone working on the project.

## Code of Conduct

We expect all contributors to be respectful and collaborative. Harassment, discrimination, or disrespectful behaviour will not be tolerated.

## Getting Started

1. **Fork** the repository and clone your fork.
2. Add the original repository as an `upstream` remote so you can pull future updates:
   ```bash
   git remote add upstream https://github.com/FarhadKhakzad/spotify-linker.git
   ```
3. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/short-description
   ```

## Development Workflow

- Python 3.11+ and [Poetry](https://python-poetry.org/) are required.
- Install dependencies and set up the local environment:
   ```bash
   poetry install
   ```
   ```bash
   # macOS/Linux
   cp env.example .env
   # Windows PowerShell
   copy env.example .env
   ```
   > Fill in secrets locally; never commit `.env`.
- Keep commits focused and written in **English, present tense** (e.g. `Add Spotify client retries`).
- Use descriptive branch names following `feature/`, `fix/`, or `chore/` prefixes.

## Quality Gates

Before opening a pull request always run:

```bash
poetry run ruff check .
poetry run pytest
```

`pytest` is configured with coverage reporting—please keep coverage at 100 %. Add or update tests alongside code changes.

## Pull Request Checklist

- [ ] Rebase on top of the latest `main`.
- [ ] Provide a clear summary of changes in English (you may add Persian notes too).
- [ ] Include screenshots or logs for UX- or API-facing changes when relevant.
- [ ] Confirm that `ruff` and `pytest` complete successfully.
- [ ] Update documentation if behaviour or configuration changes (remember to touch both `README.md` and `README.fa.md` when applicable).

## Documentation & Localization

The project ships with English and Persian documentation. Whenever you modify user-facing docs, please keep both languages in sync. If a direct translation is not possible, add a short note highlighting the difference.

## Need Help?

Feel free to open a GitHub Discussion or issue describing the question. Tag it with a clear label so maintainers can triage quickly.

We appreciate your help in making Spotify Linker Bot better! 🙌
