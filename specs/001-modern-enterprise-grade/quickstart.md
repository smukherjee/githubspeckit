# Quickstart (Phase 1 Draft)

> Objective: Provide a minimal, repeatable path for a developer to clone, provision a local environment, lock deps, run quality gates, and seed baseline data consistent with the constitution.

## Prerequisites

- Python 3.13.x installed (validate with `python3 --version`)
- `uv` installed (`pip install uv` or follow upstream instructions)
- PostgreSQL 15+ accessible locally OR rely on ephemeral SQLite fallback (dev mode only)

## 1. Clone & Enter

```bash
git clone <repo-url> modern-backend
cd modern-backend
```

## 2. Create Virtual Environment (PEP 405) & Activate

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Dependency Lock (Deterministic)

```bash
uv pip install -r pyproject.toml --system --no-editable
uv lock
uv export -o requirements.txt
```

Rationale: `requirements.txt` is portability artifact; authoritative lock lives in `uv.lock`.

## 4. Tooling Sanity Gates (Fail Fast)

(Placeholders until implementation exists)

```bash
# Safety vulnerability scan
safety check -r requirements.txt || true  # Non-blocking early in draft

# Complexity & duplication (will be wired once src/ added)
# radon cc -s -n C src || exit 1
# jscpd --threshold 3 src || exit 1
```

## 5. Environment Configuration

Single descriptor (planned: `config/app.yaml`). For now create a minimal dev stub:

```bash
mkdir -p config
cat > config/app.yaml <<'YAML'
mode: dev
log_level: debug
database:
  driver: sqlite+aiosqlite
  dsn: sqlite:///./dev.db
security:
  password_policy:
    min_length: 12
    require_numbers: true
    require_symbols: true
seed:
  create_test_tenant: true
YAML
```

## 6. Database Migration & Seed (Placeholder)

Will use Alembic; placeholder commands (no-op until migrations exist):

```bash
# alembic upgrade head
# python -m app.seed --config config/app.yaml
```

## 7. Run Dev Server (Placeholder)

```bash
# uvicorn app.main:app --reload --port 8000
```

## 8. Smoke Verification (Contracts Existence)

Check contract fragments present:

```bash
ls specs/001-modern-enterprise-grade/contracts/
```

Expected: `openapi-base.yaml`, `openapi-auth-policy.yaml`, `openapi-observability.yaml`.

## 9. Next Steps

- Implement src/ adapters & domain per hexagonal structure.
- Wire auth (Argon2id hashing, python-jose JWT).
- Introduce policy evaluation engine skeleton (ALLOW/DENY/ABSTAIN tri-state).
- Add OpenTelemetry init & log redaction middleware.
- Add migration scripts & seed logic creating `TestTenant` + admin user.

## 10. Quality Gate Roadmap (Future Automation)

| Gate | Tool | Target | Enforced Phase |
|------|------|--------|----------------|
| Vulnerabilities | safety | 0 Critical/High | Before Phase 3 merge |
| Complexity | radon/xenon | Max B avg, C individual | Phase 2+ |
| Duplication | jscpd | <3% | Phase 2+ |
| Security Scan | (dyn. OWASP) | 0 High | Pre-release |
| Performance Baseline | custom event | <10% regression | Phase 3+ |

## 11. Troubleshooting

- If lock conflicts: remove `.venv`, re-run steps 2–3.
- If using Postgres: update `config/app.yaml` database driver to `postgresql+asyncpg` and provide DSN.

---

Draft status: Will be updated as Phase 2 introduces actual runnable modules.
