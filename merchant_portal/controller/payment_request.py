import base64
import json
import os

import frappe
import requests
from frappe import _
from frappe.utils import get_url, getdate, now_datetime
from frappe.utils.file_manager import save_file
from jinja2 import Template

# ─────────────────────────────────────────────────────────────
# 1. Trigger: On Submit of Sales Invoice → Create & Send New Invoice
# ─────────────────────────────────────────────────────────────


def handle_new_invoice(doc, method):
    """Triggered when a Sales Invoice is submitted. Creates Merchant Payment Request."""
    if doc.get("custom_payment_request_sent"):
        return  # Already handled

    try:
        # Get customer and merchant info
        customer = frappe.get_doc("Customer", doc.customer)
        merchant_name = customer.get("custom_merchant")
        merchant = frappe.get_doc("Merchant", merchant_name) if merchant_name else None

        # Create Merchant Payment Request
        mpr = frappe.get_doc({
            "doctype": "Merchant Payment Request",
            "sales_invoice": doc.name,
            "type": "New Invoice",
            "posting_datetime": now_datetime(),
            "from_date": doc.custom_from__date,
            "to_date": doc.custom_to__date,
            "customer": doc.customer,
            "merchant": merchant.name if merchant else None,
            "email_address": merchant.email_address if merchant else None,
            "commercial_register": merchant.commercial_register if merchant else None,
            "status": "Pending"
        })
        mpr.insert(ignore_permissions=True)
        frappe.db.commit()

        try:
            # Attach PDF and XLSX
            attach_invoice_and_transaction_files(mpr)
        except Exception:
            mpr.status = "Failed"
            mpr.error = frappe.get_traceback()
            mpr.save(ignore_permissions=True)
            return

        try:
            # Enqueue email
            frappe.enqueue(send_payment_email, docname=mpr.name)
        except Exception:
            mpr.status = "Failed"
            mpr.error = frappe.get_traceback()
            mpr.save(ignore_permissions=True)
            return

        # Mark invoice as sent
        frappe.db.set_value("Sales Invoice", doc.name, "custom_payment_request_sent", 1)

    except Exception:
        frappe.log_error(frappe.get_traceback(), "handle_new_invoice: Failed")



@frappe.whitelist()
def manual_send_payment_request():
    invoices=frappe.db.get_all("Sales Invoice",filters={"docstatus":1,"outstanding_amount":[">",1],"custom_payment_request_sent":0},pluck ="name")
    for invoice_name in invoices:
        
        try:
            # 1. Load Sales Invoice
            doc = frappe.get_doc("Sales Invoice", invoice_name)
            if doc.get("custom_payment_request_sent"):
                frappe.throw(_("Payment Request already sent."))
            
            # if doc.get("outstanding_amount")< 1:
            #     frappe.db.set_value("Sales Invoice", invoice_name,"custom_payment_request_sent",1)
            #     frappe.throw(_("Invoice already paid"))

            # 2. Fetch Customer and Merchant
            customer = frappe.get_doc("Customer", doc.customer)
            merchant_name = customer.get("custom_merchant")
            merchant = frappe.get_doc("Merchant", merchant_name) if merchant_name else None

            # 3. Create Merchant Payment Request
            mpr = frappe.get_doc({
                "doctype": "Merchant Payment Request",
                "sales_invoice": doc.name,
                "type": "New Invoice",
                "posting_datetime": now_datetime(),
                "from_date": doc.custom_from__date,
                "to_date": doc.custom_to__date,
                "customer": doc.customer,
                "merchant": merchant.name if merchant else None,
                "email_address": merchant.email_address if merchant else None,
                "commercial_register": merchant.commercial_register if merchant else None,
                "status": "Pending"
            })
            mpr.insert(ignore_permissions=True)
            frappe.db.commit()

            try:
                # 4. Attach PDF and transaction file
                attach_invoice_and_transaction_files(mpr)
            except Exception:
                mpr.status = "Failed"
                mpr.error = frappe.get_traceback()
                mpr.save(ignore_permissions=True)
                frappe.throw(_("Failed to attach invoice or transaction file."))

            try:
                # 5. Send email (via enqueue)
                frappe.enqueue(send_payment_email, docname=mpr.name)
            except Exception:
                mpr.status = "Failed"
                mpr.error = frappe.get_traceback()
                mpr.save(ignore_permissions=True)
                frappe.throw(_("Failed to enqueue email sending."))

            # 6. Mark Sales Invoice as sent
            frappe.db.set_value("Sales Invoice", doc.name, "custom_payment_request_sent", 1)

            frappe.msgprint(_("Payment Request has been created and email will be sent."))

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Payment Request: Manual Send Failed")
            frappe.throw(_("An error occurred while creating the Payment Request. See error log."))
# ─────────────────────────────────────────────────────────────
# 2. Scheduled Task: Overdue Reminders (Daily)
# ─────────────────────────────────────────────────────────────

def send_overdue_payment_reminders():
    from frappe.utils import today
    invoices = frappe.get_all("Sales Invoice", filters={
        "docstatus": 1,
        "outstanding_amount": [">", 0],
        "due_date": ["<", today()]
    }, fields=["name", "custom_from__date", "custom_to__date"])

    for inv in invoices:
        exists = frappe.db.exists("Merchant Payment Request", {
            "sales_invoice": inv.name,
            "type": "Overdue",
            "status": "Sent"
        })
        if exists:
            continue

        try:
            mpr = frappe.get_doc({
                "doctype": "Merchant Payment Request",
                "sales_invoice": inv.name,
                "type": "Overdue",
                "posting_datetime": now_datetime(),
                "from_date": inv.custom_from__date,
                "to_date": inv.custom_to__date
            })
            mpr.insert(ignore_permissions=True)
            frappe.db.commit()

            attach_invoice_and_transaction_files(mpr)

            frappe.enqueue("merchant_portal.utils.payment_request.send_payment_email", docname=mpr.name)

        except Exception:
            frappe.log_error(frappe.get_traceback(), f"Overdue Reminder Failed: {inv.name}")

# ─────────────────────────────────────────────────────────────
# 3. Attach PDF and Transaction XLSX to Merchant Payment Request
# ─────────────────────────────────────────────────────────────

def attach_invoice_and_transaction_files(mpr_doc):
    attach_invoice_pdf(mpr_doc)
    attach_transaction_xlsx(mpr_doc)

def attach_transaction_xlsx(mpr_doc):
    try:
        # Validate merchant
        if not mpr_doc.merchant:
            frappe.throw(_("Merchant not set on payment request"))

        # Get contract ID
        contract_id = frappe.get_value(
            "Merchant Subvention Agreement",
            {"merchant": mpr_doc.merchant},
            "w4u_contract_id"
        )
        if not contract_id:
            frappe.throw(_("No active Merchant Subvention Agreement found for merchant: {0}").format(mpr_doc.merchant))

        # Call external report API
        url = "http://w4-ufx-api.tasheelfinance.com/api/merchant/generate-reports/"
        payload = {
            "requestedMerchants": [contract_id],
            "fromDate": mpr_doc.from_date.isoformat() if mpr_doc.from_date else getdate().isoformat(),
            "toDate": mpr_doc.to_date.isoformat() if mpr_doc.to_date else getdate().isoformat()
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if not response.ok:
            frappe.throw(_("Transaction report API error {0}").format(response.status_code))

        data = response.json()
        files = data.get("files") or []
        if not files:
            frappe.throw(_("No transaction files returned by API."))

        # Resolve UNC to local path
        unc_path = files[0]
        parts = unc_path.lstrip("\\").split("\\")
        try:
            idx = parts.index("MERCHANT_TRANSACTIONS")
        except ValueError:
            frappe.throw(_("Invalid UNC path structure: {0}").format(unc_path))

        rel_parts = parts[idx + 1:]
        mount_base = frappe.conf.get("merchant_transaction_mount") or "/mnt/merchant_transactions/Email_documents_UCFS/MERCHANT_TRANSACTIONS"
        local_path = os.path.join(mount_base, *rel_parts)

        if not os.path.exists(local_path):
            frappe.throw(_("Transaction file not found on disk: {0}").format(local_path))

        # Read and attach file
        with open(local_path, "rb") as f:
            file_bytes = f.read()
        file_name = os.path.basename(local_path)

        xlsx_file = save_file(
            file_name,
            file_bytes,
            "Merchant Payment Request",
            mpr_doc.name,
            is_private=1
        )
        mpr_doc.transaction_xlsx = xlsx_file.name
        mpr_doc.save(ignore_permissions=True)

    except Exception:
        mpr_doc.status = "Failed"
        mpr_doc.error = frappe.get_traceback()
        mpr_doc.save(ignore_permissions=True)
        raise

def attach_invoice_pdf(mpr_doc):
    invoice = frappe.get_doc("Sales Invoice", mpr_doc.sales_invoice)
    settings = frappe.get_single("Merchant Portal Setting")

    # Generate PDF
    pdf_data = frappe.get_print(
        doctype="Sales Invoice",
        name=invoice.name,
        print_format=settings.invoice_print_format,
        letterhead=settings.letter_head,
        as_pdf=True
    )

    # Save to File
    pdf_file = save_file(
        f"{invoice.name}.pdf",
        pdf_data,
        "Merchant Payment Request",
        mpr_doc.name,
        is_private=1
    )

    mpr_doc.invoice_pdf = pdf_file.name
    mpr_doc.save(ignore_permissions=True)
    frappe.db.commit()

# ─────────────────────────────────────────────────────────────
# 4. Send Email Using Subject & Body Templates
# ─────────────────────────────────────────────────────────────




def send_payment_email(docname):
    doc = frappe.get_doc("Merchant Payment Request", docname)

    try:
        if not doc.email_address:
            raise Exception("No email address set")

        settings = frappe.get_single("Merchant Portal Setting")
        invoice = frappe.get_doc("Sales Invoice", doc.sales_invoice)

        context = {
            "invoice": invoice,
            "doc": doc
        }

        # Render subject and body using templates
        subject = Template(settings.subject or "Payment Request – {{ invoice.name }}").render(context)
        message = Template(settings.mail_body or "Please find attached your invoice.").render(context)

        attachments = []

        # Build CC list
        cc = [
            mail.user for mail in settings.invoice_mail_cc
            if mail.user and "@" in mail.user
        ]

        # Invoice PDF
        if doc.invoice_pdf:
            pdf_file = frappe.get_doc("File", doc.invoice_pdf)
            attachments.append({
                "fname": pdf_file.file_name,
                "fcontent": pdf_file.get_content()
            })

        # Transaction XLSX
        if doc.transaction_xlsx:
            xlsx_file = frappe.get_doc("File", doc.transaction_xlsx)
            attachments.append({
                "fname": xlsx_file.file_name,
                "fcontent": xlsx_file.get_content()
            })

        # Set recipients excluding cc
        recipients = [doc.email_address]
        recipients = [email for email in recipients if email not in cc]

        # Send email
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message,
            cc=cc,
            expose_recipients="header",
            attachments=attachments
        )

        doc.status = "Sent"
        doc.save(ignore_permissions=True)

    except Exception:
        doc.status = "Failed"
        doc.error = frappe.get_traceback()
        doc.save(ignore_permissions=True)
