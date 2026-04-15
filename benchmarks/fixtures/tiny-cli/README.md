# tiny-cli fixture

A small Python CLI project used as a git-bundle fixture for the token_miser
benchmark suite.

## Contents

`repo.bundle` is a git bundle containing:

| Branch / Tag          | Description                                        |
|-----------------------|----------------------------------------------------|
| `main` (tag `v1.0`)  | Clean, working project. 21 tests pass, CLI works.  |
| `buggy-import-cycle`  | Circular import between `utils.py` and `commands/count.py`. Any CLI invocation fails with `ImportError`. |

## Project layout (on main)

```
tiny-cli/
  pyproject.toml              # hatchling, entry point: tiny = tiny_cli.__main__:main
  src/tiny_cli/
    __init__.py               # __version__ = "0.1.0"
    __main__.py               # argparse CLI — intentionally monolithic (~115 lines)
    commands/
      count.py                # counts lines in .py files in a directory
      greet.py                # prints "Hello, {name}!" with optional --shout
    utils.py                  # truncate_string, pluralize, format_table, read_lines, is_python_file
  tests/
    test_commands.py          # tests for count and greet
    test_utils.py             # tests for truncate_string, pluralize, is_python_file only
```

## Benchmark tasks this fixture supports

1. **Write tests** -- `read_lines` and `format_table` in `utils.py` have zero test coverage.
2. **Extract function / refactor** -- `__main__.py:main()` is a god-method with inline validation, argument parsing, and dispatch all in one function.
3. **Fix bug** -- The `buggy-import-cycle` branch has a circular import that must be diagnosed and resolved.
4. **Add feature** -- Extend the CLI with a new subcommand or flag (open-ended).

## Usage

```bash
# Clone from the bundle
git clone repo.bundle tiny-cli && cd tiny-cli

# Run tests
PYTHONPATH=src python -m pytest tests/ -v

# Run the CLI
PYTHONPATH=src python -m tiny_cli count .
PYTHONPATH=src python -m tiny_cli greet World --shout

# Switch to the buggy branch
git checkout buggy-import-cycle
PYTHONPATH=src python -m tiny_cli greet World   # ImportError
```
