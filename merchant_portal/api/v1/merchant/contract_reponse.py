import frappe

from merchant_portal.controller.maintenance_mode import maintenance_mode
from merchant_portal.merchant_portal.doctype.merchant_contract.merchant_contract import (
    merchant_contract_response, merchant_issue_contract_response)


@frappe.whitelist(methods=["POST"])
@maintenance_mode
def get_contract_response(contract_id,contract_document_id,status,reason=None,feedback=None):
  
    if status not in ["Decline","Accept"]:
        frappe.local.response["message"] = "Offer status must be one of [Decline,Accept]"
        frappe.throw("Offer status must be one of [Decline,Accept]")

    if status == "Decline" and not reason:
        frappe.local.response["message"] = "Please set reason for decline status"
        frappe.throw("Please set reason for decline status")
    if status== "Accept" and  not id:
        frappe.local.response["message"] = "Please set selection id"
        frappe.throw("Please set selection id")
    
        if "contract" not in frappe.request.files:
                frappe.throw("Contract not found in Files")   
            
    response=merchant_contract_response(contract_id,contract_document_id,status,reason,feedback)
    
    frappe.clear_messages()
 
    frappe.local.response["data"] = response
    return



@frappe.whitelist(methods=["POST"])
@maintenance_mode
def get_contract_issue_response(contract_id):
  
    if "contract" not in frappe.request.files:
            frappe.throw("Contract not found in Files")   
            
    response=merchant_issue_contract_response(contract_id)
    
    frappe.clear_messages()
 
    frappe.local.response["data"] = response
    return