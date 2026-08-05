# Contributing to LXL·QuantAxis

## Development Setup

```bash
git clone https://github.com/Ryhs666/LXL-QuantAxis.git
cd LXL-QuantAxis
pip install -r requirements.txt
pip install pytest ruff bandit  # dev dependencies
```

## Branch Strategy

- `main` — stable, release-ready
- `feat/<name>` — new features
- `fix/<name>` — bug fixes
- `docs/<name>` — documentation only

Work in feature branches. Open a PR to merge into `main`.

## Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(scope): description       # new feature
fix(scope): description        # bug fix
docs(scope): description       # documentation
refactor(scope): description   # code restructuring
test(scope): description       # tests only
```

Examples:
- `feat(research): add AI thesis extraction`
- `fix(backtest): resolve symbol for mark-to-market`
- `docs(readme): add architecture diagram`

## Testing

All PRs must pass the test suite:

```bash
pytest tests/ -q
```

Tests are organized by category:
- `tests/test_*.py` — unit tests
- `tests/backtest/` — backtest correctness
- `tests/security/` — auth and permissions
- `tests/contract/` — data provider interfaces
- `tests/characterization/` — legacy behavior preservation

Minimum: all existing tests must pass. New features require new tests.

## Code Style

- Python 3.12, 120-char line limit
- Follow existing patterns in the module you're modifying
- Use `ruff check` before committing
- Type hints encouraged but not enforced
- Use `get_logger(__name__)` from `src.lxl_quantaxis.core.logging`

## Architecture Rules

1. **New features → `src/lxl_quantaxis/`**: All new code goes into the V2 package
2. **No V2→V1 imports**: V2 modules must not depend on legacy `src/` modules
3. **No AI code execution**: Strategy rules must use the DSL, never `exec`/`eval`
4. **Immutable research records**: Research notes must be `frozen=True` dataclasses

## Security

- Never commit API keys, passwords, or JWT secrets
- Use environment variables for configuration (see `.env.example`)
- Report security issues privately, not in public issues

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
