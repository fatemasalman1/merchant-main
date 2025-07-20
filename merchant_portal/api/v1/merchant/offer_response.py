import frappe
from merchant_portal.merchant_portal.doctype.merchant_offer.merchant_offer import merchant_offer_response
from merchant_portal.controller.maintenance_mode import maintenance_mode


@frappe.whitelist(methods=["POST"])
@maintenance_mode
def get_offers_response(merchant,offer_id,status,reason=None,feedback=None,id=None):
    
    if status not in ["Decline","Accept"]:
        frappe.local.response["message"] = "Offer status must be one of [Decline,Accept]"
        frappe.throw("Offer status must be one of [Decline,Accept]")

    if status == "Decline" and not reason:
        frappe.local.response["message"] = "Please set reason for decline status"
        frappe.throw("Please set reason for decline status")
    if status== "Accept" and  not id:
        frappe.local.response["message"] = "Please set selection id"
        frappe.throw("Please set selection id")
        
    response=merchant_offer_response(merchant,offer_id,status,reason,feedback,id)
    
    frappe.clear_messages()
 
    frappe.local.response["data"] = response
    return