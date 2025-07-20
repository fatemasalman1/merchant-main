import frappe
from frappe.utils import today

def register_pending_mid():
    mids = frappe.db.get_all("Merchant ID", filters={"status": ["in",["Pending","Reactive Requested"]], "docstatus": 1}, fields=["*"])
    if not mids:
        return

    registers_group = {}

    for mid in mids:
        registered, commercial_register, merchant = frappe.db.get_value(
            "Merchant Subvention Agreement",
            mid["parent"],
            ["registered", "commercial_register", "merchant"]
        )

        if registered:
            type = "AddMid"
            create_integration_task(type, "Merchant Subvention Agreement", mid["parent"], commercial_register, merchant, mid["mid"])
        else:
     
            if mid["parent"] not in registers_group:
                registers_group[mid["parent"]] = {
                    "commercial_register": commercial_register,
                    "merchant": merchant,
                    "mids": []
                }
            registers_group[mid["parent"]]["mids"].append(mid["mid"])
    if registers_group:
        for parent, data in registers_group.items():
            integration = frappe.new_doc("Integration Hub")
            integration.type = "RegisterMerchant"
            integration.reference_type = "Merchant Subvention Agreement"
            integration.reference_name = parent
            integration.commercial_register = data["commercial_register"]
            integration.merchant = data["merchant"]
            for mid in data["mids"]:
                integration.append("mids", {"mid": mid})
            integration.flags.ignore_permissions = True
            integration.insert()
            frappe.db.commit()


def create_integration_task(type, reference_type, reference_name, commercial_register, merchant, mid):
    integration = frappe.new_doc("Integration Hub")
    integration.type = type
    integration.reference_type = reference_type
    integration.reference_name = reference_name
    integration.commercial_register = commercial_register
    integration.merchant = merchant
    if type == "AddMid":
        integration.append("mids", {"mid": mid})
    integration.flags.ignore_permissions = True
    integration.insert()
    frappe.db.commit()
