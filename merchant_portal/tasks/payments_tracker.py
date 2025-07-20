# merchant_portal/merchant_portal/tasks.py

from datetime import date, datetime, timedelta

import frappe
import requests
from frappe.utils import now_datetime


def fetch_payments_for_merchants():
    """
    Daily cron: for each Agreement with payment_enable_scheduler=1,
    pull payments from payment_last_pull_end_date → today,
    create Payment Entries (skipping duplicates), track results,
    and update last pull dates/status (only on success).
    """

    today = date.today()
    end_date = today

    # 1) Pre‐fetch the default 'paid_to' account & its currency for Mode of Payment 'Cash'
    mode = "Cash"
    mop = frappe.get_doc("Mode of Payment", mode)
    paid_to_account = None
    # Mode of Payment has a child table 'accounts' with a boolean 'default_account' :contentReference[oaicite:0]{index=0}
    for row in mop.accounts:
        if row.default_account:
            paid_to_account = row.default_account
            break

    if not paid_to_account:
        frappe.throw(f"No default account set for Mode of Payment '{mode}'")

    paid_to_currency = frappe.get_value("Account", paid_to_account, "account_currency")

    # 2) Get all Agreements that should run
    agreements = frappe.get_all(
        "Merchant Subvention Agreement",
        filters={
            "w4u_contract_id":          ["!=", ""],
        
            "payment_enable_scheduler": 1
        },
        fields=["name", "w4u_contract_id", "merchant", "payment_last_pull_end_date"]
    )

    for agr in agreements:
        agr_doc = frappe.get_doc("Merchant Subvention Agreement", agr.name)

        # 3) Determine date window
        if agr_doc.payment_last_pull_end_date:
            start_date = agr_doc.payment_last_pull_end_date
        else:
            # first run → first day of previous month
            first_of_current = today.replace(day=1)
            prev_month_last  = first_of_current - timedelta(days=1)
            start_date       = prev_month_last.replace(day=1)

        # nothing to fetch?
        if start_date > end_date:
            continue

        overall_status = "Success"
        error_msg      = None

        # 4) Find the linked Customer
        customer = frappe.get_value(
            "Customer",
            {"custom_merchant": agr_doc.merchant},
            "name"
        )
        if not customer:
            overall_status = "Failed"
            error_msg = f"No Customer for merchant {agr_doc.merchant}"
        else:
            page, page_size = 1, 50
            # 5) Paginate the Payments API
            while True:
                payload = {
                    "PartnerContract": agr_doc.w4u_contract_id,
                    "StartDate":       start_date.strftime("%Y-%m-%d"),
                    "EndDate":         end_date.strftime("%Y-%m-%d"),
                    "PageNumber":      page,
                    "PageSize":        page_size
                }
                try:
                    settings = frappe.get_single("Integration End Point")
                    base_url = settings.url or frappe.throw("Please set the Integration End Point URL")

                    # 2. Ensure no trailing slash (so f‐strings concatenate cleanly)
                    base_url = base_url.rstrip("/")

                    # 3. Build your full endpoint
                    endpoint = f"{base_url}/api/merchant/Payments"
                    resp = requests.post(
                        endpoint,
                        headers={"Content-Type": "application/json"},
                        json=payload
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    txns = data.get("Transactions", [])

                    for tx in txns:
                        tx_id = tx.get("Id")
                        # skip duplicates by custom_id :contentReference[oaicite:1]{index=1}
                        if frappe.db.exists("Payment Entry", {"custom_id": tx_id}):
                            continue

                        tx_date = datetime.fromisoformat(tx.get("Date")).date()
                        pe = frappe.get_doc({
                            "doctype":                "Payment Entry",
                            "payment_type":           "Receive",
                            "party_type":             "Customer",
                            "custom_merchant":          agr_doc.merchant,
                            "custom_merchant_subvention_agreement": agr_doc.name,
                            "party":                  customer,
                            "posting_date":           tx_date,
                            "paid_amount":            tx.get("Amount"),
                            "received_amount":        tx.get("Amount"),
                            "mode_of_payment":        mode,
                            "paid_to":                paid_to_account,
                            "paid_to_account_currency": paid_to_currency,
                            "custom_id":              tx_id,
                            "custom_payment_details": tx.get("PaymentDetails"),
                            "custom_payment_method":  tx.get("PaymentMethod")
                        })
                        pe.insert(ignore_permissions=True,ignore_mandatory=True)
                        pe.flags.ignore_mandatory = True
                        pe.submit()

                    total_pages = data.get("TotalPages", 1)
                    if page >= total_pages:
                        break
                    page += 1

                except Exception as e:
                    overall_status = "Failed"
                    error_msg =frappe.get_traceback()
                    break

        # 6) Record this run in the child table
        agr_doc.append("payments_scheduler_tracker_tab", {
            "posting_date": date.today(),
            "from_date":     start_date,
            "to_date":       end_date,
            "status":        overall_status,
            "error_msg":     error_msg or ""
        })

        # 7) Update parent tracking fields
        agr_doc.payment_last_scheduler_status = overall_status
        agr_doc.payment_last_execution_time   = now_datetime()
        if overall_status == "Success":
            agr_doc.payment_last_pull_start_date = start_date
            agr_doc.payment_last_pull_end_date   = end_date

        agr_doc.save(ignore_permissions=True)
