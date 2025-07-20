# merchant_portal/api/v1/settings/terms_and_conditions.py

import os
from urllib.parse import urlparse

import frappe
from frappe import _

from merchant_portal.controller.language_decorator import \
    set_language_from_header
from merchant_portal.controller.maintenance_mode import maintenance_mode


@frappe.whitelist(allow_guest=True, methods=["GET"])
@maintenance_mode
@set_language_from_header
def terms_and_conditions():
    # 1) fetch the file URL/path stored in your single-setting doctype
    terms_url = frappe.db.get_single_value("Merchant Portal Setting", "terms_and_conditions_file")
    if not terms_url:
        frappe.local.response["message"] = _("Terms and Conditions file not found")
        frappe.throw(_("Terms and Conditions file not found"), frappe.ValidationError)

    # 2) strip off host if it's a full URL
    if terms_url.startswith("http"):
        path = urlparse(terms_url).path     # e.g. "/files/9d6fecba-b166-4dc1-9bde-198beae9988a.pdf"
    else:
        path = terms_url                     # already something like "/files/…"

    # 3) derive the filename
    filename = os.path.basename(path)

    # 4) build the absolute path under sites/<your_site>/public/
    #    we split on “/” so sub-folders under public/ are handled too
    rel_parts = path.lstrip("/").split("/")     # ["files", "9d6fecba-….pdf"]
    abs_path = frappe.get_site_path("public", *rel_parts)

    # 5) log where we’re looking—handy to spot path mismatches
    frappe.log_error(f"Looking for T&C PDF at {abs_path}", "terms_and_conditions")

    if not os.path.isfile(abs_path):
        frappe.local.response["message"] = _("Terms and Conditions file not found")
        frappe.throw(_("Terms and Conditions file not found on server"), frappe.ValidationError)

    # 6) read & stream back as PDF
    with open(abs_path, "rb") as f:
        pdf_bytes = f.read()

    frappe.local.response.filename    = filename
    frappe.local.response.filecontent = pdf_bytes
    frappe.local.response.type        = "pdf"
