import frappe
from frappe.utils.password import update_password
from merchant_portal.utils import validate_login_user
from merchant_portal.controller.language_decorator import set_language_from_header
from merchant_portal.controller.maintenance_mode import maintenance_mode
@frappe.whitelist(methods=["POST"])
@maintenance_mode
@set_language_from_header
def change_password(email,pwd):
        # validate_login_user(email)
        user=frappe.get_doc("User", email)
        user.check_permission("read")
        update_password(user=user.name,pwd=pwd,logout_all_sessions=True)
        frappe.db.set_value("User",email,"custom_allow_new_password",0)
        frappe.local.response["message"] = frappe._("Password change successfully")
        return 
