# Copyright (c) 2024, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests
from datetime import datetime
from frappe.utils.data import evaluate_filters
from hijri_converter import Hijri, Gregorian
from frappe import _, msgprint, qb
# from frappe.core.doctype.user_permission.user_permission import add_user_permissions
from frappe.core.doctype.user.user import generate_keys
from passlib.utils import generate_password
from frappe.utils.background_jobs import enqueue
import json
from ....utils import add_user_permissions
import os
class RegistrationQuestionnaire(Document):
   
     
    
   
    def before_insert(self):
        self.get_commercial_register()
        
       
        if not self.new_password_email:
            self.create_user()
            
       
            
    def validate(self):
        if self.merchant_lead:
            frappe.db.set_value("Merchant Lead", self.merchant_lead,"status","Convert to Registration")
            
        self.fetch_annual_sales_digt()
        months=self.get_months()

        if months:
            self.business_starting_by_months=months

        self.get_mac_percentage()
        
        self.get_merchant_size()
        
    
    def before_submit(self):
        
        self.validate_data()
        self.validate_approval()
        
        if self.status=="Waiting To Review":
            self.status="Manually Approved"
            self.create_merchant()

    def create_user(self):
        
        not_exist = self.check_if_exist()
        
        if not_exist:
            # Create a new user document if it doesn't exist
            user_name = self.create_user_doc()
            user = frappe.get_doc("User", user_name)
        else:
            # Get the existing user document
            user = frappe.get_doc("User", self.user)

        user.flags.ignore_permissions = True
        
        # Always generate a new password and setup the user
        self.setup_user(user, generate_new_password=True)
        self.user = user.name


    def check_if_exist(self):
        user = frappe.db.exists("User", {"name": self.email_address})
        if not user:
            return True
        
        # Store the existing user for later setup
        self.user = user
        return False


    def create_user_doc(self):
        user = frappe.new_doc("User")
        user.email = self.email_address
        user.username = self.first_name
        user.first_name = self.first_name
        user.send_welcome_email = 0
        user.enabled = 1

        user.flags.ignore_permissions = True  # Ignore permissions when creating the user
        user.flags.ignore_mandatory = True
        user.flags.ignore_password_policy = True
        user.insert()
        frappe.db.commit()

        # Store the current user and switch to Administrator
        current_user = frappe.session.user
        try:
            frappe.set_user('Administrator')  # Switch to the Administrator user to bypass permissions
            generate_keys(user=user.name)  # Generate API keys as Administrator
        finally:
            frappe.set_user(current_user)  # Switch back to the original user

        return user.name



    def setup_user(self, user, generate_new_password=False):
        # Always generate a new password
        password = generate_password(6)
        self.temp_password = password  # Temporary attribute for this instance
        user.new_password = password
        user.flags.ignore_password_policy = True  # Allow setting the password
        user.save(ignore_permissions=True)  # Save the password to the database
        frappe.db.commit()

        # Store the generated password for further use
        self.new_pass = password

        # Send the email with the new password
        self.send_email(password, user.email)

        # Remove existing roles and assign the "Merchant" role
        user_roles = frappe.get_roles()
        user.remove_roles(*user_roles)
        user.add_roles("Merchant")

        # Create custom permission for the user
        self.create_permission(user.name, "User", user.name)
        
        # Allow the user to set a new password
        frappe.db.set_value("User", user.name, "custom_allow_new_password", 1)
        return user.name


    def send_email(self, password, email_address):
        
        email_args = {
            "recipients": email_address,
            "sender": None,
            "subject": "Temporary Password",
            "message": f"Your Temporary Password is: {password}",
            "header": [_("Temporary Password"), "blue"],
            "delayed": False,
        }
        enqueue(
            method=frappe.sendmail,
            queue="short",
            timeout=300,
            event=None,
            is_async=True,
            job_name=None,
            now=False,
            **email_args,
        )
        self.new_password_email=1
        frappe.db.set_value(self.doctype, self.name, "new_password_email", 1)
        frappe.db.commit()
    def create_permission(self, user, doctype, value):
      
        data = get_params(user, doctype, value)
        add_user_permissions(data)
    @frappe.whitelist()
    def create_merchant(self):
        
       
        merchant=frappe.new_doc("Merchant")
        merchant.company_name=self.company_name
       
        merchant.registration_questionnaire=self.name
        merchant.first_name=self.first_name
        merchant.last_name=self.last_name
        merchant.email_address=self.email_address
        merchant.company_logo=self.company_logo
        merchant.phone_number=self.phone_number
        merchant.company_link=self.company_link
        merchant.integration_q=self.integration_q
        merchant.co_markting_q=self.co_markting_q
        merchant.type_of_business=self.type_of_business
        merchant.business_category=self.business_category
        merchant.service_type=self.service_type
        for i in self.sub_category:
            merchant.append("sub_category",{
                "business_category_sub":i.business_category_sub
            })
        merchant.commercial_register=self.commercial_register
        merchant.wathq_status=self.wathq_status
        merchant.annual_sales=self.annual_sales
        merchant.iban_number=self.iban_number
        merchant.annual_sales_digit=self.annual_sales_digit
        merchant.commercial_register_status=self.commercial_register_status
        merchant.merchant_ticket_size=self.merchant_ticket_size
        merchant.number_of_outlets=self.number_of_outlets
        merchant.business_starting_date=self.business_starting_date
        merchant.business_starting_by_months=self.business_starting_by_months
        merchant.iban=self.iban
        merchant.active_zakat=self.active_zakat
        merchant.zakat_attacment=self.zakat_attacment
        merchant.active_vat=self.active_vat
        merchant.vat_attachment=self.vat_attachment
        merchant.mac_percentage=self.mac_percentage
        merchant.automate_approval=self.automate_approval
        merchant.approved=self.approved
        merchant.merchant_representative=self.merchant_representative
        merchant.job_title=self.job_title
        merchant.wathq=self.wathq
        merchant.approved_by=self.approved_by
        merchant.merchant_size=self.merchant_size
        merchant.user=self.user
        for i in self.stores:
            merchant.append("stores",{
                "store_name":i.store_name,
                "store_website_url":i.store_website_url,
                "location":i.location,
                "description":i.description,
            })

        for i in self.merchant_id:
            merchant.append("merchant_id",{
                "id":i.id
            })
        for i in self.management_contact:
            merchant.append("management_contact",{
                "job_title":i.job_title,
                "name1":i.name1,
                "email":i.email,
                "phone_number":i.phone_number,
                "more_info":i.more_info,
            })
        merchant.response_code=self.response_code
        merchant.response=self.response
        merchant.response_json=self.response_json
       

        if str(self.response_code) == "200":
            r_j = json.loads(self.response_json)

            # General Address Info
            general = r_j.get("address", {}).get("general", {})
            national = r_j.get("address", {}).get("national", {})

            merchant.zip_code = general.get("zipcode")
            merchant.telephone2 = general.get("telephone2")
            merchant.fax = general.get("fax1")
            merchant.address = general.get("address")
            merchant.postal_box_1 = general.get("postalBox1")
            merchant.postal_box_2 = general.get("postalBox2")

            # National Address Info
            if national:
                merchant.building_number = national.get("buildingNumber")
                merchant.street_name = national.get("streetName")
                merchant.district_name = national.get("districtName")
                merchant.unit_number = national.get("unitNumber")
                # Fallback to general telephone if not in national
                merchant.telephone_1 = general.get("telephone1")

            # Board members
            parties = r_j.get("parties", [])
            for party in parties:
                name = party.get("name")
                job_title = party.get("relation", {}).get("name")
                if name and job_title:
                    merchant.append("managers", {
                        "name1": name,
                        "job_title": job_title

                    })
        merchant.insert(ignore_permissions=True)
        Url = frappe.utils.get_url_to_form("Merchant",merchant.name)
        frappe.msgprint("Merchant created successfully ,  <a href={1} > {0} </a>".format(merchant.name,Url))
    def validate_approval(self):
        
        if not self.approved and self.status != "Denial":
            frappe.throw("Please connect with manager , this merchant need approved")
        
        self.approved_by=frappe.session.user

    def validate_data(self):
        if not self.commercial_register_status:
            frappe.throw("Please set <b>Commercial Register Status</b> , you can fetch data from wathq or set manually")
        if not self.business_starting_date:
                frappe.throw("Please set <b>Business Starting Date</b> , you can fetch data from wathq or set manually")

    @frappe.whitelist()
    def get_months(self,business_starting_date=None):
        business_starting=self.business_starting_date
        if business_starting_date:
            business_starting=business_starting_date
        if business_starting:
            # Get the current date
            current_date = datetime.now().date()
            
            # Convert business_starting_date to date format
            business_starting_date = frappe.utils.getdate(business_starting)
            
            # Check if the business start date is in the past
            if business_starting_date > current_date:
                frappe.throw("Business Starting Date cannot be in the future.")
            
            # Calculate the number of months between the two dates
            months_difference = (current_date.year - business_starting_date.year) * 12 + (current_date.month - business_starting_date.month)
            
            return months_difference
    
    def fetch_annual_sales_digt(self):
        if self.annual_sales:
            digit=frappe.db.get_value("Merchant Annual Sales",self.annual_sales,"digit")
            
            self.annual_sales_digit=digit
            
    @frappe.whitelist()
    def get_commercial_register(self,commercial_register=None,save=None):
        pass
        # if commercial_register:
        #     commercial_register=commercial_register
        # if self.commercial_register:
        #     commercial_register=self.commercial_register
        # if not commercial_register:
        #     frappe.throw("Please set Commercial Register")
        # setting=frappe.get_doc("Wathq Api Setting")
        # if not setting.api_key:
        #     frappe.throw("Please set Api Key in <b>Wathq Api Setting</b>")
           
        # url = "https://api.wathq.sa/v5/commercialregistration/fullinfo/{0}".format(commercial_register)
        # headers = {
        #     "accept": "application/json",
        #     "apiKey": setting.api_key  
        # }
       
        # proxies = {
        # "http": "http://10.0.10.11:3128",
        # "https": "http://10.0.10.11:3128"
        # }

        # response = requests.get(url, headers=headers,proxies=proxies)
        
        # if response.status_code == 200:
        #     self.wathq_status="Success"
        #     self.response_code=200
        #     data = response.json()
        #     self.response=str(data)

        #     if "status" in data:
        #         if data["status"]["id"]=="active":
        #             self.commercial_register_status="Active"
            
        #     if "issueDate"in data:
        #         hijri_date = data["issueDate"]

        #         # Split the date to get the year, month, and day
        #         hijri_year, hijri_month, hijri_day = map(int, hijri_date.split("/"))

        #         # Convert the Hijri date to Gregorian
        #         gregorian_date = Hijri(hijri_year, hijri_month, hijri_day).to_gregorian()

        #         # Format the Gregorian date as YYYY-MM-DD
        #         formatted_gregorian_date = gregorian_date.strftime('%Y-%m-%d')
        #         months=self.get_months(formatted_gregorian_date)
                
        #         self.business_starting_date=formatted_gregorian_date
        #         self.business_starting_by_months=months
                
        # else:
            
        #     self.wathq_status="Failed"
        #     self.response_code=response.status_code
            
        #     self.wathq_status="Failed"
        #     self.response_code=response.status_code
        #     data = response.json()
        #     self.response=str(data)
            
      
        # self.get_mac_percentage()
        

    @frappe.whitelist()
    def get_mac_percentage(self):
        
            
            number_of_row=0
            valid_row=0
            rejected_row=0
            point = 0
            accepted_row=[]
            rejected_rows=[]
            mac = frappe.get_doc("Pre-Defined MAC")
            if mac:

                for d in mac.criteria:
                    number_of_row+=1
                    
                        
                    result = evaluate_filters(
                        self, [("Registration Questionnaire", d.field, d.condition, d.value)]
                    )
                    
                    if result:
                    
                        accepted_row.append(d)
                        valid_row+=1
                        point += d.weight
                    else:
                    
                        rejected_row+=1
                        rejected_rows.append(d)

        
            self.mac_percentage = point
            
            if point>=mac.merchant_score_automate_approval and self.commercial_register_status=="Active":
                self.automate_approval=1
                self.approved=1
              
              
                self.status="Automated Approved"

                if self.docstatus!=1:
                
                    
                    self.flags.ignore_permissions = True
                    self.submit()
                    frappe.enqueue(
                    queue="short",
                    method=self.create_merchant(),
                    timeout=600,
                
                    )
                
            
            elif point<mac.merchant_score_automate_approval and self.commercial_register_status=="Active":
                self.status="Waiting To Review"
            elif point<mac.merchant_score_automate_approval and self.commercial_register_status!="Active" and self.status !="Denial" :
                self.status="Pending"
            else: 
                self.automate_approval=0
                self.approved=0
              
    def create_approved_workflow_doc(self):
        
        workflow_action=frappe.new_doc("Workflow Action")
        workflow_action.status="Completed"
        
        workflow_action.reference_doctype=self.doctype
        workflow_action.workflow_state="Pending"
        workflow_action.completed_by_role="Head of Commercial"
        workflow_action.completed_by="Administrator"
        workflow_action.append("permitted_roles", {"role": "Head of Commercial"})
        workflow_action.user="Administrator"
        workflow_action.flags.ignore_permissions = True
        workflow_action.flags.ignore_mandatory = True
        workflow_action.insert()
       
        frappe.db.set_value("Workflow Action",workflow_action.name,"reference_name",self.name)
        frappe.db.commit()
    @frappe.whitelist()
    def get_merchant_size(self):
        number_of_rows = 0
        valid_rows = 0
        rejected_rows_count = 0
        point = 0
        accepted_rows = []
        rejected_rows = []
        field_points = {}  # To keep track of highest points per field
        
        score_setting = frappe.get_doc("Merchant Sizing Engine")
        
        if score_setting:
            for d in score_setting.merchant_scoring:
                number_of_rows += 1
                if d.field in [
                    "service_type",
                   
                ]:
                    result = self.get_muliti_select_value(d.field, d.condition, d.value)
                else:
                # Evaluate conditions for each scoring field
                    result =  evaluate_filters(
                        self, [("Registration Questionnaire", d.field, d.condition, d.value)]
                    )

                if result:
                    # Check if this field already has a higher point, if not, update it
                    if d.field not in field_points or d.point > field_points[d.field]:
                        field_points[d.field] = d.point
                    
                    accepted_rows.append(d)
                    valid_rows += 1
                else:
                    rejected_rows_count += 1
                    rejected_rows.append(d)

            # Sum the highest points for each field
            point = sum(field_points.values())
           
            # Calculate merchant size based on accumulated points
            size = self.get_class(score_setting, point)
            self.merchant_size = size
    
    def get_muliti_select_value(self, field, condition, value):
        self = self.as_dict()
        field_value = self[field]
        values_list = []
        for i in field_value:
            values_list.append(i[field])

        if condition == "in":

            if value in values_list:
                return True
            else:
                False
        if condition == "not in":
            if value not in values_list:
                return True
            else:
                False
    def get_class(self, case_scorecard, point):
        sorted_classes = sorted(
            case_scorecard.merchant_scoring_point, key=lambda x: x.point, reverse=False
        )

        result = None

        for row in sorted_classes:
            if point >= row.point:
                result = row.size

        return result
    @frappe.whitelist()
    def check_sub_category(self,business_category):
        if business_category:
            subs=frappe.db.get_all("Merchant Business Category Sub",filters={"parent":business_category},pluck="name")
            if len(subs):
                self.has_sub=1
                self.sub_category=[]
            else:
                self.has_sub=0
        else: self.has_sub=0

    @frappe.whitelist()
    def make_denail(self,message):
        
        self.status="Denial"
        self.denial_reason=message
        self.save()
        
        self.workflow_state="Rejected"
        self.submit()
def get_proxies():
        http_proxy = os.getenv("HTTP_PROXY", "")
        https_proxy = os.getenv("HTTPS_PROXY", "")
        return {
            "http": http_proxy,
            "https": https_proxy
        }        
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def set_catogery_filter(doctype, txt, searchfield, start, page_len, filters):
    if not filters.get("type_of_business"):
        frappe.msgprint("Please select Type of Business first.")
        return []

    
    category = qb.DocType("Merchant Business Categories")

    return (
        qb.from_(category)
        .select(category.merchant_business_category)
        .where((category.parent == filters.get("type_of_business")))
        .run()
    )
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def set_sub_catogery_filter(doctype, txt, searchfield, start, page_len, filters):
    if not filters.get("business_category"):
        frappe.msgprint("Please select Business Category  first.")
        return []

    
    category = qb.DocType("Merchant Business Category Sub")

    return (
        qb.from_(category)
        .select(category.business_category_sub)
        .where((category.parent == filters.get("business_category")))
        .run()
    )
def get_params(user, doctype, docname, is_default=0, hide_descendants=0, applicable=None):
        """Return param to insert"""
        param = {
            "user": user,
            "doctype": doctype,
            "docname": docname,
            "is_default": is_default,
            "apply_to_all_doctypes": 1,
            "applicable_doctypes": [],
            "hide_descendants": hide_descendants,
        }
        if applicable:
            param.update({"apply_to_all_doctypes": 0})
            param.update({"applicable_doctypes": applicable})
        return param    

def get_application_status(email):
    registration=frappe.db.exists("Registration Questionnaire", {"email_address": email})
    
    if not registration:
        frappe.local.response["message"] =frappe._("User Not found")
        frappe.throw(_("User Not found"))
    
    status=frappe.db.get_value("Registration Questionnaire",registration,"status")
    main_status_map={"Pending":"Submitted","Waiting To Review":"Submitted","Automated Approved":"Approved","Manually Approved":"Approved","Denial":"Rejected"}  
    data={}
    data["id"]=registration
    data["main_status"]=main_status_map[status]
    
    sub_status=""
    sub_status=status

    if status in ["Automated Approved","Manually Approved"]:
        sub_status= "Approved"

    if status == "Denial":
        data["sub_status"]=frappe.db.get_value("Registration Questionnaire",registration,"denial_reason")

    data["sub_status"]=sub_status
    decision_status =0

    if status in ["Automated Approved","Manually Approved","Denial"]:
        decision_status=1

    data["decision_status"]=decision_status
    
    progess_steps=[]
    progess_steps.append({"Application Submission":frappe.db.get_value("Registration Questionnaire",registration,"creation")})
    data["progess"]=progess_steps
    return data

        

    
