# Copyright (c) 2025, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from merchant_portal.controller.integration import create_integration_task

class MerchantID(Document):
    
     def before_insert(self):
        type="RegisterMerchant"
        registed=frappe.db.get_value("Merchant",self.merchant,"registed")
        
        if registed:
            type="AddMid"
            
        create_integration_task(type,self.commercial_register,self.doctype,self.name,self.merchant)
        