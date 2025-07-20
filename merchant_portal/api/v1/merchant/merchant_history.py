import frappe
from merchant_portal.merchant_portal.doctype.merchant_offer.merchant_offer import get_history_offers
from merchant_portal.merchant_portal.doctype.merchant_contract.merchant_contract import get_history_contract
from merchant_portal.controller.maintenance_mode import maintenance_mode

@frappe.whitelist(methods=["GET"])
@maintenance_mode
def get_offer_and_contract():
    response_data_offer=[]
    response_data_contract=[]
    status,response_data_offer= get_history_offers(frappe.session.user)
    status,response_data_contract= get_history_contract(frappe.session.user)
    data= response_data_contract+response_data_offer

    frappe.clear_messages()
    frappe.local.response["has_history"] = 1 if len(data) else 0
    frappe.local.response["data"] = data
    return