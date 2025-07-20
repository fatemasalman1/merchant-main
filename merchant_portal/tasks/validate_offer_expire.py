import frappe
from frappe.utils import today

def validate_offer_expire():
    offers=frappe.db.get_all("Merchant Offer",filters={"offer_end_date":["<",today()],"status":"Waiting For Response"},pluck="name")
    if len(offers):
        for offer in offers:
            frappe.get_doc("Merchant Offer",offer).set_offer_expired()
            