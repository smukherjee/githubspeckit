# Quality Module

## Purpose

This module provides **build-time quality gates and code analysis tools** to ensure:
- Code complexity stays within constitutional limits (avg B, max C)
- Code duplication remains below threshold (<3%)
- Security vulnerabilities are detected (safety scans)

## Architecture Decision

The `quality/` module is a **development-time tooling module** that enforces code quality standards defined in the Constitution.

### Why Not in `tests/` or `scripts/`?

1. **Not Tests**: These are quality gates, not behavioral tests. They analyze code structure and patterns, not functionality.

2. **Not Scripts**: While similar to scripts, quality tools are **part of the codebase** and run in the CI pipeline as first-class checks.

3. **Importable Utilities**: Quality modules can be imported and used programmatically (e.g., in pre-commit hooks, IDE plugins, or CI workflows).

### Constitution Compliance (v1.5.1)

**Principle I (Modularity)**: ✅ Quality is a distinct module for code analysis

**Principle III (Quality Gates)**: ✅ This module implements constitution-defined quality thresholds:
- Complexity: Average B, Max C (Xenon)
- Duplication: <3% (jscpd)
- Security: Vulnerability scanning (safety)

**Principle IV (Testing Discipline)**: ✅ Quality gates complement testing by enforcing structural quality

## Module Structure

```
src/quality/
├── __init__.py              # Public API exports
├── complexity.py            # Cyclomatic complexity checks (Xenon wrapper)
├── duplication.py           # Code duplication detection (jscpd wrapper)
└── security.py              # Vulnerability scanning (safety wrapper)
```

## Usage Example

```python
from quality.complexity import check_complexity

# Run complexity check
violations = check_complexity("src/", avg_max="B", abs_max="C")
if violations:
    raise SystemExit(f"Complexity violations: {violations}")
```

## CI Integration

Quality gates run in CI before tests:

```yaml
- name: Quality Gates
  run: |
    python -m quality.complexity src/ --avg B --max C
    python -m quality.duplication --threshold 3
    python -m quality.security
```

## Related Documentation

- Constitution v1.5.1, Principle III (Quality Gates)
- quality_justifications.yaml (specific violation approvals)
