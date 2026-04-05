from pathlib import Path

from apps.knowledge_base.indexer import VaultIndexer
from apps.knowledge_base.linker import NotesLinker
from apps.knowledge_base.search import VaultSearch
from apps.knowledge_base.synthesizer import build_synthesis_prompt


def _create_vault(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "python-patterns.md").write_text(
        "# Python Patterns\n\n"
        "Use dataclasses for models. #python #patterns\n\n"
        "See also [[go-patterns]]"
    )
    (vault / "go-patterns.md").write_text(
        "# Go Patterns\n\n"
        "Use interfaces for abstraction. #go #patterns\n\n"
        "See also [[python-patterns]]"
    )
    (vault / "ai-notes.md").write_text(
        "# AI Notes\n\n"
        "Claude API uses messages format. #ai\n\n"
        "[[python-patterns]] are useful for AI apps."
    )
    return vault


def test_index_vault(tmp_path):
    vault = _create_vault(tmp_path)
    indexer = VaultIndexer(tmp_path / "index.db")
    stats = indexer.index_vault(vault)
    assert stats["indexed"] == 3
    assert stats["errors"] == 0


def test_index_vault_skip_unchanged(tmp_path):
    vault = _create_vault(tmp_path)
    indexer = VaultIndexer(tmp_path / "index.db")
    indexer.index_vault(vault)
    stats2 = indexer.index_vault(vault)
    assert stats2["skipped"] == 3
    assert stats2["indexed"] == 0


def test_search_notes(tmp_path):
    vault = _create_vault(tmp_path)
    indexer = VaultIndexer(tmp_path / "index.db")
    indexer.index_vault(vault)
    search = VaultSearch(tmp_path / "index.db")
    results = search.search("python")
    assert len(results) >= 1
    assert any("python" in r["title"].lower() for r in results)


def test_search_no_results(tmp_path):
    vault = _create_vault(tmp_path)
    indexer = VaultIndexer(tmp_path / "index.db")
    indexer.index_vault(vault)
    search = VaultSearch(tmp_path / "index.db")
    results = search.search("nonexistent_xyz_topic")
    assert len(results) == 0


def test_get_note(tmp_path):
    vault = _create_vault(tmp_path)
    indexer = VaultIndexer(tmp_path / "index.db")
    indexer.index_vault(vault)
    search = VaultSearch(tmp_path / "index.db")
    note = search.get_note(str(vault / "python-patterns.md"))
    assert note is not None
    assert note["title"] == "python-patterns"


def test_synthesis_prompt():
    notes = [
        {"title": "Python", "path": "python.md", "content": "Use dataclasses"},
        {"title": "Go", "path": "go.md", "content": "Use interfaces"},
    ]
    prompt = build_synthesis_prompt("What patterns should I use?", notes)
    assert "dataclasses" in prompt
    assert "interfaces" in prompt


def test_linker_find_related(tmp_path):
    vault = _create_vault(tmp_path)
    indexer = VaultIndexer(tmp_path / "index.db")
    indexer.index_vault(vault)
    linker = NotesLinker(tmp_path / "index.db")
    related = linker.find_related(str(vault / "python-patterns.md"))
    # Should find go-patterns or ai-notes as related
    assert isinstance(related, list)


def test_indexer_stats(tmp_path):
    vault = _create_vault(tmp_path)
    indexer = VaultIndexer(tmp_path / "index.db")
    indexer.index_vault(vault)
    stats = indexer.get_stats()
    assert stats["total_notes"] == 3
    assert stats["total_words"] > 0
