import frappe
from frappe import _
from merchant_portal.controller.language_decorator import set_language_from_header
from merchant_portal.controller.maintenance_mode import maintenance_mode
@frappe.whitelist(allow_guest=True, methods=["GET"])
@maintenance_mode
@set_language_from_header
def get_business_category(search=None):
    # Set the language for the session
    lang =frappe.local.lang 

    # Initialize the result list
    categories = []

    if search:
        # Prepare the search logic
        if lang == "ar":
            # Find all possible matches in Arabic translations
            translated_to_original = frappe.db.get_all(
                "Translation",
                filters={
                    "translated_text": ["like", f"%{search}%"],
                    "language": "ar"
                },
                pluck="source_text"
            )
            # Include original terms in the search
            translated_to_original.append(search)  # Fallback to direct search
            filters = {"name": ["in", translated_to_original]}
        else:
            # Search directly in English
            filters = {"name": ["like", f"%{search}%"]}

        # Query the database using the prepared filters
        categories = frappe.db.get_all(
            "Merchant Business Category",
            filters=filters,
            pluck="name"
        )

        # Translate results back to Arabic if `lang` is Arabic
        if lang == "ar":
            categories = [
                frappe.db.get_value("Translation", {
                    "source_text": name,
                    "language": "ar"
                }, "translated_text") or name
                for name in categories
            ]
    else:
        
        # If no search term, return all names
        categories = frappe.db.get_all(
            "Merchant Business Category",
            pluck="name"
        )

        # Translate names if the language is Arabic
        if lang == "ar":
            categories = [
                frappe.db.get_value("Translation", {
                    "source_text": name,
                    "language": "ar"
                }, "translated_text") or name
                for name in categories
            ]

    return categories
