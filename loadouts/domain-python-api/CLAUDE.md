# Python API Project

## Framework Patterns
- Flask: use app factory pattern, blueprints for routes, `flask.g` for request-scoped state
- FastAPI: use dependency injection, Pydantic models for request/response, async where beneficial
- Return 422 for validation errors, 404 for missing resources, 409 for conflicts — never 500 for expected conditions
- Use proper HTTP status codes: 201 for creation, 204 for deletion, 200 for everything else

## Database
- SQLAlchemy: use the session pattern from the existing codebase (check for `db.session`, `get_db()`, or similar)
- Parameterized queries only — never string-format SQL
- Migrations: match existing tool (alembic, flask-migrate, or raw SQL)

## Testing
- Use pytest with the project's existing fixtures (check conftest.py first)
- Test client: `app.test_client()` for Flask, `TestClient(app)` for FastAPI
- Test the HTTP interface, not internal functions — assert status codes and response bodies
- Seed test data in fixtures, not inline
- Cover: happy path, validation errors (422), not-found (404), edge cases

## Code Style
- Type hints on function signatures
- No docstrings on obvious functions — only on non-trivial business logic
- Imports: stdlib, third-party, local (isort order)
- Match existing patterns in the codebase before inventing new ones

## Efficiency
- grep for route decorators (`@app.route`, `@router`) to find endpoints
- grep for model definitions before writing queries
- Read conftest.py before writing tests
- One endpoint or one test file per edit — don't batch unrelated changes
