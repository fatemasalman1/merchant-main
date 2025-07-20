# your_app/your_app/doctype/api_tester/api_tester.py
import frappe, requests, json
from frappe.model.document import Document

class APITester(Document):
    @frappe.whitelist()
    def run_test(self):
        # parse headers & payload (or default to empty dict)
        try:
            headers = json.loads(self.headers_json or "{}")
        except Exception as e:
            frappe.throw(f"Invalid JSON in Headers: {e}")

        try:
            payload = json.loads(self.payload_json or "{}")
        except Exception as e:
            frappe.throw(f"Invalid JSON in Payload: {e}")

        # send the request
        resp = requests.request(
            method=self.method,
            url=self.url,
            headers=headers,
            json=payload
        )

        # save and return the raw text
        frappe.db.set_value(self.doctype, self.name, "response_body", resp.text)
        return resp.text
