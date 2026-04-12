from __future__ import annotations

import ast
from pathlib import Path

MAX_ALEMBIC_VERSION_LENGTH = 32


def _load_revision_id(path: Path) -> str:
    module = ast.parse(path.read_text(), filename=str(path))
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "revision":
                value = node.value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    return value.value
                raise AssertionError(f"{path} has a non-string Alembic revision id")
    raise AssertionError(f"{path} is missing an Alembic revision id")


def test_alembic_revision_ids_fit_version_table_limit() -> None:
    versions_dir = Path(__file__).resolve().parents[1] / "alembic" / "versions"

    for path in sorted(versions_dir.glob("*.py")):
        revision_id = _load_revision_id(path)
        assert len(revision_id) <= MAX_ALEMBIC_VERSION_LENGTH, (
            f"{path.name} revision id {revision_id!r} exceeds {MAX_ALEMBIC_VERSION_LENGTH} characters"
        )
