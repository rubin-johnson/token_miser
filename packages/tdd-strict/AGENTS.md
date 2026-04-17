# TDD Strict

You follow strict test-driven development. The test comes first. Always.

## Rules

- Never write implementation code without a failing test that demands it.
- The cycle is: write a failing test, run it to confirm it fails, write the minimum code to pass, run it to confirm it passes, refactor if needed.
- Each test should test one behavior. Name it after what it verifies, not what it calls.
- Run the test suite after every change. If tests break, fix them before proceeding.
- Do not write tests that test implementation details. Test behavior and outputs.
- Use fixtures and helpers to avoid duplicating test setup.
- 100% coverage of new code. If you can't test it, reconsider the design.
- When the task says "implement X", start by writing test_X that describes what X should do, then implement X.
- Keep tests fast. No network calls, no disk I/O beyond temp directories.
- If a test is hard to write, that's a design signal. Simplify the code under test.
