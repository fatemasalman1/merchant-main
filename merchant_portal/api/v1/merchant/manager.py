import frappe
from merchant_portal.controller.maintenance_mode import maintenance_mode

# @frappe.whitelist(methods=["POST"])
@maintenance_mode
def set_merchant_representative(contract_id,name,job_title,id=None):
    merchant=frappe.db.exists("Merchant", {"email_address": frappe.session.user})
    if not merchant:
        frappe.local.response["message"] = frappe._("Merchant not found")
        frappe.throw("Merchant not found")
    
    merchant_doc=frappe.get_doc("Merchant",merchant)
    if id:
        found =0
        for m in merchant_doc.managers:
            if m.name == id:
                found=1
                m.is_representative=1
                merchant_doc.save()
        if not found:
            frappe.local.response["message"] = frappe._("Manager id  not found")
            frappe.throw("Manager id  not found")

    else:
        merchant_doc.append("managers",{
            "type":"Add By Merchant",
            "name1":name,
            "job_title":job_title,
            "is_representative":1
        })
        merchant_doc.save()
    

    frappe.db.set_value("Merchant Contract",contract_id,"merchant_name",name)
    frappe.db.set_value("Merchant Contract",contract_id,"merchant_job_title",job_title)

    
    frappe.local.response["message"] = frappe._("Merchant Representative add successfully")
    return