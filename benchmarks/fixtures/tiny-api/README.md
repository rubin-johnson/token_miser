# tiny-api fixture

A git-bundled FastAPI CRUD app used as a fixture for the token_miser benchmark suite.

## Contents

The bundle contains a small FastAPI app with in-memory storage, three endpoints
(`GET /items`, `GET /items/{id}`, `POST /items`), Pydantic models, and basic
pytest tests.

## Branches and tags

| Branch / Tag        | Description                                                              |
|---------------------|--------------------------------------------------------------------------|
| `main` / `v1.0`    | Clean, working app. Tests pass. No known bugs.                           |
| `buggy-pagination`  | Off-by-one in `database.list_items()` — each page returns one extra item (overlaps with the next page). Existing tests pass because they only check page 1 with few items. |
| `buggy-500`         | A `_compute_discount_tier()` helper divides by `price`, causing `ZeroDivisionError` when `price=0`. Existing tests pass because they use non-zero prices. |

## Benchmark tasks these support

- **Bug fix (pagination):** Write a failing test that exposes the off-by-one, then fix it.
- **Bug fix (500):** Diagnose why `POST /items` with `price=0` returns 500, add a guard or validation.
- **Refactoring:** Replace dict-based response builders in `schemas.py` with dataclasses or Pydantic models.
- **Test coverage:** Add edge-case tests (invalid input, not-found, pagination boundaries) — the happy-path-only test suite is intentional.

## Usage

```bash
git clone repo.bundle tiny-api
cd tiny-api
pip install -e .
python -m pytest tests/ -v
```

To work with a buggy branch:

```bash
git checkout buggy-pagination  # or buggy-500
```
