import json
from datetime import datetime

import frappe
from frappe.core.doctype.user.user import generate_keys
from frappe.utils import cint
from frappe.utils.password import update_password
from six.moves.urllib.parse import urlparse

from merchant_portal.controller.language_decorator import \
    set_language_from_header
from merchant_portal.controller.maintenance_mode import maintenance_mode
from merchant_portal.controller.rate_limit import rate_limit_exponential
from merchant_portal.controller.two_factor import (authenticate_for_2factor,
                                                   confirm_otp_token,
                                                   get_cached_user_pass,
                                                   should_run_2fa)
from merchant_portal.utils import (get_server_url, upload_file,
                                   validate_login_user)


@frappe.whitelist(allow_guest=True,methods=["POST"])
@rate_limit_exponential( key="user_id",limit=5,window=60,base_penalty=120,max_strikes=10)
# TODO remove otp from request (Shafi)
@maintenance_mode
@set_language_from_header
def email_verification(email,otp=None, tmp_id=None):
    
    status=validate_login_user(email)
    
    if status:
        authenticate_for_2factor(email,"Email")
        if otp and  tmp_id:

            if not confirm_otp_token(email,otp,tmp_id):
                
                    return False
            production=1
            if frappe.conf.get('production') == 0:
                    production = frappe.conf.get('production')
            api_key=None
            api_secret= None
            if not production:
                api_key ,api_secret=get_keys(email)
           
            frappe.local.response["message"] =frappe._("Success")
            frappe.local.response["data"] = {"name":email,"api_key": api_key,"api_secret":api_secret} 


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