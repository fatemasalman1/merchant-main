import frappe



def create_integration_task(type,commercial_register,reference_type,reference_name,merchant):
    integration_hub=frappe.new_doc("Integration Hub")
    integration_hub.type=type
    integration_hub.commercial_register=commercial_register
    integration_hub.reference_type=reference_type
    integration_hub.reference_name=reference_name
    integration_hub.merchant=merchant
    integration_hub.flags.ignore_permissions = True
    integration_hub.insert()
    