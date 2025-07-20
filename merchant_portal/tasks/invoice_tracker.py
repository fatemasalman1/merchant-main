# merchant_portal/merchant_portal/tasks.py

import calendar
from datetime import date, timedelta

import frappe
import requests
from frappe.utils import now_datetime


def generate_opening_invoices():
    """
    One‐time backfill for migrated merchants:
      • Single invoice from 2024-01-01 → last day of previous month
      • Create Sales Invoice, set due_date
      • Track run, mark opening_invoice_fetched, record pull dates
    """
    today = date.today()
    # calculate last day of previous month
    first_of_current = today.replace(day=1)
    end_date = first_of_current - timedelta(days=1)

    # fixed start
   

    settings = frappe.get_single("Merchant Portal Setting")
    item_code          = settings.billing_fee_item
    payment_terms_days = settings.payment_terms_days or 0

    if not item_code:
        frappe.throw("Please set Billing Fee Item in Merchant Portal Settings")

    agreements = frappe.get_all(
        "Merchant Subvention Agreement",
        filters={
            "w4u_contract_id":         ["!=", ""],
       
            "opening_invoice_fetched": 0
        },
        fields=["name", "w4u_contract_id", "merchant"]
    )

    for agr in agreements:
        agr_doc = frappe.get_doc("Merchant Subvention Agreement", agr.name)
        start_date =agr_doc.initial_transaction_date
        # 1) Find linked Customer
        customer = frappe.get_value(
            "Customer",
            {"custom_merchant": agr.merchant},
            "name"
        )
        if not customer:
            _track(
                agr_doc, start_date, end_date,
                "Failed", f"No Customer for merchant {agr.merchant}"
            )
            continue

        # Fetch from API
        settings = frappe.get_single("Integration End Point")
        base_url = settings.url or frappe.throw("Integration End Point URL not set")
        base_url = base_url.rstrip("/")

        # 2. Build the invoice URL with query params
        url = (
            f"{base_url}/api/merchant/Invoice"
            f"?contract={agr.w4u_contract_id}"
            f"&fromDate={start_date}"
            f"&toDate={end_date}"
        )
        
        try:
            resp = requests.post(url)
            resp.raise_for_status()
            data = resp.json()
            if data.get("Amount") <=0:
                continue
            # 3) Avoid duplicate
            if not frappe.db.exists("Sales Invoice", {
                "contract_no":       agr.w4u_contract_id,
                "custom_from_date":  start_date,
                "custom_to_date":    end_date
            }):
                posting_date = end_date + timedelta(days=1)
                due_date     = posting_date + timedelta(days=payment_terms_days)

                si = frappe.get_doc({
                    "doctype":               "Sales Invoice",
                    "customer":              customer,
                    "set_posting_time":        1,
                    "posting_date":          posting_date,
                    "due_date":              due_date,
                    "custom_merchant_name":          agr_doc.merchant,
                    "custom_merchant_subvention_agreement": agr_doc.name,
                    "custom_contractno":           agr.w4u_contract_id,
                    "custom_from__date":      start_date,
                    "custom_to__date":        end_date,
                    "custom_overdue_amount": data.get("OvdAmount"),
                    "custom_iban":           data.get("IBAN"),
                    "disable_rounded_total":1,
                    "items": [{
                        "item_code": item_code,
                        "qty":       1,
                        "rate":      data.get("Amount") or 0
                    }]
                })
                si.insert(ignore_permissions=True)
                si.submit()

            # 4) Track success and mark as done
            _track(agr_doc, start_date, end_date, "Success")
            agr_doc.opening_invoice_fetched = 1
            agr_doc.last_pull_start_date    = start_date
            agr_doc.last_pull_end_date      = end_date
            agr_doc.last_execution_time     = now_datetime()
            agr_doc.save(ignore_permissions=True)

        except Exception as e:
            _track(agr_doc, start_date, end_date, "Failed", str(e))
            
def fetch_billing_for_merchants():
    """
    Daily cron: on billing_day, for Agreements with opening_invoice_fetched = 1,
    pull invoices since last_pull_end_date → yesterday, create Sales Invoice,
    track results, and update last_pull dates.
    """
    #  date.today()
    today =1
    settings = frappe.get_single("Merchant Portal Setting")
    billing_day        = settings.billing_day or 1
    item_code          = settings.billing_fee_item
    payment_terms_days = settings.payment_terms_days or 0

    # Only run on configured billing_day
    if today.day != billing_day:
        return

    if not item_code:
        frappe.log_error(
            "No billing_fee_item set in Merchant Portal Settings",
            "Scheduler: Billing Fee Item Missing"
        )
        return

    end_date = today - timedelta(days=1)

    agreements = frappe.get_all(
        "Merchant Subvention Agreement",
        filters={
            "w4u_contract_id":         ["!=", ""],

            "opening_invoice_fetched": 1
        },
        fields=["name", "w4u_contract_id", "merchant", "last_pull_end_date"]
    )
    
    for agr in agreements:
        agr_doc = frappe.get_doc("Merchant Subvention Agreement", agr.name)

        # Determine next window
        if agr.last_pull_end_date:
            start_date = agr.last_pull_end_date + timedelta(days=1)
        else:
            # if somehow missing, default one cycle back
            prev_month = today.month - 1 or 12
            prev_year  = today.year if today.month > 1 else today.year - 1
            start_date = date(prev_year, prev_month, billing_day)

        # Skip if no new period
        if start_date > end_date:
            continue

        # Lookup Customer
        customer = frappe.get_value(
            "Customer",
            {"custom_merchant": agr.merchant},
            "name"
        )
        if not customer:
            _track(agr_doc, start_date, end_date, "Failed",
                   f"No Customer for merchant {agr.merchant}")
            continue

        # Fetch from API
        settings = frappe.get_single("Integration End Point")
        base_url = settings.url or frappe.throw("Integration End Point URL not set")
        base_url = base_url.rstrip("/")

        # 2. Build the invoice URL with query params
        url = (
            f"{base_url}/api/merchant/Invoice"
            f"?contract={agr.w4u_contract_id}"
            f"&fromDate={start_date}"
            f"&toDate={end_date}"
        )
        try:
            resp = requests.post(url)
            resp.raise_for_status()
            data = resp.json()
            if  data.get("Amount")<1:
                continue
            # Create invoice if not exists
            if not frappe.db.exists("Sales Invoice", {
                "contract_no":       agr.w4u_contract_id,
                "custom_from_date":  start_date,
                "custom_to_date":    end_date
            }):
                posting_date = end_date + timedelta(days=1)
                due_date     = posting_date + timedelta(days=payment_terms_days)

                si = frappe.get_doc({
                    "doctype":               "Sales Invoice",
                    "customer":              customer,
                    "set_posting_time":        1,
                    "posting_date":          posting_date,
                    "due_date":              due_date,
                    "custom_contractno":           agr.w4u_contract_id,
                    "custom_from__date":      start_date,
                    "custom_to__date":        end_date,
                    "custom_overdue_amount": data.get("OvdAmount"),
                    "custom_iban":           data.get("IBAN"),
                    "custom_merchant_name":          agr_doc.merchant,
                    "custom_merchant_subvention_agreement": agr_doc.name,
                      "disable_rounded_total":1,
                    "items": [{
                        "item_code": item_code,
                        "qty":       1,
                        "rate":      data.get("Amount") or 0
                    }]
                })
                si.insert(ignore_permissions=True)
              

            # Update pull dates on success
            agr_doc.last_pull_start_date = start_date
            agr_doc.last_pull_end_date   = end_date
            agr_doc.save(ignore_permissions=True)
            _track(agr_doc, start_date, end_date, "Success")

        except Exception as e:
            _track(agr_doc, start_date, end_date, "Failed", str(e))


def _track(agr_doc, from_date, to_date, status, error_msg=None):
    """
    Log into scheduler_status_tracker and update last_scheduler_status.
    """
    agr_doc.append("scheduler_status_tracker", {
        "posting_date": date.today(),
        "from_date":     from_date,
        "to_date":       to_date,
        "status":        status,
        "error_msg":     error_msg or ""
    })
    agr_doc.last_scheduler_status = status
    agr_doc.last_execution_time   = now_datetime()
    agr_doc.save(ignore_permissions=True)
