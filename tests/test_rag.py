from app.locales import load_locales
from app.rag import KnowledgeBase, load_chunks

LOCALES = load_locales()
PT = LOCALES["pt-BR"].knowledge_dir
EN = LOCALES["en"].knowledge_dir


def test_chunks_split_by_heading():
    headings = {c.heading for c in load_chunks(PT)}
    assert {"Horário de funcionamento", "Cancela", "Valor da consulta"} <= headings


def test_search_finds_relevant_chunk():
    kb = KnowledgeBase(PT)
    assert kb.search("quanto custa a consulta particular")[0].heading == "Valor da consulta"
    assert any(c.heading == "Endereço" for c in kb.search("qual o endereço"))


def test_english_knowledge_base():
    kb = KnowledgeBase(EN)
    assert kb.search("how much is a private appointment")[0].heading == "Appointment fee"
    assert any(c.heading == "Opening hours" for c in kb.search("what are your opening hours"))


def test_search_without_match_returns_empty():
    assert KnowledgeBase(PT).search("xyzzy") == []
