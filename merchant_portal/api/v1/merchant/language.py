import frappe
from merchant_portal.controller.maintenance_mode import maintenance_mode

@frappe.whitelist(methods=["POST"])
@maintenance_mode
def set_language(language):
    if language not in ("ar","en"):
        frappe.local.response["message"] = "Language  must be one of [en,ar]"
        frappe.throw("Language  must be one of [en,ar]")
    
   
    
    frappe.db.set_value("User",frappe.session.user,"language",language)
    
    frappe.clear_messages()
 
    frappe.local.response["data"] = "Success"
    return