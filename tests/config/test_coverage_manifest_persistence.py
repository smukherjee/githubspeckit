"""
TEST-DB-13A: Validate coverage manifest includes persistence adapters.

Validates:
- coverage_critical_paths.yml includes persistence repository patterns (IMPL-DB-13)
- Alembic env.py included in critical paths
- Seed scripts included in manifest
- Version incremented to 2
- last_updated reflects Phase 3 changes

Status: Phase 3 Lane DB-F
Dependencies: IMPL-DB-13 (coverage manifest update)
"""
from __future__ import annotations

import pytest
import yaml
from pathlib import Path


def test_coverage_manifest_includes_persistence_category():
    """
    Test coverage manifest includes persistence-adapters category (IMPL-DB-13).
    
    Validates:
    - New persistence-adapters category exists
    - Includes repositories.py and models.py patterns
    - Rationale references FR-002, FR-018
    """
    manifest_path = Path(__file__).parent.parent.parent / "coverage_critical_paths.yml"
    
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    # Find persistence-adapters category
    persistence_category = None
    for category in manifest["categories"]:
        if category["name"] == "persistence-adapters":
            persistence_category = category
            break
    
    assert persistence_category is not None, "persistence-adapters category missing from manifest"
    
    # Validate rationale mentions tenant isolation and soft delete
    rationale = persistence_category["rationale"]
    assert "tenant isolation" in rationale.lower() or "multi-tenancy" in rationale.lower()
    assert "FR-002" in rationale or "FR-018" in rationale
    
    # Validate patterns include repositories and models
    patterns = persistence_category["patterns"]
    assert "adapters/persistence/repositories.py" in patterns, "repositories.py missing from patterns"
    assert "adapters/persistence/models.py" in patterns, "models.py missing from patterns"


def test_coverage_manifest_includes_migration_environment():
    """
    Test coverage manifest includes alembic/env.py (IMPL-DB-13).
    
    Validates:
    - database-migrations category exists
    - Includes alembic/env.py pattern
    - Rationale references FR-015, FR-052
    """
    manifest_path = Path(__file__).parent.parent.parent / "coverage_critical_paths.yml"
    
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    # Find database-migrations category
    migrations_category = None
    for category in manifest["categories"]:
        if category["name"] == "database-migrations":
            migrations_category = category
            break
    
    assert migrations_category is not None, "database-migrations category missing from manifest"
    
    # Validate rationale mentions schema changes and integrity
    rationale = migrations_category["rationale"]
    assert "migration" in rationale.lower() or "schema" in rationale.lower()
    assert "FR-015" in rationale or "FR-052" in rationale
    
    # Validate patterns include alembic/env.py
    patterns = migrations_category["patterns"]
    assert "alembic/env.py" in patterns, "alembic/env.py missing from patterns"


def test_coverage_manifest_includes_seed_scripts():
    """
    Test coverage manifest includes both in-memory and DB seed scripts (IMPL-DB-13).
    
    Validates:
    - seed-bootstrap category updated
    - Includes cli/bootstrap.py (in-memory seed)
    - Includes cli/db_bootstrap.py (durable seed)
    """
    manifest_path = Path(__file__).parent.parent.parent / "coverage_critical_paths.yml"
    
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    # Find seed-bootstrap category
    seed_category = None
    for category in manifest["categories"]:
        if category["name"] == "seed-bootstrap":
            seed_category = category
            break
    
    assert seed_category is not None, "seed-bootstrap category missing from manifest"
    
    # Validate patterns include both seed implementations
    patterns = seed_category["patterns"]
    assert "cli/bootstrap.py" in patterns, "cli/bootstrap.py missing from patterns"
    assert "cli/db_bootstrap.py" in patterns, "cli/db_bootstrap.py missing from patterns"
    
    # Validate notes mention durable DB seed
    notes = seed_category["notes"]
    assert "durable" in notes.lower() or "db" in notes.lower()


def test_coverage_manifest_version_incremented():
    """
    Test coverage manifest version incremented for Phase 3 changes (IMPL-DB-13).
    
    Validates:
    - Version is 2 (incremented from 1)
    - last_updated is 2025-10-05 (Phase 3 completion date)
    """
    import datetime
    
    manifest_path = Path(__file__).parent.parent.parent / "coverage_critical_paths.yml"
    
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    # Validate version incremented
    assert manifest["version"] == 2, "Manifest version should be 2 after Phase 3 updates"
    
    # Validate last_updated is recent (Phase 3 timeframe)
    # YAML parser converts ISO date to datetime.date object
    expected_date = datetime.date(2025, 10, 5)
    assert manifest["last_updated"] == expected_date, "last_updated should reflect Phase 3 completion"


def test_coverage_manifest_all_persistence_files_covered():
    """
    Test all critical persistence files are covered by patterns (IMPL-DB-13).
    
    Validates comprehensive coverage of persistence layer.
    """
    manifest_path = Path(__file__).parent.parent.parent / "coverage_critical_paths.yml"
    
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    # Extract all patterns from all categories
    all_patterns = []
    for category in manifest["categories"]:
        all_patterns.extend(category["patterns"])
    
    # Critical persistence files that must be covered
    critical_files = [
        "adapters/persistence/repositories.py",
        "adapters/persistence/models.py",
        "alembic/env.py",
        "cli/bootstrap.py",
        "cli/db_bootstrap.py",
    ]
    
    for critical_file in critical_files:
        # Check if any pattern matches this file
        matched = any(
            critical_file == pattern or
            critical_file.startswith(pattern.rstrip("*"))
            for pattern in all_patterns
        )
        assert matched, f"Critical file {critical_file} not covered by any pattern in manifest"


def test_coverage_manifest_structure_valid():
    """
    Test coverage manifest has valid YAML structure (IMPL-DB-13).
    
    Validates:
    - Valid YAML syntax
    - Required top-level fields present
    - All categories have required fields
    """
    manifest_path = Path(__file__).parent.parent.parent / "coverage_critical_paths.yml"
    
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    # Validate top-level structure
    assert "version" in manifest
    assert "last_updated" in manifest
    assert "owner" in manifest
    assert "categories" in manifest
    
    # Validate each category has required fields
    for category in manifest["categories"]:
        assert "name" in category, f"Category missing name: {category}"
        assert "rationale" in category, f"Category {category.get('name')} missing rationale"
        assert "patterns" in category, f"Category {category.get('name')} missing patterns"
        assert isinstance(category["patterns"], list), f"Category {category.get('name')} patterns not a list"
        assert len(category["patterns"]) > 0, f"Category {category.get('name')} has no patterns"
