
import frappe
from frappe import _

from merchant_portal.controller.language_decorator import \
    set_language_from_header
from merchant_portal.controller.maintenance_mode import maintenance_mode


@frappe.whitelist(methods=["POST"])
@maintenance_mode
@set_language_from_header
def create_issue(issue_type,subject,description=None):

    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("You must be logged in to create an issue"), frappe.PermissionError)

    data = frappe._dict(frappe.local.form_dict)

    # mandatory field
    if not data.get("subject"):
        frappe.throw(_("Subject is mandatory"))



    merchant_link = frappe.db.get_value("Merchant", {"email_address": user}, "name")


    agr_link = None
    if  merchant_link:
        agr_link = frappe.db.get_value(
            "Merchant Subvention Agreement",
            {"merchant": merchant_link},
            "name"
        )

    issue = frappe.get_doc({
        "doctype": "Issue",
        "custom_user": user,
        "issue_type":issue_type,
        "raised_by":user,
        "subject": subject,
        "description": description,
        "custom_merchant": merchant_link,
        "custom_merchant_subvention_agreement": agr_link,
        "via_customer_portal": 1
    })
    issue.insert(ignore_permissions=True)
    return {"name": issue.name}



@frappe.whitelist(methods=["GET"])
@maintenance_mode
@set_language_from_header
def get_issues():

    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("You must be logged in to view your issues"), frappe.PermissionError)

    filters = {
        "via_customer_portal": 1,
        "custom_user": user
    }


    issues = frappe.get_all(
        "Issue",
        filters=filters,
        fields=[
            "name",
            "custom_user",
            "subject",
            "issue_type",
            "description",
            "custom_response_text",
            "opening_date",
            "status"
        ],
        order_by="creation DESC"
    )
    return {"issues": issues}