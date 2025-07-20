import frappe
from frappe.sessions import clear_sessions
from merchant_portal.controller.language_decorator import set_language_from_header
from merchant_portal.controller.maintenance_mode import maintenance_mode

@frappe.whitelist(methods=["POST"])
@maintenance_mode
@set_language_from_header
def logout():
    user = frappe.session.user
    clear_sessions(user=user, keep_current=False, force=True)
    frappe.set_user("Administrator") 
    api_credentials = generate_keys(user)
    frappe.set_user("Guest")  
    frappe.local.response["message"] = frappe._("Logged out successfully")
    return

@frappe.whitelist()
@maintenance_mode
def generate_keys(user: str):

    user_details = frappe.get_doc("User", user)
    api_key = frappe.generate_hash(length=15)
    api_secret = frappe.generate_hash(length=15)
    user_details.api_key = api_key
    user_details.api_secret = api_secret
    user_details.save(ignore_permissions=True)  
    frappe.db.commit()
    
    
