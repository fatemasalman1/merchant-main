# merchant_portal/api/maintenance.py

import frappe
from werkzeug.exceptions import ServiceUnavailable

@frappe.whitelist(allow_guest=True)
def is_service_available():
    """
    - Raises HTTP 503 if maintenance_mode == 1.
    - Returns true  if not in maintenance and (guest or merchant not disabled).
    - Returns false if merchant is disabled.
    """
    # 1) Global maintenance → 503
    settings = frappe.get_single("Merchant Portal Setting")
    if getattr(settings, "maintenance_mode", 0) == 1:
        raise ServiceUnavailable(description="Service is temporarily under maintenance")

    # 2) Guest users are always “available”
    user = frappe.session.user
    if user == "Guest":
        return True

    # 3) Check merchant disabled flag
    disabled = frappe.db.get_value("Merchant",
                                   {"user": user},
                                   "disabled") or 0
    if disabled == 1:
        raise ServiceUnavailable(description="Service is temporarily under maintenance")
    return  True
