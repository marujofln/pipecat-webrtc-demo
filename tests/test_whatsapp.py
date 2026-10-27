import hashlib
import hmac

from app.whatsapp import parse_call_events, verify_signature

CONNECT = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "changes": [
                {
                    "field": "calls",
                    "value": {
                        "calls": [
                            {
                                "id": "wacid.ABC",
                                "from": "5511999990002",
                                "to": "5511888880000",
                                "event": "connect",
                                "session": {"sdp_type": "offer", "sdp": "v=0..."},
                            }
                        ]
                    },
                }
            ]
        }
    ],
}


def test_parse_connect_event():
    [e] = parse_call_events(CONNECT)
    assert (e.call_id, e.event, e.caller, e.sdp_type, e.sdp) == ("wacid.ABC", "connect", "5511999990002", "offer", "v=0...")


def test_ignores_non_call_fields():
    assert parse_call_events({"entry": [{"changes": [{"field": "messages", "value": {}}]}]}) == []


def test_signature():
    body = b'{"a":1}'
    sig = "sha256=" + hmac.new(b"segredo", body, hashlib.sha256).hexdigest()
    assert verify_signature(body, sig, "segredo")
    assert not verify_signature(body, "sha256=errado", "segredo")
    assert not verify_signature(body, None, "segredo")
