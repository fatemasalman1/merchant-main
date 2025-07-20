# Copyright (c) 2025, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MerchantPaymentRequest(Document):
    
     def on_trash(self):
         frappe.db.set_value("Sales Invoice", self.sales_invoice, "custom_payment_request_sent", 0)
