# Test Report

This report records the local prototype test run included with the artifact.

Command:

```text
python -m pytest
```

Environment:

```text
platform win32 -- Python 3.14.2
pytest-8.3.4
hypothesis-6.124.7
```

Result:

```text
collected 113 items
tests/test_pipeline.py: 46 passed
tests/test_typecheck.py: 53 passed
tests/test_verification.py: 14 passed
113 passed in 24.12s
```

The checked-in tests cover parser/transpiler pipeline snapshots, type-checking
behavior, and verification wrapper behavior. They are implementation
consistency tests, not a mechanized proof of translation correctness.
