# Code Configuration

## Python

- Use pyenv for Python version management, uv for packages and virtual environments
- Never use: pip, pip-tools, poetry, pipenv, or venv module directly
- Package config goes in pyproject.toml; dependencies managed with `uv add`
- Run tests with `uv run pytest`

## Go

- Use `go mod` for module management; always commit `go.mod` and `go.sum`
- Run `go vet ./...` before `golangci-lint run`; both before committing
- Error handling: always check errors, wrap with `fmt.Errorf("context: %w", err)`

## Code Quality

- TDD: tests first, always
- 100% test coverage required; exceptions require an explicit comment explaining why
- No hardcoded returns, no over-mocking
- All code must read like a human wrote it — no excessive comments or over-engineered abstractions
- Don't add features beyond what was asked

## Architecture

- Simple > clever; smaller/cheaper solutions when possible
- Match existing project patterns; add only what is needed
- Follow the Rule of Three before abstracting
- Every interactive prompt must have a non-interactive bypass flag (e.g. `--yes`, `--force`)

## Commits

- Concise, imperative mood commit messages
- No AI co-author attribution
