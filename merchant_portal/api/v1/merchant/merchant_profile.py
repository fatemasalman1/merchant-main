import json

import frappe

from merchant_portal.controller.maintenance_mode import maintenance_mode
from merchant_portal.merchant_portal.doctype.merchant.merchant import \
    get_merchant_profile_data


@frappe.whitelist(methods=["GET"])
@maintenance_mode
def get_merchant_profile():
 
    user=frappe.session.user    
    merchant=frappe.db.exists("Merchant", {"email_address": user})
    
    if not merchant:
        frappe.local.response["message"] = "Merhcant Not Found"
        frappe.throw("Merhcant Not Found")

    frappe.has_permission("Merchant", doc=merchant, throw=True)

    response=get_merchant_profile_data(merchant)
    frappe.local.response["message"] = "success"
    frappe.local.response["data"] = response
    return


@frappe.whitelist(methods=["POST"])
@maintenance_mode
def update_merchant_details(data):
    user = frappe.session.user
    merchant_name = frappe.db.exists("Merchant", {"email_address": user})

    if not merchant_name:
        frappe.local.response["message"] = "Merchant Not Found"
        frappe.throw("Merchant Not Found")
    if isinstance(data, str):
        data = json.loads(data)
    allowed_fields = ["company_name", "email_address", "phone_number", "first_name", 
                      "company_link", "iban_number", "type_of_business", "business_category"]

    invalid_keys = [key for key in data.keys() if key not in allowed_fields]
    if invalid_keys:
        frappe.local.response["message"] = f"Invalid fields provided: {', '.join(invalid_keys)}"
        frappe.throw(f"Invalid fields provided: {', '.join(invalid_keys)}")

    merchant = frappe.get_doc("Merchant", merchant_name)
    
 
    for field, value in data.items():
        if field in allowed_fields:
            merchant.set(field, value)
    
    merchant.save()
    frappe.db.commit()
    frappe.local.response["message"] = "Merchant details updated successfully"


@frappe.whitelist(methods=["POST"])
@maintenance_mode
def add_store(data):
    user = frappe.session.user
    merchant_name = frappe.db.exists("Merchant", {"email_address": user})

    if not merchant_name:
        frappe.local.response["message"] = "Merchant Not Found"
        frappe.throw("Merchant Not Found")

    if isinstance(data, str):
        data = json.loads(data)
    # Allowed fields for stores
    allowed_fields = {"store_name", "store_website_url", "location", "description"}
    
    # Validate keys in data
    invalid_keys = [key for key in data.keys() if key not in allowed_fields]
    if invalid_keys:
        frappe.local.response["message"] = f"Invalid fields provided: {', '.join(invalid_keys)}"
        frappe.throw(f"Invalid fields provided: {', '.join(invalid_keys)}")

    # Fetch the merchant document and add a new row
    merchant = frappe.get_doc("Merchant", merchant_name)
    new_store = merchant.append("stores", {
        "store_name": data.get("store_name"),
        "store_website_url": data.get("store_website_url"),
        "location": data.get("location"),
        "description": data.get("description")
    })
    
    merchant.save()
    frappe.db.commit()

    # Return the name (row identifier) of the newly added row
    frappe.local.response["message"] = "Store added successfully"
    frappe.local.response["row_name"] = new_store.name


@frappe.whitelist(methods=["DELETE"])
@maintenance_mode
def delete_store(row_name):
    user = frappe.session.user
    merchant_name = frappe.db.exists("Merchant", {"email_address": user})

    if not merchant_name:
        frappe.local.response["message"] = "Merchant Not Found"
        frappe.throw("Merchant Not Found")
  
    # Fetch the merchant document
    merchant = frappe.get_doc("Merchant", merchant_name)

    # Find and remove the specified row by row_name
    store = next((store for store in merchant.stores if store.name == row_name), None)
    
    if not store:
        frappe.local.response["message"] = "Store Not Found"
        frappe.throw("Store Not Found")

    # Remove the store row and save
    merchant.remove(store)
    merchant.save()
    frappe.db.commit()
    frappe.local.response["message"] = "Store deleted successfully"


@frappe.whitelist(methods=["PUT"])
@maintenance_mode
def update_store(data):
    user = frappe.session.user
    merchant_name = frappe.db.exists("Merchant", {"email_address": user})

    if not merchant_name:
        frappe.local.response["message"] = "Merchant Not Found"
        frappe.throw("Merchant Not Found")
    if isinstance(data, str):
        data = json.loads(data)
    # Check that 'name' is provided in data
    row_name = data.get("name")
    if not row_name:
        frappe.local.response["message"] = "Row name (unique identifier) is required"
        frappe.throw("Row name (unique identifier) is required")

    # Allowed fields for update
    allowed_fields = {"store_name","store_website_url", "location", "description"}

    # Validate keys in data
    invalid_keys = [key for key in data.keys() if key not in allowed_fields and key != "name"]
    if invalid_keys:
        frappe.local.response["message"] = f"Invalid fields provided: {', '.join(invalid_keys)}"
        frappe.throw(f"Invalid fields provided: {', '.join(invalid_keys)}")

    # Fetch the merchant document and find the specific store row
    merchant = frappe.get_doc("Merchant", merchant_name)
    store = next((store for store in merchant.stores if store.name == row_name), None)
    
    if not store:
        frappe.local.response["message"] = "Store Not Found"
        frappe.throw("Store Not Found")

    # Update only allowed fields
    for field in allowed_fields:
        if field in data:
            store.set(field, data[field])
    
    merchant.save()
    frappe.db.commit()
    frappe.local.response["message"] = "Store updated successfully"

@frappe.whitelist(methods=["POST"])
@maintenance_mode
def add_management_contact(data):
    user = frappe.session.user
    merchant_name = frappe.db.exists("Merchant", {"email_address": user})

    if not merchant_name:
        frappe.local.response["message"] = "Merchant Not Found"
        frappe.throw("Merchant Not Found")
    if isinstance(data, str):
        data = json.loads(data)
    # Allowed fields for management_contact
    allowed_fields = {"job_title", "management_contact_name", "email", "phone_number", "more_info"}
    
    # Validate keys in data
    invalid_keys = [key for key in data.keys() if key not in allowed_fields]
    if invalid_keys:
        frappe.local.response["message"] = f"Invalid fields provided: {', '.join(invalid_keys)}"
        frappe.throw(f"Invalid fields provided: {', '.join(invalid_keys)}")

    # Fetch the merchant document and add a new row
    merchant = frappe.get_doc("Merchant", merchant_name)
    new_contact = merchant.append("management_contact", {
        "job_title": data.get("job_title"),
        "management_contact_name": data.get("management_contact_name"),
        "email": data.get("email"),
        "phone_number": data.get("phone_number"),
        "more_info": data.get("more_info")
    })
    
    merchant.save()
    frappe.db.commit()

    # Return the row name of the newly added row
    frappe.local.response["message"] = "Management contact added successfully"
    frappe.local.response["row_name"] = new_contact.name

@frappe.whitelist(methods=["DELETE"])
@maintenance_mode
def delete_management_contact(row_name):
    user = frappe.session.user
    merchant_name = frappe.db.exists("Merchant", {"email_address": user})

    if not merchant_name:
        frappe.local.response["message"] = "Merchant Not Found"
        frappe.throw("Merchant Not Found")
    
  
    # Fetch the merchant document
    merchant = frappe.get_doc("Merchant", merchant_name)

    # Find and remove the specified row by row_name
    contact = next((contact for contact in merchant.management_contact if contact.name == row_name), None)
    
    if not contact:
        frappe.local.response["message"] = "Management Contact Not Found"
        frappe.throw("Management Contact Not Found")

    # Remove the contact row and save
    merchant.remove(contact)
    merchant.save()
    frappe.db.commit()
    frappe.local.response["message"] = "Management contact deleted successfully"


@frappe.whitelist(methods=["PUT"])
@maintenance_mode
def update_management_contact(data):
    user = frappe.session.user
    merchant_name = frappe.db.exists("Merchant", {"email_address": user})

    if not merchant_name:
        frappe.local.response["message"] = "Merchant Not Found"
        frappe.throw("Merchant Not Found")
    if isinstance(data, str):
        data = json.loads(data)
    # Check that 'name' (row identifier) is provided
    row_name = data.get("name")
    if not row_name:
        frappe.local.response["message"] = "Row name (unique identifier) is required"
        frappe.throw("Row name (unique identifier) is required")

    # Allowed fields for update
    allowed_fields = {"job_title", "management_contact_name", "email", "phone_number", "more_info"}

    # Validate keys in data
    invalid_keys = [key for key in data.keys() if key not in allowed_fields and key != "name"]
    if invalid_keys:
        frappe.local.response["message"] = f"Invalid fields provided: {', '.join(invalid_keys)}"
        frappe.throw(f"Invalid fields provided: {', '.join(invalid_keys)}")

    # Fetch the merchant document and find the specific contact row
    merchant = frappe.get_doc("Merchant", merchant_name)
    contact = next((contact for contact in merchant.management_contact if contact.name == row_name), None)
    
    if not contact:
        frappe.local.response["message"] = "Management Contact Not Found"
        frappe.throw("Management Contact Not Found")

    # Update only allowed fields
    for field in allowed_fields:
        if field in data:
            contact.set(field, data[field])
    
    merchant.save()
    frappe.db.commit()
    frappe.local.response["message"] = "Management contact updated successfully"

import json

import frappe


@frappe.whitelist(methods=["POST"])
@maintenance_mode
def add_merchant_id(data):
    user = frappe.session.user
    merchant_name = frappe.db.exists("Merchant", {"email_address": user})
    
    if not merchant_name:
        frappe.local.response["message"] = "Merchant Not Found"
        frappe.throw("Merchant Not Found")
    
    agreement_name = frappe.db.exists("Merchant Subvention Agreement", {"merchant": merchant_name, "status": "Active"})
    
    if not agreement_name:
        frappe.local.response["message"] = frappe._("We couldn’t find an active Subvention Agreement linked to your account")
        frappe.throw(frappe._("We couldn’t find an active Subvention Agreement linked to your account"))

    if isinstance(data, str):
        data = json.loads(data)

    # Allowed fields for merchant_id
    allowed_fields = {"id","branch"}
   
    invalid_keys = [key for key in data.keys() if key not in allowed_fields]
   
    if invalid_keys:
        frappe.local.response["message"] = f"Invalid fields provided: {', '.join(invalid_keys)}"
        frappe.throw(f"Invalid fields provided: {', '.join(invalid_keys)}")

    # Check if MID already exists and is not disabled
    mid_exists = frappe.db.exists("Merchant ID", {
        "mid": data.get("id"),
        "status": ["!=", "Disabled"]
    })
    if mid_exists:
        frappe.local.response["message"] = frappe._("MID {0} already exists".format(data.get("id")))
        frappe.throw(frappe._("MID {0} already exists".format(data.get("id"))))

    # Check if MID exists but is disabled
    result = frappe.db.get_value("Merchant ID", {
        "mid": data.get("id"),
        "status": "Disabled"
    }, ["parent", "name"])

    subvention = None
    mid_name = None
    if result:
        subvention, mid_name = result

    # Load agreement document
    agreement = frappe.get_doc("Merchant Subvention Agreement", agreement_name)

    # Check if the disabled MID belongs to a different agreement
    if subvention and subvention != agreement.name:
        frappe.local.response["message"] = frappe._("MID {0} is already used by another merchant".format(data.get("id")))
        frappe.throw(frappe._("MID {0} is already used by another merchant".format(data.get("id"))))
  
    # Reactivation flow
    if mid_name:
        for i in agreement.mids:
            if i.name == mid_name:
                i.status = "Reactive Requested"
                
        agreement.save(ignore_permissions=True)
        row_name = mid_name
        message = "Reactivation request set successfully"

    # New MID flow
    else:
        new_row = agreement.append("mids", {
            "mid": data.get("id"),
            "status": "Pending",
            "branch":data.get("branch")
        })
        agreement.save(ignore_permissions=True)
        row_name = new_row.name  # This is now set after saving
        message = "MID added successfully"

    frappe.local.response["message"] = message
    frappe.local.response["row_name"] = row_name
    frappe.local.response["success"] = True


@frappe.whitelist(methods=["DELETE"])
@maintenance_mode
def delete_merchant_id(row_name):
    user = frappe.session.user
    merchant_name = frappe.db.exists("Merchant", {"email_address": user})

    if not merchant_name:
        frappe.local.response["message"] = "Merchant Not Found"
        frappe.throw("Merchant Not Found")

    agreement = frappe.db.exists("Merchant Subvention Agreement", {"merchant": merchant_name, "status": "Active"})
    
    if not agreement:
        frappe.local.response["message"] = frappe._("We couldn’t find an active Subvention Agreement linked to your account")
        frappe.throw("We couldn’t find an active Subvention Agreement linked to your account")

    # Fetch the agreement document
    agreement = frappe.get_doc("Merchant Subvention Agreement", agreement)

    # Find the row in the child table
    row_to_delete = None
    for row in agreement.mids:
        if row.name == row_name:
            row_to_delete = row
            break
    if not row_to_delete:
        frappe.local.response["message"] = frappe._("MID {0} not found".format(row_name))
        frappe.throw(frappe._("MID {0} not found".format(row_name)))    
    
    if row.status == "Disable Requested":
        frappe.local.response["message"] = frappe._("Request already submitted")
        frappe.throw("Request already submitted")
    
    if row.status== "Active":
        
        frappe.db.sql("""
                UPDATE `tabMerchant ID`
                SET status = 'Disable Requested'
                WHERE parent = %s AND mid = %s
            """, (agreement.name, row.mid))

        frappe.db.commit()
        enqueue_create_integration_hub_task(agreement,row.mid)
        frappe.local.response["message"] = "Remove Request created  successfully"
        
        
    if row.status in ["Failed","Pending"]:   
        agreement.mids.remove(row_to_delete)
        agreement.save(ignore_permissions=True)
        frappe.local.response["message"] = "Merchant ID deleted successfully"

@frappe.whitelist(methods=["PUT"])
@maintenance_mode
def update_merchant_id(data):
    user = frappe.session.user
    merchant_name = frappe.db.exists("Merchant", {"email_address": user})

    if not merchant_name:
        frappe.local.response["message"] = "Merchant Not Found"
        frappe.throw("Merchant Not Found")

    agreement = frappe.db.exists("Merchant Subvention Agreement", {"merchant": merchant_name, "status": "Active"})
    
    if not agreement:
        frappe.local.response["message"] = frappe._("We couldn’t find an active Subvention Agreement linked to your account")
        frappe.throw("We couldn’t find an active Subvention Agreement linked to your account")

    if isinstance(data, str):
        data = json.loads(data)

    # Check that 'name' (row identifier) is provided
    row_name = data.get("name")
    if not row_name:
        frappe.local.response["message"] = "Row name (unique identifier) is required"
        frappe.throw("Row name (unique identifier) is required")

    # Allowed fields for update
    allowed_fields = {"id", "branch"}

    # Validate keys in data
    invalid_keys = [key for key in data.keys() if key not in allowed_fields and key != "name"]
    if invalid_keys:
        frappe.local.response["message"] = f"Invalid fields provided: {', '.join(invalid_keys)}"
        frappe.throw(f"Invalid fields provided: {', '.join(invalid_keys)}")

    # Fetch the agreement document
    agreement = frappe.get_doc("Merchant Subvention Agreement", agreement)

    # Find the row to update
    row_to_update = None
    for row in agreement.mids:
        if row.name == row_name:
            row_to_update = row
            break

    if not row_to_update:
        frappe.local.response["message"] = frappe._("MID {0} not found".format(row_name))
        frappe.throw(frappe._("MID {0} not found".format(row_name)))

    # # Check if the new MID is the same as the old one
    # if row_to_update.mid == data.get("id"):
    #     frappe.local.response["message"] = frappe._("No changes made because old and new MID are the same")
    #     frappe.throw("No changes made because old and new MID are the same")

    # Check if MID is in an uneditable state
    if row_to_update.status != "Pending":
        frappe.local.response["message"] = "Unable to update MID"
        frappe.throw("Unable to update MID in (Active or Suspended) status")

    # Update MID
    row_to_update.mid = data.get("id")
    row_to_update.branch=data.get("branch")

    # Save the document
    agreement.save(ignore_permissions=True)

    frappe.local.response["message"] = "Merchant ID updated successfully"

@frappe.whitelist(methods=["PUT"])
@maintenance_mode
def update_merchant_details(data):
    user = frappe.session.user
    merchant_name = frappe.db.exists("Merchant", {"email_address": user})

    if not merchant_name:
        frappe.local.response["message"] = "Merchant Not Found"
        frappe.throw("Merchant Not Found")
    if isinstance(data, str):
        data = json.loads(data)
    # Fetch the merchant document
    merchant = frappe.get_doc("Merchant", merchant_name)
    
    # Allowed fields to update
    allowed_fields = {
        "phone_number", "first_name", 
        "company_link", "iban_number", "type_of_business", "business_category"
    }
    
    # Validate that all keys in data are allowed fields
    invalid_keys = [key for key in data.keys() if key not in allowed_fields]
    if invalid_keys:
        frappe.local.response["message"] = f"Invalid fields provided: {', '.join(invalid_keys)}"
        frappe.throw(f"Invalid fields provided: {', '.join(invalid_keys)}")

    # Update fields based on provided data
    for field, value in data.items():
        if field in allowed_fields:
            merchant.set(field, value)
    
    # Save changes to the merchant document
    merchant.save()
    frappe.db.commit()

    frappe.local.response["message"] = "Merchant details updated successfully"

@frappe.whitelist(methods=["GET"])
@maintenance_mode
def get_merchant_representative():
    user = frappe.session.user
    merchant_name = frappe.db.exists("Merchant", {"email_address": user})

    if not merchant_name:
        frappe.local.response["message"] = "Merchant Not Found"
        frappe.throw("Merchant Not Found")
    data={}
    data["merchant_representative"]=frappe.db.get_value("Merchant",merchant_name,"merchant_representative")
    data["job_title"]=frappe.db.get_value("Merchant",merchant_name,"job_title")

    frappe.local.response["data"] = data
    return

@frappe.whitelist(methods=["GET"])
@maintenance_mode
def validate_merchant():
    user = frappe.session.user
    merchant_name = frappe.db.exists("Merchant", {"email_address": user})
    if merchant_name:
        frappe.local.response["valid"] = 1
        return
    
    frappe.local.response["valid"] = 0
    return

@frappe.whitelist()
def enqueue_create_integration_hub_task(docname, mid):
    frappe.enqueue(
        method=create_integration_hub_task,
        queue='default',
        timeout=300,
        is_async=True,
        doc=docname,
        mid=mid
    )

def create_integration_hub_task(doc,mid):
        integration = frappe.new_doc("Integration Hub")
        integration.type = "RemoveMid"
        integration.reference_type = "Merchant Subvention Agreement"
        integration.reference_name = doc.name
        integration.commercial_register = doc.commercial_register
        integration.merchant = doc.merchant
        integration.append("mids", {"mid": mid})
        integration.flags.ignore_permissions = True
        integration.insert()
        frappe.db.commit()
        