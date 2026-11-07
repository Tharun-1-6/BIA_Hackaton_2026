from unittest.mock import patch
from fastapi.testclient import TestClient

from bia_hackaton_2026.main import app
from bia_hackaton_2026.tests.mock_payloads import mock_audio_payload, mock_text_payload
from bia_hackaton_2026.whatsapp.config import CAREGIVER_WHATSAPP_NUMBER, get_caregiver_numbers

client = TestClient(app)


def test_health_check() -> None:
    """Verifies that GET /health returns status code 200 and healthy payload."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "sahayi-backend"}


def test_meta_webhook_handshake_verification() -> None:
    """Verifies that GET /webhooks/whatsapp handles Meta hub.challenge verification."""
    response = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "1158201444",
            "hub.verify_token": "sahayi_token_2026",
        },
    )
    assert response.status_code == 200
    assert response.text == "1158201444"


def test_meta_webhook_handshake_invalid_token() -> None:
    """Verifies that GET /webhooks/whatsapp rejects invalid token."""
    response = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "1158201444",
            "hub.verify_token": "wrong_token",
        },
    )
    assert response.status_code == 403


def test_whatsapp_webhook_standard_text() -> None:
    """Verifies that POST /webhooks/whatsapp handles standard text and dispatches REST reply."""
    payload = mock_text_payload(body="സുഖമാണോ? (How are you?)", sender="whatsapp:+919876543210")

    with patch("bia_hackaton_2026.whatsapp.webhook.send_whatsapp_message") as mock_send:
        response = client.post("/webhooks/whatsapp", data=payload)

        assert response.status_code == 200
        assert "application/xml" in response.headers.get("content-type", "")
        assert response.text == "<Response/>"
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        assert args[0] == "whatsapp:+919876543210"
        assert "Sahayi: സന്ദേശം ലഭിച്ചു" in args[1]


def test_whatsapp_webhook_initiate_sos() -> None:
    """Verifies that POST /webhooks/whatsapp triggers emergency response and alerts all caregivers."""
    payload = mock_text_payload(body="INITIATE SOS", sender="whatsapp:+919876543210")

    with patch("bia_hackaton_2026.whatsapp.webhook.send_whatsapp_message") as mock_send:
        response = client.post("/webhooks/whatsapp", data=payload)

        assert response.status_code == 200
        assert "application/xml" in response.headers.get("content-type", "")
        assert response.text == "<Response/>"

        # Should send 1 message to member, and 1 to each configured caregiver
        caregivers = get_caregiver_numbers()
        assert mock_send.call_count == 1 + len(caregivers)
        calls = mock_send.call_args_list

        member_call = calls[0][0]
        assert member_call[0] == "whatsapp:+919876543210"
        assert "Sahayi SOS:" in member_call[1]
        assert "അടിയന്തര സഹായം രേഖപ്പെടുത്തി" in member_call[1]

        alerted_recipients = [c[0][0] for c in calls[1:]]
        for cg in caregivers:
            expected = cg if cg.startswith("whatsapp:") else f"whatsapp:{cg}"
            assert expected in alerted_recipients
            cg_call = next(c for c in calls[1:] if c[0][0] == expected)
            assert "EMERGENCY ALERT" in cg_call[0][1]
            assert "+919876543210" in cg_call[0][1]


def test_whatsapp_webhook_sos_keyword() -> None:
    """Verifies that POST /webhooks/whatsapp handles 'SOS' keyword."""
    payload = mock_text_payload(body="SOS", sender="whatsapp:+919876543210")

    with patch("bia_hackaton_2026.whatsapp.webhook.send_whatsapp_message") as mock_send:
        response = client.post("/webhooks/whatsapp", data=payload)

        assert response.status_code == 200
        assert response.text == "<Response/>"
        caregivers = get_caregiver_numbers()
        assert mock_send.call_count == 1 + len(caregivers)
        member_call = mock_send.call_args_list[0][0]
        assert "Sahayi SOS:" in member_call[1]


def test_meta_webhook_incoming_sos_json() -> None:
    """Verifies that POST /webhooks/whatsapp processes Meta Cloud API incoming JSON message."""
    meta_json = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1844407913356808",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "917012649561",
                                    "id": "wamid.TEST_META_001",
                                    "type": "text",
                                    "text": {"body": "SOS"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    with patch("bia_hackaton_2026.whatsapp.webhook.send_whatsapp_message") as mock_send:
        response = client.post("/webhooks/whatsapp", json=meta_json)

        assert response.status_code == 200
        assert response.text == "EVENT_RECEIVED"

        # Member + All Caregivers alert
        caregivers = get_caregiver_numbers()
        assert mock_send.call_count == 1 + len(caregivers)
        calls = mock_send.call_args_list
        assert calls[0][0][0] == "+917012649561"
        assert "Sahayi SOS:" in calls[0][0][1]

        alerted_recipients = [c[0][0] for c in calls[1:]]
        for cg in caregivers:
            clean_cg = cg.replace("whatsapp:", "").replace("+", "").strip()
            assert any(clean_cg in r for r in alerted_recipients)
            cg_call = next(c for c in calls[1:] if clean_cg in c[0][0])
            assert "EMERGENCY ALERT" in cg_call[0][1]


def test_meta_webhook_caregiver_inbound() -> None:
    """Verifies that Caregiver messaging the bot receives portal connection greeting."""
    meta_json = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1844407913356808",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "917736246747",
                                    "id": "wamid.TEST_CAREGIVER_001",
                                    "type": "text",
                                    "text": {"body": "Hi"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    with patch("bia_hackaton_2026.whatsapp.webhook.send_whatsapp_message") as mock_send:
        response = client.post("/webhooks/whatsapp", json=meta_json)
        assert response.status_code == 200
        assert response.text == "EVENT_RECEIVED"
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        assert args[0] == "+917736246747"
        assert "Sahayi Caregiver Portal Connected" in args[1]


def test_meta_webhook_secondary_caregiver_inbound() -> None:
    """Verifies that secondary Caregiver messaging the bot also receives portal connection greeting."""
    meta_json = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1844407913356808",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "919746654062",
                                    "id": "wamid.TEST_CAREGIVER_002",
                                    "type": "text",
                                    "text": {"body": "Hi from caregiver 2"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    with patch("bia_hackaton_2026.whatsapp.webhook.send_whatsapp_message") as mock_send:
        response = client.post("/webhooks/whatsapp", json=meta_json)
        assert response.status_code == 200
        assert response.text == "EVENT_RECEIVED"
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        assert args[0] == "+919746654062"
        assert "Sahayi Caregiver Portal Connected" in args[1]


def test_meta_webhook_ai_agent_text_integration() -> None:
    """Verifies that non-SOS text messages are processed through the AI agent pipeline."""
    meta_json = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1844407913356808",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "917012649561",
                                    "id": "wamid.TEST_AI_001",
                                    "type": "text",
                                    "text": {"body": "സുഖമാണോ? (How are you?)"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    with patch("bia_hackaton_2026.agent.runner.send_message") as mock_send:
        response = client.post("/webhooks/whatsapp", json=meta_json)
        assert response.status_code == 200
        assert response.text == "EVENT_RECEIVED"
        mock_send.assert_called()


def test_meta_webhook_ai_agent_voice_integration(tmp_path) -> None:
    """Verifies that incoming WhatsApp audio (.ogg) is transcribed via STT and processed by AI agent."""
    dummy_audio = tmp_path / "test.ogg"
    dummy_audio.write_bytes(b"dummy audio content")

    meta_audio_json = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1844407913356808",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "917012649561",
                                    "id": "wamid.TEST_AUDIO_001",
                                    "type": "audio",
                                    "audio": {"id": "1234567890", "mime_type": "audio/ogg"},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    with patch(
        "bia_hackaton_2026.whatsapp.webhook.download_meta_audio",
        return_value=str(dummy_audio),
    ), patch(
        "bia_hackaton_2026.stt.detect.detect_and_transcribe",
        return_value={"text": "എനിക്ക് നെഞ്ചുവേദന എടുക്കുന്നു", "language": "ml"},
    ), patch(
        "bia_hackaton_2026.agent.runner.send_message"
    ) as mock_agent_send:
        response = client.post("/webhooks/whatsapp", json=meta_audio_json)
        assert response.status_code == 200
        assert response.text == "EVENT_RECEIVED"
        mock_agent_send.assert_called()


def test_whatsapp_webhook_audio_attachment() -> None:
    """Verifies that POST /webhooks/whatsapp handles audio attachment and calls download_audio_media."""
    payload = mock_audio_payload(
        sender="whatsapp:+919876543210",
        media_url="https://api.twilio.com/mock-audio-file",
        content_type="audio/ogg",
        message_sid="MM999888777",
    )

    with patch(
        "bia_hackaton_2026.whatsapp.webhook.download_audio_media",
        return_value="/tmp/sahayi_audio/MM999888777.ogg",
    ) as mock_download, patch(
        "bia_hackaton_2026.whatsapp.webhook.send_whatsapp_message"
    ) as mock_send:
        response = client.post("/webhooks/whatsapp", data=payload)

        assert response.status_code == 200
        assert "application/xml" in response.headers.get("content-type", "")
        assert response.text == "<Response/>"
        mock_download.assert_called_once_with(
            "https://api.twilio.com/mock-audio-file",
            "MM999888777",
        )
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        assert "വോയ്സ് സന്ദേശം ലഭിച്ചു" in args[1]
