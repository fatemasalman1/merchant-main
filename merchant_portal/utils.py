import frappe
from six.moves.urllib.parse import urlparse
from datetime import datetime
from frappe.utils import cint
from frappe.desk.form.linked_with import get_linked_doctypes
import json
from frappe import _
from frappe.core.utils import find
from frappe.desk.form.linked_with import get_linked_doctypes
from frappe.utils import cstr
def validate_sign_up_user(email):
    email_user=frappe.db.exists("User", {"name": email})
    enabled=frappe.db.get_value("User",email_user,"enabled")
    if enabled:
        merchant=frappe.db.exists("Merchant", {"email_address": email_user})
        if merchant:
            
            frappe.local.response["message"] = frappe._("User Already Exist , Please Login")
            frappe.local.response["data"] = {"name":merchant}
            frappe.throw("User Already Exist , Please Login")

    
    
    registration=frappe.db.get_value("Registration Questionnaire", {"email_address": email},"name")
    
    if registration:
            status=frappe.db.get_value("Registration Questionnaire", {"email_address": email},"status")
            if status in ["Pending","Waiting To Review"]:

                frappe.local.response["message"] =frappe._("User is already registered, under review")
                frappe.local.response["data"] = {"name":registration}
                frappe.throw("User is already registered, under review")
            
            if status == "Denial" :
                frappe.local.response["message"] =frappe._("Sorry ,Your registration has been denied")
                frappe.local.response["data"] = {"name":registration}
                frappe.throw("Sorry ,Your registration has been denied ")

           
    return True

def validate_login_user(email):
    email_user=frappe.db.exists("User", {"name": email})
    

    enabled=frappe.db.get_value("User",email_user,"enabled")
    if enabled and frappe.db.exists("Merchant", {"email_address": email,"disabled":0}):
         return True
    
    registration=frappe.db.get_value("Registration Questionnaire", {"email_address": email},"name")
    
    if registration:
            status=frappe.db.get_value("Registration Questionnaire", {"email_address": email},"status")
            if status in ["Pending","Waiting To Review"]:

                frappe.local.response["message"] =frappe._("Please Try Again Later, Under Review")
                frappe.local.response["data"] = {"name":registration}
                frappe.throw("Please Try Again Later, Under Review")
            
            if status == "Denial" :
                frappe.local.response["message"] =frappe._("Sorry ,Your registration has been denied")
                frappe.local.response["data"] = {"name":registration}
                frappe.throw("Sorry ,Your Account has been denied")
    
    merchant=frappe.db.exists("Merchant", {"email_address": email})
    
    if not merchant and email_user:
         frappe.local.response["message"] = frappe._("Sorry , your account has been suspended")
         frappe.throw("Sorry , your account has been suspended")

    if frappe.db.get_value("Merchant",merchant,"disabled"):
         frappe.local.response["message"] = frappe._("Sorry , your account has been suspended")
         frappe.throw("Sorry , your account has been suspended")
    
    if merchant and not email_user:
         frappe.local.response["message"] = frappe._("We couldn't find an account with that Email.")
         frappe.throw("We couldn't find an account with that Email.")
    
    if not merchant and not email_user:
         frappe.local.response["message"] = frappe._("We couldn't find an account with that Email.")
         frappe.throw("We couldn't find an account with that Email.")
    return True

def upload_file(files, doctype, docname,file_name):
    is_private = frappe.form_dict.is_private
    fieldname = frappe.form_dict.fieldname
    file_url = frappe.form_dict.file_url
    folder = frappe.form_dict.folder or "Home"
    filename = frappe.form_dict.file_name
    content = None
    image_url = {"file_url": ""}
    if file_name not in files:
        frappe.throw("{0} not found in Files".format(file_name))
    
    if files[file_name]:
            file = files[file_name]
            content = file.stream.read()
            filename = file.filename
            frappe.local.uploaded_file = content
            frappe.local.uploaded_filename = filename
            image = frappe.get_doc(
                {
                    "doctype": "File",
                    "attached_to_doctype": doctype,
                    "attached_to_name": docname,
                    "attached_to_field": fieldname,
                    "folder": folder,
                    "file_name": filename,
                    "file_url": file_url,
                    "is_private": cint(is_private),
                    "content": content,
                }
            ).save(ignore_permissions=True)

            image_url = {"file_url": image.file_url}

    return image_url

def get_server_url():
    base_url = frappe.request.url
    server_url = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(base_url))
    return server_url



@frappe.whitelist()
def add_user_permissions(data):
    """Add and update the user permissions"""

    if isinstance(data, str):
        data = json.loads(data)
    data = frappe._dict(data)

    # get all doctypes on whom this permission is applied
    perm_applied_docs = check_applicable_doc_perm(data.user, data.doctype, data.docname)
    exists = frappe.db.exists(
        "User Permission",
        {
            "user": data.user,
            "allow": data.doctype,
            "for_value": data.docname,
            "apply_to_all_doctypes": 1,
        },
    )
    if data.apply_to_all_doctypes == 1 and not exists:
        remove_applicable(perm_applied_docs, data.user, data.doctype, data.docname)
        insert_user_perm(
            data.user, data.doctype, data.docname, data.is_default, data.hide_descendants, apply_to_all=1
        )
        return 1
    elif len(data.applicable_doctypes) > 0 and data.apply_to_all_doctypes != 1:
        remove_apply_to_all(data.user, data.doctype, data.docname)
        update_applicable(perm_applied_docs, data.applicable_doctypes, data.user, data.doctype, data.docname)
        for applicable in data.applicable_doctypes:
            if applicable not in perm_applied_docs:
                insert_user_perm(
                    data.user,
                    data.doctype,
                    data.docname,
                    data.is_default,
                    data.hide_descendants,
                    applicable=applicable,
                )
            elif exists:
                insert_user_perm(
                    data.user,
                    data.doctype,
                    data.docname,
                    data.is_default,
                    data.hide_descendants,
                    applicable=applicable,
                )
        return 1
    return 0


def insert_user_perm(
    user, doctype, docname, is_default=0, hide_descendants=0, apply_to_all=None, applicable=None
):
    user_perm = frappe.new_doc("User Permission")
    user_perm.user = user
    user_perm.allow = doctype
    user_perm.for_value = docname
    user_perm.is_default = is_default
    user_perm.hide_descendants = hide_descendants
    if applicable:
        user_perm.applicable_for = applicable
        user_perm.apply_to_all_doctypes = 0
    else:
        user_perm.apply_to_all_doctypes = 1
  
    user_perm.flags.ignore_permissions = True
    user_perm.insert()


def remove_applicable(perm_applied_docs, user, doctype, docname):
    for applicable_for in perm_applied_docs:
        frappe.db.delete(
            "User Permission",
            {
                "applicable_for": applicable_for,
                "for_value": docname,
                "allow": doctype,
                "user": user,
            },
        )


def remove_apply_to_all(user, doctype, docname):
    frappe.db.delete(
        "User Permission",
        {
            "apply_to_all_doctypes": 1,
            "for_value": docname,
            "allow": doctype,
            "user": user,
        },
    )


def update_applicable(already_applied, to_apply, user, doctype, docname):
    for applied in already_applied:
        if applied not in to_apply:
            frappe.db.delete(
                "User Permission",
                {
                    "applicable_for": applied,
                    "for_value": docname,
                    "allow": doctype,
                    "user": user,
                },
            )
   
   
@frappe.whitelist()
def check_applicable_doc_perm(user, doctype, docname):
   
    applicable = []
    doc_exists = frappe.get_all(
        "User Permission",
        fields=["name"],
        filters={
            "user": user,
            "allow": doctype,
            "for_value": docname,
            "apply_to_all_doctypes": 1,
        },
        limit=1,
    )
    if doc_exists:
        applicable = get_linked_doctypes(doctype).keys()
    else:
        data = frappe.get_all(
            "User Permission",
            fields=["applicable_for"],
            filters={
                "user": user,
                "allow": doctype,
                "for_value": docname,
            },
        )
        for permission in data:
            applicable.append(permission.applicable_for)
    return applicable