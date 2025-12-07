import requests

class ETRService:
    """
    Service to send fiscal receipts to Tremol S21/M23 via HTTP/JSON.
    """
    def __init__(self, payload, etr_url="http://localhost:8000/fiscal/receipt"):
        self.payload = payload
        self.etr_url = etr_url

    def send_receipt(self):
        """
        Sends the receipt to the ETR device and returns a response dict.
        """
        try:
            response = requests.post(self.etr_url, json=self.payload, timeout=10)
            response.raise_for_status()  # raise HTTPError for bad responses
            data = response.json()

            # Expected keys from Tremol: success, receipt_no, etr_serial
            return {
                "success": data.get("success", False),
                "receipt_no": data.get("receipt_no"),
                "etr_serial": data.get("etr_serial"),
                "raw": data
            }

        except requests.RequestException as e:
            # Network or request error
            return {
                "success": False,
                "error": str(e)
            }
