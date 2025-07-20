# merchant_portal/utils.py

import functools
import frappe
from werkzeug.exceptions import ServiceUnavailable

def maintenance_mode(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # 1) Check global maintenance flag
        settings = frappe.get_single("Merchant Portal Setting")
        if getattr(settings, "maintenance_mode", 0) == 1:
            # raises a 503
            raise ServiceUnavailable(description="Service is temporarily under maintenance")

        # 2) Check per-merchant disabled flag
        user = frappe.session.user
        disabled = frappe.db.get_value(
            "Merchant",
            {"user": user},
            "disabled"
        ) or 0

        if disabled == 1:
            raise ServiceUnavailable(description="Your merchant account is currently disabled")

        # 3) Everything OK → call the wrapped function
        return f(*args, **kwargs)

    return wrapper
