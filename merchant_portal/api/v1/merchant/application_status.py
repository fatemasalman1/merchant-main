import frappe
from merchant_portal.merchant_portal.doctype.registration_questionnaire.registration_questionnaire import get_application_status
from merchant_portal.controller.maintenance_mode import maintenance_mode


@frappe.whitelist(methods=["GET"])
@maintenance_mode
def application_status():
    
    data= get_application_status(frappe.session.user)
    frappe.clear_messages()
    frappe.local.response["data"] = data
    return