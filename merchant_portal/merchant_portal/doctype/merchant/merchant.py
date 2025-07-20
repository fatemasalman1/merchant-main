# Copyright (c) 2024, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Merchant(Document):
  
        
    @frappe.whitelist()
    def create_commercial_proposition(self):
        commercial_proposition=frappe.new_doc("Commercial Proposition")
        commercial_proposition.merchant=self.name
        commercial_proposition.company_name=self.company_name
        commercial_proposition.size=self.merchant_size
        commercial_proposition.co_markting_q=self.co_markting_q
        commercial_proposition.business_category=self.business_category
        commercial_proposition.user=self.user
        proposition=frappe.db.get_all("Commercial Proposition",filters={"merchant_approval_status":"Accepted","merchant":self.name},pluck="name")
        
        if len(proposition):
            commercial_proposition.commercial_proposition_type="Renewal"
        else:
            commercial_proposition.commercial_proposition_type="New"
        commercial_proposition.flags.ignore_mandatory = True
        commercial_proposition.flags.ignore_permissions = True
        commercial_proposition.insert()
        Url = frappe.utils.get_url_to_form("Commercial Proposition",commercial_proposition.name)
        frappe.msgprint("Commercial Proposition created successfully ,  <a href={1} > {0} </a>".format(commercial_proposition.name,Url))
        frappe.db.set_value("Commercial Proposition",commercial_proposition.name,"proposition_title","{0}-{1}".format(self.company_name,commercial_proposition.name))
    
def get_merchant_profile_data(merchant):
    response={}

    merchant=frappe.get_doc("Merchant",merchant)
    response["company_name"]=merchant.company_name
    response["email_address"]=merchant.email_address
    response["phone_number"]=merchant.phone_number
    response["full_name"]=merchant.first_name
    response["company_link"]=merchant.company_link
    response["iban_number"]=merchant.iban_number
    response["type_of_business"]=merchant.type_of_business
    response["business_category"]=merchant.business_category
    response["stores"]=merchant.stores
    response["management_contact"]=merchant.management_contact
    response["mid_editable"]=0
    if merchant.status=="Active (Contracted)":
        response["mid_editable"]=1
    mids=[]
    agreement=frappe.get_value("Merchant Subvention Agreement", {"merchant": merchant.name},"name")
    
    if agreement:
        mids_record=frappe.db.get_all("Merchant ID",filters={"parent":agreement,"docstatus":1},fields=["name","mid","branch","status"])
        
        if len(mids_record):
            mids=mids_record
            
    response["merchant_id"]=mids
    return response

