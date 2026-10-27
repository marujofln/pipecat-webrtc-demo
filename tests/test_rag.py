from app.rag import KnowledgeBase, load_chunks


def test_chunks_split_by_heading():
    headings = {c.heading for c in load_chunks()}
    assert {"Horário de funcionamento", "Cancela", "Valor da consulta"} <= headings


def test_search_finds_relevant_chunk():
    kb = KnowledgeBase()
    assert kb.search("quanto custa a consulta particular")[0].heading == "Valor da consulta"
    assert any(c.heading == "Endereço" for c in kb.search("qual o endereço"))


def test_search_without_match_returns_empty():
    assert KnowledgeBase().search("xyzzy") == []
