from app.auth import Policies

POLICIES = Policies(
    {
        "roles": {"guest": {"tools": ["search_knowledge"]}, "patient": {"tools": ["search_knowledge", "list_available_slots", "schedule_appointment"]}},
        "default_role": "guest",
        "callers": {"5511999990001": "patient"},
    }
)


def test_known_caller_gets_role_tools_with_or_without_plus():
    assert POLICIES.can_call("5511999990001", "schedule_appointment")
    assert POLICIES.can_call("+5511999990001", "schedule_appointment")


def test_unknown_caller_falls_back_to_default_role():
    assert POLICIES.role_of("5500000000000") == "guest"
    assert not POLICIES.can_call("5500000000000", "schedule_appointment")


def test_unlisted_tool_is_denied():
    assert not POLICIES.can_call("5511999990001", "delete_patient")


def test_caller_entry_with_role_and_language():
    p = Policies({"roles": {"patient": {"tools": ["x"]}}, "callers": {"551100": {"role": "patient", "language": "en"}}})
    assert p.role_of("551100") == "patient"
    assert p.language_of("551100") == "en"
    assert p.can_call("551100", "x")


def test_shipped_policies_file_loads():
    p = Policies.load()
    assert "search_knowledge" in p.allowed_tools("qualquer")
    assert p.language_of("5511999990003") == "en"
    assert p.language_of("5511999990001") == "pt-BR"
