import base64
import calendar
import json
import os
import uuid
from datetime import date

import frappe
import requests
from frappe import _
from frappe.utils import get_url, getdate
from frappe.utils.file_manager import save_file

from merchant_portal.controller.maintenance_mode import maintenance_mode


@frappe.whitelist(methods=["GET"])
@maintenance_mode
def get_merchant_transactions(fromDate=None, toDate=None, pageNumber=1, pageSize=20):
    """
    GET /api/method/your_app.api.get_merchant_dashboard
      ?fromDate=YYYY-MM-DD   (optional)
      &toDate=YYYY-MM-DD     (optional)
      &pageNumber=<int>      (optional, defaults to 1)
      &pageSize=<int>        (optional, defaults to 20)
    """

    result = {"success": 0, "data": {}, "error": ""}

    try:
        # — 1) Default dates to first/last of current month —
        today = date.today()
        first_day = today.replace(day=1)
        last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        fromDate = fromDate or first_day.isoformat()
        toDate   = toDate   or last_day.isoformat()

        # — 2) Normalize paging params —
        try:
            pageNumber = int(pageNumber)
        except (TypeError, ValueError):
            pageNumber = 1
        try:
            pageSize = int(pageSize)
        except (TypeError, ValueError):
            pageSize = 20

        # — 3) Merchant + status checks —
        user = frappe.session.user
        merchant = frappe.db.get_value("Merchant", {"email_address": user}, "name")
        if not merchant:
            raise ValueError("Merchant record not found for this user {0}".format(user))

        status = frappe.db.get_value("Merchant", merchant, "status")
        if status != "Active (Contracted)":
            raise ValueError("Merchant is not in Active (Contracted) status")

        # — 4) Agreement + registered + contract ID —
        agr = frappe.db.get_value(
            "Merchant Subvention Agreement",
            {"merchant": merchant},
            ["registered", "w4u_contract_id"],
            as_dict=True
        )
        if not agr:
            raise ValueError("No Subvention Agreement found for merchant")
        if agr.registered != 1:
            raise ValueError("Agreement is not registered")
        partner_contract = agr.w4u_contract_id
        if not partner_contract:
            raise ValueError("Contract ID missing in agreement")
        settings = frappe.get_single("Integration End Point")
        base_url = settings.url or frappe.throw("Please set the Integration End Point URL")

        # 2. Ensure no trailing slash (so f‐strings concatenate cleanly)
        base_url = base_url.rstrip("/")

        # 3. Build your full endpoint
        url = f"{base_url}/api/merchant/Dashboard"

    
        payload = {
            "PartnerContract": partner_contract,
            "StartDate":       fromDate,
            "EndDate":         toDate,
            "PageNumber":      str(pageNumber),
            "PageSize":        str(pageSize)
        }
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
          
        )
        resp.raise_for_status()
        j = resp.json()

        # — 6) Build success response —
        counters = j.get("DashboardCounters", {})
        result["data"] = {
            "current_invoice_amount": counters.get("CurrentInvoiceAmt"),
            "total_outstanding":       counters.get("TotalOutstanding"),
            "total_paid":              counters.get("TotalPaid"),
            "transactions":            j.get("Transactions", []),
            "total_rows":              j.get("TotalRows"),
            "total_pages":             j.get("TotalPages"),
        }
        result["success"] = 1

    except Exception as e:
        frappe.log_error(title="get_merchant_dashboard Failed", message=frappe.get_traceback())
       

    return result




@frappe.whitelist(methods=["GET"])
def generate_report_file(fromDate=None, toDate=None):
    """
    POST /api/method/merchant_portal.api.v1.report.generate_report_file
    {
      "fromDate": "YYYY-MM-DD",  # optional
      "toDate":   "YYYY-MM-DD"   # optional
    }
    → {
         "filename": "report_2025-05-01_2025-05-31.csv",
         "content": "<base64-encoded CSV data>"
       }
    """
    # ─── Default dates ──────────────────────────────────────────
    today = date.today()
    if not fromDate:
        fromDate = today.replace(day=1).isoformat()
    if not toDate:
        last = calendar.monthrange(today.year, today.month)[1]
        toDate = today.replace(day=last).isoformat()

    # ─── Merchant by email_address ──────────────────────────────
    user = frappe.session.user
    merchant = frappe.db.get_value("Merchant", {"email_address": user}, "name")
    if not merchant:
        frappe.throw(_("No Merchant found for email {0}").format(user))

    # ─── Contract ID ────────────────────────────────────────────
    contract_id = frappe.get_value(
        "Merchant Subvention Agreement",
        {"merchant": merchant},
        "w4u_contract_id"
    )
    if not contract_id:
        frappe.throw(_("No active Agreement for merchant {0}").format(merchant))

    # ─── Call external report API ────────────────────────────────
    api_url = frappe.get_site_config().get(
        "w4u_report_api_url",
        "http://w4-ufx-api.tasheelfinance.com/api/merchant/generate-reports/"
    )
    resp = requests.post(api_url, json={
        "requestedMerchants": [contract_id],
        "fromDate": fromDate,
        "toDate":   toDate
    }, headers={"Content-Type": "application/json"})
    if not resp.ok:
        frappe.throw(_("Report API error {0}").format(resp.status_code))

    files = (resp.json() or {}).get("files") or []
    if not files:
        frappe.throw(_("No files returned from report API"))

    # ─── Resolve UNC → local path ───────────────────────────────
    unc = files[0].lstrip("\\")
    parts = unc.split("\\")
    try:
        idx = parts.index("MERCHANT_TRANSACTIONS")
    except ValueError:
        frappe.throw(_("Invalid UNC: {0}").format(unc))
    rel = parts[idx+1:]
    mount = frappe.conf.get(
        "merchant_transaction_mount",
        "/mnt/merchant_transactions/Email_documents_UCFS/MERCHANT_TRANSACTIONS"
    )
    local_path = os.path.join(mount, *rel)
    if not os.path.exists(local_path):
        frappe.throw(_("File not found: {0}").format(local_path))

    # ─── Read bytes & base64-encode ──────────────────────────────
    with open(local_path, "rb") as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode("ascii")
    filename = os.path.basename(local_path)

    # ─── Return JSON payload ─────────────────────────────────────
    return {
        "filename": filename,
        "content": b64
    }
