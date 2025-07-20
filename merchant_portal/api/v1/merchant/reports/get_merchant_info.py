import frappe

from merchant_portal.controller.maintenance_mode import maintenance_mode


@frappe.whitelist(methods=["GET"])
@maintenance_mode
def get_merchant_dashboard():
    user = frappe.session.user
    merchant = _find_merchant(user)

    # 1) If already contracted, short-circuit
    if merchant and _is_active_contracted(merchant):
        return {
            "contracted": 1,
            "mid": check_mid_add(merchant),
            "has_offer": 0,
            "offer_status": None,
            "has_contract": 0,
            "contract_status": None,
        }

    # 2) Otherwise build the “not yet contracted” response
    step_data = get_status_stepper(user)
    has_offer,    offer_status    = _has_offer(step_data)
    has_contract, contract_status = _has_contract(step_data)
    base = {
        "contracted":        0,
        "mid":                0,
        "has_offer":         has_offer,
        "offer_status":      offer_status,
        "has_contract":      has_contract,
        "contract_status":   contract_status,
        "application_id":    _get_application_id(user),
        "stepper":           step_data["stepper"],
        "application_status": step_data["application_status"],
    }
    return base


# — Helpers — 

def _find_merchant(user_email):
    return frappe.db.exists("Merchant", {"email_address": user_email})

def _is_active_contracted(merchant_name):
    status = frappe.db.get_value("Merchant", merchant_name, "status")
    return status == "Active (Contracted)"
                  
def _get_application_id(user_email):
    return frappe.db.get_value("Registration Questionnaire",
                               {"user": user_email},
                               "name")

def _has_offer(step_data):
    """
    Returns (has_offer, offer_status):
      - has_offer = 1 and offer_status = sub_title if in-progress "Waiting For Response"
      - otherwise (0, None)
    """
    if step_data["application_status"]["title"] != "Offer":
        return 0, None

    for step in step_data["stepper"]:
        if step["title"] == "Offer" and step.get("status") == 2:
            sub = step.get("sub_title")
            return (1, sub) if sub == "Waiting For Response" else (0, None)
    return 0, None

def _has_contract(step_data):
    """
    Returns (has_contract, contract_status):
      - has_contract = 1 and contract_status = sub_title if in-progress and sub_title in allowed set
      - otherwise (0, None)
    """
    if step_data["application_status"]["title"] != "Contract":
        return 0, None

    allowed = {
        "Sent To Merchant",
        "Waiting Merchant Upload Contract"
    }

    for step in step_data["stepper"]:
        if step["title"] == "Contract" and step.get("status") == 2:
            sub = step.get("sub_title")
            return (1, sub) if sub in allowed else (0, None)

    return 0, None

    
@frappe.whitelist(allow_guest=True)
def get_status_stepper(user_email):
    raw_steps = [
        {
            "doctype": "Merchant Lead",
            "field": "email",
            "status_map": {"Convert to Registration": 1},
            "title": "Registration"
        },
        {
            "doctype": "Registration Questionnaire",
            "field": "user",
            "status_map": {"Automated Approved": 1, "Manually Approved": 1},
            "title": "Application Status"
        },
        {
            "doctype": "Merchant Offer",
            "field": "user",
            "status_map": {"Accepted": 1},
            "title": "Offer",
            "in_progress_statuses": ["Negotiate", "Expired", "Waiting For Response"]
        },
        {
            "doctype": "Merchant Contract",
            "field": "user",
            "status_map": {"Contracted": 1},
            "title": "Contract",
            "in_progress_statuses": [
                "Pending",
                "Pending (Waiting Review)",
                "Sent To Merchant",
                "Feedback Received",
                "Merchant Accepted",
                "Waiting Review Uploaded",
                "Waiting Review Uploaded Contract",
                "Waiting Merchant Upload Contract"
            ]
        },
        {
            "doctype": "Merchant",
            "field": "user",
            "status_map": {"Active (Contracted)": 1},
            "title": "Completion"
        },
    ]

    collected = []

    for step in raw_steps:
        docs = frappe.get_all(
            step["doctype"],
            filters={step["field"]: user_email},
            fields=["status", "creation"],
            order_by="creation desc",
            limit=1
        )

        if docs:
            latest = docs[0]
            status = latest.status
            created = latest.creation

            # Fully completed
            if status in step.get("status_map", {}):
                collected.append({
                    "title": step["title"],
                    "status": 1,
                    "creation": created
                })

            # In progress
            elif status in step.get("in_progress_statuses", []):
                sub = status
                if sub == "Feedback Received":
                    sub = "Feedback Sent"
                collected.append({
                    "title": step["title"],
                    "status": 2,
                    "creation": created,
                    "sub_title": sub
                })

            # Not started
            else:
                collected.append({
                    "title": step["title"],
                    "status": 0,
                    "creation": None
                })
        else:
            # No record at all
            collected.append({
                "title": step["title"],
                "status": 0,
                "creation": None
            })

    # Backfill: mark any earlier 0 as done if a later step is in progress/completed
    for i in range(len(collected)):
        if collected[i]["status"] == 0:
            if any(s["status"] in (1, 2) for s in collected[i+1:]):
                collected[i]["status"] = 1
                collected[i]["creation"] = None

    # Determine current application_status
    application_status = None
    # First look for an in-progress step
    for s in collected:
        if s["status"] == 2:
            application_status = {"title": s["title"], "status": 2}
            break

    # If none in progress, pick the most recent completed
    if not application_status:
        for s in reversed(collected):
            if s["status"] == 1:
                application_status = {"title": s["title"], "status": 1}
                break

    return {
        "stepper": collected,
        "application_status": application_status
    }


def check_mid_add(merchant):
    agreement=frappe.db.get_value("Merchant Subvention Agreement",{"merchant":merchant},"name")
    
    if not agreement:
        return 0
    
    mids=frappe.db.get_all("Merchant ID",filters={"parent":agreement},pluck="name")
    
    if not len(mids):
        return 1
    return 0
