import json
import os
from datetime import datetime

import frappe
import requests
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, get_url, now
from frappe.utils.background_jobs import enqueue
from hijri_converter import Gregorian, Hijri
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
                                   validate_sign_up_user)

REGISTRATION=None
DATA_LEAD=None


# TODO remove otp from request (Shafi)
@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit_exponential( key="user_id",limit=5,window=60,base_penalty=120,max_strikes=10)
@set_language_from_header
@maintenance_mode
def email_verification(email, full_name,commercial_register,mobile_number, otp=None, tmp_id=None):
    """
    Handles email verification. Creates a Merchant Lead if no OTP is provided.
    Confirms email verification when OTP and tmp_id are provided.
    """
    
    validate_sign_up_user(email)
    # Step 1: Validate the input
    if not full_name:
        frappe.local.response["message"] = frappe._("Please set full name")
        frappe.throw(_("Please set full name"))

    # Step 2: Check if a Merchant Lead already exists
    lead = frappe.db.get_value("Merchant Lead", {"email": email}, "name")
    if not lead:
        # Create lead if it doesn't exist
        lead = create_lead(email, full_name,mobile_number)
        frappe.local.response["message"] = frappe._("Lead created successfully.")
        frappe.local.response["lead_name"] = lead

    authenticate_for_2factor(email, "Email")

    # Step 3: Handle OTP verification
    if otp and tmp_id:
        

        # Confirm OTP
        if not confirm_otp_token(email, otp, tmp_id):
            frappe.throw(_("Invalid OTP or temporary ID."))

        # Fetch commercial register data and update the lead
        data = fetch_commercial_register(commercial_register, lead)
        if data:
            frappe.db.set_value("Merchant Lead", lead, "email_verified", 1)
            # frappe.db.set_value("Merchant Lead", lead, "company_name", data["business_name"])
            frappe.db.set_value("Merchant Lead", lead, "business_starting_date", data["business_starting_date"])
            frappe.db.set_value("Merchant Lead", lead, "paid_amount", data["paid_amount"])
            data["name"] = email
            frappe.local.response["message"] = frappe._("Email verified successfully.")
            frappe.local.response["data"] = data

            
def fetch_commercial_register(commercial_register, lead):
    """
    Validates the commercial register number and fetches data from Wathq API.
    """
    if  len(str(commercial_register)) != 10:
        frappe.local.response["message"] = frappe._("Commercial Register must be a 10-digit number")
        frappe.throw(_("Commercial Register must be a 10-digit number"))

    return get_commercial_register(commercial_register, lead)

def get_commercial_register(commercial_register, lead):
    """
    Fetches commercial register details from the Wathq API and updates the Merchant Lead.
    Handles API errors by setting failure status and response data.
    """
    setting = frappe.get_doc("Wathq Api Setting")
    if not setting.api_key:
        frappe.throw(_("Please set API Key in <b>Wathq Api Setting</b>"))

    url = f"https://api.wathq.sa/v5/commercialregistration/fullinfo/{commercial_register}"
    headers = {
        "accept": "application/json",
        "apiKey": setting.api_key
    }
    use_proxy = frappe.conf.get('enable_proxies') or 0
    if use_proxy:
   
        proxies = {
            "http": "http://10.0.10.11:3128",
            "https": "http://10.0.10.11:3128"
            }
    
        response = requests.get(url, headers=headers  ,proxies=proxies)
    else:
        response = requests.get(url, headers=headers  )
    if response.status_code== 404:
        frappe.local.response["message"] = frappe._("Commercial Register not found")
        frappe.throw(_("Commercial Register not found"))
        
    if response.status_code== 400:
        frappe.local.response["message"] = frappe._("Commercial Register is expired")
        frappe.throw(_("Commercial Register is expired"))  
          
    if response.status_code == 200:
        # Update Merchant Lead with API success response
        frappe.db.set_value("Merchant Lead", lead, "wathq_status", "Success")
        frappe.db.set_value("Merchant Lead", lead, "response_code", 200)

        data = response.json()
        frappe.db.set_value("Merchant Lead", lead, "response", str(data))
        frappe.db.set_value("Merchant Lead", lead, "response_json", json.dumps(data, ensure_ascii=False))
        frappe.db.set_value("Merchant Lead", lead, "commercial_register", commercial_register)
        # Extract and process the data
        response_data = {
            "business_name": data.get("crName"),
            "paid_amount":data.get("capital", 0).get("subscribedAmount", 0) or 0
        }

        if "issueDate" in data:
            hijri_date = data["issueDate"]
            hijri_year, hijri_month, hijri_day = map(int, hijri_date.split("/"))
            gregorian_date = Hijri(hijri_year, hijri_month, hijri_day).to_gregorian()
            response_data["business_starting_date"] = gregorian_date.strftime('%Y-%m-%d')
            response_data["business_starting_date_hijri"] = hijri_date

        # Extract manager details
        managers = [
            {"type": "Wathq", "name": party["name"], "job_title": party["relation"]["name"]}
            for party in data.get("parties", [])
            
        ]
        response_data["manager"] = managers

        frappe.db.commit()
        return response_data

    else:
    
        # Update Merchant Lead with API failure response
        handle_commercial_register_error(response, lead,commercial_register)

        frappe.db.set_value("Merchant Lead", lead, "email_verified", 1)
        frappe.db.set_value("Merchant Lead", lead, "wathq_status", "Failed")
        frappe.db.set_value("Merchant Lead", lead, "response_code", "Network Error")
        frappe.db.set_value("Merchant Lead", lead, "commercial_register", commercial_register)
        frappe.db.set_value("Merchant Lead", lead, "response", str(response.json()))
        frappe.db.commit()
        frappe.local.response["message"] = frappe._("Error  while fetching commercial register data from Wathq, Please try again later")
        frappe.throw(_("Error  while fetching commercial register data from Wathq, Please try again later"))

def get_proxies():
    http_proxy = os.getenv("HTTP_PROXY", "")
    https_proxy = os.getenv("HTTPS_PROXY", "")
    return {
        "http": http_proxy,
        "https": https_proxy
    }

def handle_commercial_register_error(response, lead,commercial_register):
    """
    Handles API errors and updates the Merchant Lead with the error response.
    """
    frappe.db.set_value("Merchant Lead", lead, "wathq_status", "Failed")
    frappe.db.set_value("Merchant Lead", lead, "response_code", response.status_code)
    frappe.db.set_value("Merchant Lead", lead, "commercial_register", commercial_register)
    try:
        error_response = response.json()
        frappe.db.set_value("Merchant Lead", lead, "response", json.dumps(error_response, ensure_ascii=False))
        frappe.db.set_value("Merchant Lead", lead, "status","Failed")
        error_message = error_response.get("message", "Unknown error")
        frappe.db.set_value("Merchant Lead", lead, "failed_message",error_message)
        frappe.db.commit()
        
    except ValueError:
        # If the response is not JSON, store raw text
        frappe.db.set_value("Merchant Lead", lead, "response", response.text)
        frappe.db.set_value("Merchant Lead", lead, "status","Failed")
        frappe.db.set_value("Merchant Lead", lead, "failed_message",error_message)
        
        frappe.db.commit()
        error_message = "Unexpected response format from API."
    
  
    frappe.local.response["message"] = frappe._(  _("Error {0}: {1}".format(response.status_code, error_message))
       )
 
    frappe.throw(
        _("Error {0}: {1}".format(response.status_code, error_message)),
        title="Wathq API Error"
    )



@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit_exponential( key="user_id",limit=5,window=60,base_penalty=120,max_strikes=10)
@maintenance_mode
@set_language_from_header
def sign_up(email, data):
    """
    Handles the sign-up process for a merchant. Creates a lead and enqueues
    a background job for processing the rest of the logic.
    """


    # Validate the user (stub for actual validation logic)
    status = validate_sign_up_user(email)
    if not status:
        frappe.throw(_("User validation failed for email: {0}".format(email)))

    # Check if Merchant Lead exists
    merchant_lead = frappe.db.exists("Merchant Lead", {"email": email})
    if not merchant_lead:
        frappe.throw(_("Please verify your email: {0}".format(email)))

    # Validate the input data
    valid_data = validate_data(data)

    # Create the lead and enqueue the rest of the logic
    lead_name = complete_lead_info(merchant_lead, valid_data)
    frappe.db.set_value("Merchant Lead",merchant_lead,"status","Scheduled")
    enqueue(
        "merchant_portal.controller.background_job_handler.background_job_handler",  # Replace with actual import path
        lead_name=lead_name,
        valid_data=valid_data,
        queue="long",
        
    )

    # Respond immediately to the client
    frappe.local.response["message"] = _("Your lead is created successfully, and the process will complete shortly.")
    frappe.local.response["lead_name"] = lead_name


def complete_lead_info(merchant_lead, valid_data):
        
        merchant_lead_doc = frappe.get_doc("Merchant Lead", merchant_lead)
        business_category_name = frappe.db.get_value("Translation", {
            "translated_text": valid_data["business_category"],
            "language": "ar"
        }, "source_text") or valid_data["business_category"]
        merchant_lead_doc.type_of_business = frappe.db.get_value("Merchant Business Categories",{"merchant_business_category":business_category_name},"parent")
        merchant_lead_doc.business_category = business_category_name
  
        annual_sales_name = frappe.db.get_value("Translation", {
            "translated_text": valid_data["annual_sales"],
            "language": "ar"
        }, "source_text") or valid_data["annual_sales"]
        
        merchant_lead_doc.annual_sales = annual_sales_name


        merchant_lead_doc.company_name=valid_data["company_name"]
        merchant_lead_doc.commercial_register=valid_data["commercial_register"]

        merchant_lead_doc.merchant_ticket_size = valid_data["merchant_ticket_size"]
        merchant_lead_doc.merchant_representative = valid_data["merchant_representative"]
        merchant_lead_doc.job_title = valid_data["job_title"]
        merchant_lead_doc.wathq = valid_data["wathq"]

     


        merchant_lead_doc.flags.ignore_permissions = True
        merchant_lead_doc.flags.ignore_validate_update_after_submit = True
        merchant_lead_doc.save()

        return merchant_lead_doc.as_dict()


def validate_data(data):
    """
    Validates the input data and ensures required fields and files are present.
    """
    try:
        valid_data = json.loads(data) if isinstance(data, str) else data
    except json.JSONDecodeError:
        frappe.throw(_("Invalid JSON input for data."))

    required_fields = [
        "business_category","commercial_register",
        "annual_sales","company_name",
        "merchant_ticket_size",
       
    ]


    # Validate required fields
    for field in required_fields:
        if field not in valid_data:
            frappe.throw(_("{0} not found in data.".format(field)))



    return valid_data

def create_lead(email, full_name,mobile_number):
    """
    Creates a Merchant Lead if it does not already exist, or updates the existing one.
    """
    merchant_lead = frappe.db.exists("Merchant Lead", {"email": email})

    if merchant_lead:
        # Update existing Merchant Lead
        merchant_lead = frappe.get_doc("Merchant Lead", merchant_lead)
        merchant_lead.update({
            "email": email,
            "full_name": full_name,
            "phone_number":mobile_number,
            "complete_1": 1,
            "status": "View",
        })
        merchant_lead.flags.ignore_permissions = True
        merchant_lead.save()
    else:
        # Create new Merchant Lead
        merchant_lead = frappe.new_doc("Merchant Lead")
        merchant_lead.update({
            "email": email,
            "full_name": full_name,
                "phone_number":mobile_number,
            "complete_1": 1,
            "status": "View",
        })
        merchant_lead.flags.ignore_permissions = True
        merchant_lead.insert()

    frappe.db.commit()
    return merchant_lead.as_dict()

