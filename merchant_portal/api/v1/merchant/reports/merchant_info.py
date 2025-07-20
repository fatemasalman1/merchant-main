import calendar
from datetime import date

import frappe
import requests

from merchant_portal.controller.maintenance_mode import maintenance_mode


@frappe.whitelist(methods=["GET"])
@maintenance_mode
def get_merchant_dashboard_counter(fromDate=None, toDate=None):
    """
    GET /api/method/your_app.api.get_merchant_dashboard_counter
      ?fromDate=YYYY-MM-DD (optional)
      &toDate=YYYY-MM-DD   (optional)

    If you omit either parameter, it defaults to the first/last day of the current month.
    """
    # return{
    #     "success": 1,
    #     "data": {
    #         "current_invoice_amount": "0",
    #         "total_outstanding": "9591.43",
    #         "total_paid": "6198.3"
    #     },
    #     "error": ""
    # }
    # 1) Compute default dates if needed
    today = date.today()
    first_day = today.replace(day=1)
    last_day = today.replace(
        day=calendar.monthrange(today.year, today.month)[1]
    )

    fromDate = fromDate or first_day.isoformat()
    toDate   = toDate   or last_day.isoformat()

    result = {"success": 0, "data": {}, "error": ""}

    try:
        # 2) Merchant + status checks
        user = frappe.session.user
        merchant = frappe.db.get_value("Merchant", {"email_address": user}, "name")
        if not merchant:
            raise ValueError("Merchant record not found for this user {0}".format(user))

        status = frappe.db.get_value("Merchant", merchant, "status")
        if status != "Active (Contracted)":
            raise ValueError("Merchant is not in Active (Contracted) status")

        # 3) Agreement + registered + contract ID
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
        base_url = settings.url or frappe.throw("Integration End Point URL not set")
        base_url = base_url.rstrip("/")

        # 2. Build the invoice URL with query params
        url = (
            f"{base_url}/api/merchant/DashboardCounters"
            f"?partnerContract={partner_contract}"
            f"&fromDate={fromDate}&toDate={toDate}"
        )

        resp = requests.post(url, timeout=10)
        resp.raise_for_status()
        payload = resp.json()

        # 5) Build success response
        result["data"] = {
            "current_invoice_amount": payload.get("CurrentInvoiceAmt"),
            "total_outstanding":   payload.get("TotalOutstanding"),
            "total_paid":     payload.get("TotalPaid"),
        }
        result["success"] = 1

    except Exception as e:
        # log full traceback
        frappe.log_error(title="get_merchant_dashboard_counter Failed",message=frappe.get_traceback())
        

    return result
