import frappe
from frappe import _
from frappe.core.doctype.user.user import generate_keys
from frappe.utils.password import update_password

from merchant_portal.controller.language_decorator import \
    set_language_from_header
from merchant_portal.controller.maintenance_mode import maintenance_mode
from merchant_portal.controller.rate_limit import rate_limit_exponential
from merchant_portal.controller.two_factor import (authenticate_for_2factor,
                                                   confirm_otp_token,
                                                   get_cached_user_pass,
                                                   should_run_2fa)
from merchant_portal.utils import validate_login_user


@frappe.whitelist(allow_guest=True,methods=["POST"])
@rate_limit_exponential( key="user_id",limit=5,window=60,base_penalty=120,max_strikes=10)
@maintenance_mode
@set_language_from_header
def login(email,pwd,otp=None,tmp_id=None):
   
    if not frappe.db.exists("User", email):
        frappe.local.response["message"] = frappe._("User Not Found , Please Register")
        frappe.throw(_("User Not Found , Please Register"))
    login_manager = frappe.auth.LoginManager()
    login_manager.authenticate(user=email, pwd=pwd)

    
    
    # validate_login_user(email)
    authenticate_for_2factor(email,"Email")
    if otp and  tmp_id:

        if not confirm_otp_token(email,otp,tmp_id):
                return False
        new_pass=frappe.db.get_value("User",email,"custom_allow_new_password")
        language=frappe.db.get_value("User",email,"language")
        production=1
        if frappe.conf.get('production') == 0:
            production = frappe.conf.get('production')
        
        api_key=None
        api_secret= None
        if  production != 1:
            api_key ,api_secret=get_keys(email)
        
        frappe.set_user(email)
        frappe.local.login_manager.user = email
        frappe.form_dict.pop("pwd", None)
        frappe.local.login_manager.post_login()
        frappe.clear_messages()
        frappe.local.response["status_code"] = 200
        frappe.local.response["message"] = "Authentication success"
        frappe.local.response["home_page"] = ""
        frappe.local.response["new_password"] =new_pass
        frappe.local.response["language"] =language
        frappe.local.response["data"] = {
            "api_key": api_key,"api_secret":api_secret,
            "merchant": frappe.db.get_value("Merchant",{"user":email},"name"),
            "user_id": email,
            "full_name": frappe.db.get_value("User",{"name":email},"full_name"),
        }
        return

@frappe.whitelist(allow_guest=True,methods=["POST"])
@maintenance_mode
@set_language_from_header
def opt_verification_and_change_password(email,otp,tmp_id,pwd):
  
    if not confirm_otp_token(email,otp,tmp_id):
                    return False
    

    api_key ,api_secret=get_keys(email)
    frappe.set_user(email)
    frappe.local.response["data"] = {
        "api_key": api_key,"api_secret":api_secret,
        "merchant": frappe.db.get_value("Merchant",{"user":email},"name"),
        "user_id": email,
        "full_name": frappe.db.get_value("User",{"name":email},"full_name"),
    }
    frappe.local.response["message"] = frappe._("OTP verification successful")
    return 



def get_keys(email):
        api_key = frappe.db.get_value("User", email, "api_key")
        if not api_key:
            frappe.set_user('Administrator')
            generate_keys(email)
            api_key = frappe.db.get_value("User", email, "api_key")
        api_secret = frappe.utils.password.get_decrypted_password(
            "User", email, fieldname="api_secret"
        )
        return api_key ,api_secret