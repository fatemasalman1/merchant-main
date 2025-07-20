# merchant_portal/api/v1/merchant/generate_contract.py

import os
from urllib.parse import urlparse

import frappe
from frappe import _

from merchant_portal.controller.language_decorator import \
    set_language_from_header
from merchant_portal.controller.maintenance_mode import maintenance_mode


@frappe.whitelist(methods=["POST"])
@maintenance_mode
@set_language_from_header
def get_merchant_contract(contract_id):
    # 1) permission
    frappe.has_permission("Merchant Contract", doc=contract_id, throw=True)

    # 2) get whatever's in the pdf_file field
    pdf_file = frappe.db.get_value("Merchant Contract", contract_id, "pdf_file")
    
    if not pdf_file:
        frappe.throw(_("PDF File not found"), frappe.ValidationError)

    # 3) strip host if needed
    if pdf_file.startswith("http"):
        parsed = urlparse(pdf_file)
        path = parsed.path      # e.g. "/files/MC-000019_contract.pdf"
    else:
        path = pdf_file         # e.g. "/files/MC-000019_contract.pdf"

    # 4) get just the filename (or sub-folders under files/)
    #    here we assume everything after the last slash
    filename = os.path.basename(path)

    # 5) build the absolute path under sites/<your_site>/public/files/
    abs_path = frappe.get_site_path("public", "files", filename)

    # 6) log it so you can check your error log if it's wrong
    frappe.log_error(f"Looking for PDF at {abs_path}", "get_merchant_contract")

    if not os.path.isfile(abs_path):
        frappe.throw(_("PDF File not found on server"), frappe.ValidationError)

    # 7) read & stream it
    with open(abs_path, "rb") as f:
        pdf_bytes = f.read()

    frappe.local.response.filename    = filename
    frappe.local.response.filecontent = pdf_bytes
    frappe.local.response.type        = "pdf"
