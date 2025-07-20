import frappe
from merchant_portal.controller.language_decorator import set_language_from_header
from merchant_portal.controller.maintenance_mode import maintenance_mode
@frappe.whitelist(allow_guest=True, methods=["GET"])
@maintenance_mode
@set_language_from_header
def get_merchant_annual_sales():
    # Set the session language
    lang=frappe.local.lang 

    # Fetch all names from the Merchant Annual Sales doctype
    sales_records = frappe.db.get_all("Merchant Annual Sales", pluck="name")

    # If the language is Arabic, translate names
    if lang == "ar":
        sales_records = [
            frappe.db.get_value("Translation", {
                "source_text": record,
                "language": "ar"
            }, "translated_text") or record
            for record in sales_records
        ]

    return sales_records
