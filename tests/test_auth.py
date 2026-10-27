from app.auth import Policies

POLICIES = Policies(
    {
        "roles": {"guest": {"tools": ["search_knowledge"]}, "resident": {"tools": ["search_knowledge", "open_gate"]}},
        "default_role": "guest",
        "callers": {"5511999990002": "resident"},
    }
)


def test_known_caller_gets_role_tools_with_or_without_plus():
    assert POLICIES.can_call("5511999990002", "open_gate")
    assert POLICIES.can_call("+5511999990002", "open_gate")


def test_unknown_caller_falls_back_to_default_role():
    assert POLICIES.role_of("5500000000000") == "guest"
    assert not POLICIES.can_call("5500000000000", "open_gate")


def test_unlisted_tool_is_denied():
    assert not POLICIES.can_call("5511999990002", "schedule_appointment")


def test_shipped_policies_file_loads():
    p = Policies.load()
    assert "search_knowledge" in p.allowed_tools("qualquer")
