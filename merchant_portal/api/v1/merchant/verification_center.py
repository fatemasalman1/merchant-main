import frappe
from merchant_portal.merchant_portal.doctype.merchant_offer.merchant_offer import get_merchant_offers
from merchant_portal.merchant_portal.doctype.merchant_contract.merchant_contract import get_merchant_contract
from merchant_portal.controller.maintenance_mode import maintenance_mode

@frappe.whitelist(methods=["GET"])
@maintenance_mode
def get_pending_requirements():
      data=[]
      status,offer_data= get_merchant_offers(frappe.session.user)
   
      if status:
         data.append(offer_data)
         
      status,contract_data= get_merchant_contract(frappe.session.user)
      if status:
         data.append(contract_data)
      
      
         
      frappe.clear_messages()
      frappe.local.response["has_pending_requirements"] = 1 if len(data) else 0
      frappe.local.response["data"] = data
      return