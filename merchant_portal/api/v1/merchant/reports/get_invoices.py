import frappe
from frappe.utils import cint
from merchant_portal.controller.maintenance_mode import maintenance_mode
from frappe import _
from frappe.utils.pdf import get_pdf

import frappe
from frappe.utils import cint

import frappe
import math
from frappe.utils import cint

@frappe.whitelist(methods=["GET", "POST"])
def get_merchant_invoices(PageNumber=1, PageSize=20):
    """
    GET or POST /api/method/merchant_portal.api.get_merchant_invoices
      ?PageNumber=1
      &PageSize=20

    Pagination via:
      • PageNumber – 1-based page index (default 1)
      • PageSize   – items per page     (default 20)

    Returns:
      TotalRows   – total matching invoices
      TotalPages  – total pages given PageSize
      PageNumber  – current page
      PageSize    – items per page
      invoices    – list of invoice objects
    """

    # 1) Validate user → Merchant → status
    user = frappe.session.user
    merchant = frappe.db.get_value("Merchant", {"email_address": user}, "name")
    if not merchant:
        frappe.throw("Merchant record not found for this user", frappe.DoesNotExistError)

    status = frappe.db.get_value("Merchant", merchant, "status")
    if status != "Active (Contracted)":
        frappe.throw("Merchant is not in Active (Contracted) status", frappe.ValidationError)

    # 2) Load registered agreement
    agr = frappe.db.get_value(
        "Merchant Subvention Agreement",
        {"merchant": merchant},
        ["name", "registered"],
        as_dict=True
    )
    if not agr or not agr.registered:
        frappe.throw("No registered subvention agreement for this merchant", frappe.DoesNotExistError)

    agreement_name = agr.name

    # 3) Coerce & normalize pagination params
    page = max(cint(PageNumber), 1)
    size = max(cint(PageSize), 1)
    start = (page - 1) * size

    # 4) Count & fetch invoices
    filters = {
        "custom_merchant_subvention_agreement": agreement_name,
        "docstatus": 1
    }
    total_rows = frappe.db.count("Sales Invoice", filters)
    total_pages = math.ceil(total_rows / size) if size else 0

    raw = frappe.get_all(
        "Sales Invoice",
        filters=filters,
        fields=[
            "name",
            "posting_date",
            "due_date",
            "custom_from__date",
            "custom_to__date",
            "custom_overdue_amount",
            "grand_total",
            "outstanding_amount",
            "status",
        ],
        order_by="posting_date desc",
        limit_start=start,
        limit_page_length=size
    )

    # 5) Remap fields
    invoices = [{
        "name":               inv.name,
        "posting_date":       inv.posting_date,
        "due_date":           inv.due_date,
        "from_date":          inv.custom_from__date,
        "to_date":            inv.custom_to__date,
        "overdue_amount":     inv.custom_overdue_amount,
        "grand_total":        inv.grand_total,
        "outstanding_amount": inv.outstanding_amount,
        "status":             inv.status,
    } for inv in raw]

    return {
        "TotalRows":   total_rows,
        "TotalPages":  total_pages,
        "PageNumber":  page,
        "PageSize":    size,
        "invoices":    invoices
    }





@frappe.whitelist()
@maintenance_mode
def download_tasheel_invoice(invoice_name):
    """
    Download a Sales Invoice PDF using the 'Tasheel Invoice' print format
    only if the invoice's custom_merchant_subvention_agreement belongs
    to the current user's Merchant.
    """
    user = frappe.session.user

    # 1) Find the Merchant for this user
    merchant_name = frappe.db.get_value("Merchant", {"email_address": user}, "name")
    if not merchant_name:
        frappe.throw(_("No Merchant record found for user {0}").format(user),
                     frappe.ValidationError)

    # 2) Load the Sales Invoice
    try:
        invoice = frappe.get_doc("Sales Invoice", invoice_name)
    except frappe.DoesNotExistError:
        frappe.throw(_("Sales Invoice {0} not found").format(invoice_name),
                     frappe.DoesNotExistError)

    # 3) Get the linked agreement from your custom field
    agreement_name = invoice.get("custom_merchant_subvention_agreement")
    if not agreement_name:
        frappe.throw(_("This invoice has no linked Subvention Agreement"),
                     frappe.ValidationError)

    # 4) Verify the agreement belongs to this merchant
    agreement = frappe.get_doc("Merchant Subvention Agreement", agreement_name)
    if agreement.merchant != merchant_name:
        frappe.throw(_("You are not permitted to access this invoice"),
                     frappe.PermissionError)

    # 5) Render with the 'Tasheel Invoice' print format + letter head
    html = frappe.get_print(
        doctype="Sales Invoice",
        name=invoice_name,
        print_format="Tasheel Invoice",
        no_letterhead=0,
        letterhead="Tasheel Invoice"
        
    )

    # 6) Convert to PDF and return
    pdf_bytes = get_pdf(html)
    frappe.local.response.filename = f"{invoice_name}.pdf"
    frappe.local.response.filecontent = pdf_bytes
    frappe.local.response.type = "pdf"
