import frappe
from frappe.utils import today, add_to_date

def track_contract_status():
    today_date = today()

    # Grab all active contracts whose end date has passed, including the auto_renewal flag
    contracts = frappe.get_all(
        "Merchant Subvention Agreement",
        filters={
            "contract_end_date": ["<", today_date],
            "status": "Active"
        },
        fields=["name", "contract_end_date", "auto_renewal"]
    )

    for c in contracts:
        if c.auto_renewal:
            # extend the original end date by 1 year
            new_end_date = add_to_date(c.contract_end_date, years=1)
            frappe.db.set_value(
                "Merchant Subvention Agreement",
                c.name,
                {
                    "contract_end_date": new_end_date,
                    "status": "Active"
                }
            )
        else:
            # no auto-renewal → expire the contract
            frappe.db.set_value(
                "Merchant Subvention Agreement",
                c.name,
                "status",
                "Expired"
            )
