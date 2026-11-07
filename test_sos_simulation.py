import requests

def test_meta_sos_pipeline():
    url = "http://127.0.0.1:8000/webhooks/whatsapp"
    
    # Meta Cloud API JSON format for incoming WhatsApp SOS
    meta_payload = {
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
                                    "id": "wamid.SIMULATED_SOS_001",
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

    print("\n--- Sending simulated SOS from Elder (+91 7012649561) to Meta Webhook ---")
    try:
        response = requests.post(url, json=meta_payload)
        print(f"Server Response Code: {response.status_code}")
        print(f"Server Response Text: {response.text}")
        print("\nCheck your uvicorn terminal to see the live outbound Meta messages!")
    except Exception as e:
        print(f"Error connecting to local server: {e}")
        print("Make sure you started your server: uv run uvicorn bia_hackaton_2026.main:app --port 8000")

if __name__ == "__main__":
    test_meta_sos_pipeline()
