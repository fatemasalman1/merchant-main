# Copyright (c) 2024, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VerificationCenter(Document):
    pass
    




@frappe.whitelist()
def get_verification_center_info(email):
    pass
    # merchant=frappe.db.exists("Merchant", {"email_address": email})
    # response_data=[]
    
    # if not merchant:
    #     return False,None
    
    # verification_centers=frappe.db.get_all("Verification Center",{"merchant":merchant,"status":"Not Responded"},pluck="name")
    
    # if not len(verification_centers):
    #     return False,
    # for v in verification_centers:
    #     data={}
    #     verification_center=frappe.get_doc("Verification Center",v)
    #     data["type"]="Dynamic"
    #     data_section=[]
    #     for data in verification_center.data_section:
    #         data_section.append({
    #             "field_name":data.field_name,
    #             "field_type":data.field_type,
    #             "value":data.value,
    #             "in_card":data.in_card,
    #             "button_type":data.button_type,
    #             "button_url":data.button_url
    #         })
            
            
    
        
