# Copyright (c) 2024, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class MerchantOffer(Document):

    def validate(self):
       
        self.check_offer_status()
            
    def check_offer_status(self):
        if self.status=="Negotiate":
            frappe.db.set_value("Commercial Proposition",self.commercial_proposition,"merchant_approval_status","Negotiate")
            frappe.db.set_value("Commercial Proposition",self.commercial_proposition,"status","Pending")
            frappe.db.set_value("Commercial Proposition",self.commercial_proposition,"workflow_state","Draft")
        
        if self.status=="Accepted":
            frappe.db.set_value("Commercial Proposition",self.commercial_proposition,"merchant_approval_status","Accepted")
            frappe.db.set_value("Commercial Proposition",self.commercial_proposition,"status","Accepted")
            frappe.db.set_value("Commercial Proposition",self.commercial_proposition,"workflow_state","Approved")
            selection=""
            for row in self.payment_plan_offer:
                if row.selection==1:
                    selection=row.payment_plan_offer
            

            commercial_proposition = frappe.get_doc("Commercial Proposition", self.commercial_proposition)
            for row in commercial_proposition.payment_plan_offer:
                if row.payment_plan_offer == selection:
                    commercial_proposition.monthly_price = round(row.investment / row.months, 2)
                    row.selection = 1  # Directly set in commercial_proposition's child table rows
            commercial_proposition.save()
            frappe.db.commit()
            commercial_proposition.submit()
            frappe.db.set_value("Merchant",self.merchant,"status","Offer (Waiting To Contract)")
            
        if self.status=="Closed":
            frappe.db.set_value("Commercial Proposition",self.commercial_proposition,"merchant_approval_status","Closed")
            frappe.db.set_value("Commercial Proposition",self.commercial_proposition,"status","Pending")
            frappe.db.set_value("Commercial Proposition",self.commercial_proposition,"workflow_state","Draft")
            
    def set_offer_expired(self):
        self.status="Expired"
        frappe.db.set_value("Commercial Proposition",self.commercial_proposition,"merchant_approval_status","Expired")
        frappe.db.set_value("Commercial Proposition",self.commercial_proposition,"status","Pending")
        frappe.db.set_value("Commercial Proposition",self.commercial_proposition,"workflow_state","Draft")
        self.save()

    @frappe.whitelist()
    def set_status(self,status):
        if status:
            self.status=status
        self.save()

    def on_trash(self):
        if self.status in ["Accepted","Negotiate","Closed"]:
            frappe.throw("Unable to delete [ Accepted , Negotiate , Closed ] Offer")
        
        else:
            frappe.db.set_value("Commercial Proposition",self.commercial_proposition,"merchant_approval_status","Pending")
            frappe.db.set_value("Commercial Proposition",self.commercial_proposition,"status","Pending")
            frappe.db.set_value("Commercial Proposition",self.commercial_proposition,"workflow_state","Draft")

def get_history_offers(email):
        merchant=frappe.db.exists("Merchant", {"email_address": email})
        response_data=[]
        if not merchant:
            return False,[]
        
        offers=frappe.db.get_all("Merchant Offer",{"merchant":merchant,"status":["in",["Accepted","Negotiate"]]},"name")
        if not len(offers):
            return False,[]
        
       
        for offer in offers:
            data={}
            data["doctype"]="Offer"
            data["merchant"]=merchant
            data["offer_id"]=offer
            offer=frappe.get_doc("Merchant Offer",offer)
            data["monthly_price"]=0
            data["date"]=offer.creation
            data["status"]=offer.status
            if offer.monthly_price:
                data["monthly_price"]=offer.monthly_price 

            data["type"]=None
            if offer.type:
                data["type"]=offer.type

            data["valid_for"]=None
            if offer.valid_for:
                data["valid_for"]=offer.valid_for
            
            data["customer_acquisition"]=None
            if offer.customer_acquisition != "0 ر.س":
                data["customer_acquisition"]=offer.customer_acquisition

            payment_plans=[]

            for plan in offer.payment_plan_offer:
                if plan.selection==1:
                    payment_plans.append({
                        "id":plan.name,
                        "payment_plan_offer":plan.payment_plan_offer,
                        "investment":plan.investment,
                        "monthly_price": round(plan.investment/plan.months,2),
                        "selection":1
                    })
            
            data["payment_plans"]=payment_plans
            note_msg=None
            if offer.size == "L":
                note_msg="No subvention will be charged for the first 3 months."
            data["note"]=note_msg
            
            response_data.append(data)
       
        return True, response_data
def get_merchant_offers(email):
        merchant=frappe.db.exists("Merchant", {"email_address": email})
        if not merchant:
            return False,None
        
        offer=frappe.db.get_value("Merchant Offer",{"merchant":merchant,"status":"Waiting For Response"},"name")
        if not offer:
            return False,None
       
        data={}
        data["form"]="Offer"
        
        data["doctype"]="Offer"
        data["merchant"]=merchant
        data["offer_id"]=offer
        offer=frappe.get_doc("Merchant Offer",offer)
        data["status"]=offer.status
        data["monthly_price"]=0
        if offer.monthly_price:
            data["monthly_price"]=offer.monthly_price 
        data["date"]=offer.creation
        data["type"]=None
        if offer.type:
            data["type"]=offer.type

        data["valid_for"]=None
        if offer.valid_for:
            data["valid_for"]=offer.valid_for
        
        data["customer_acquisition"]=None
        if offer.customer_acquisition != "0 ر.س":
            data["customer_acquisition"]=offer.customer_acquisition

        payment_plans=[]

        for plan in offer.payment_plan_offer:
           
            payment_plans.append({
                "id":plan.name,
                "payment_plan_offer":plan.payment_plan_offer,
                "investment":plan.investment,
                "monthly_price": round(plan.investment/plan.months,2)
                
            })
        
        data["payment_plans"]=payment_plans
        note_msg=None
        if offer.size == "L":
                note_msg="No subvention will be charged for the first 3 months."
        data["note"]=note_msg
        if not offer.get_seen:
            frappe.db.set_value("Merchant Offer",offer.name,"seen_by_merchant",1)
            frappe.db.set_value("Merchant Offer",offer.name,"seen_datetime",now_datetime())
            frappe.db.set_value("Merchant Offer",offer.name,"get_seen",1)
            frappe.db.commit()
            
        return True, data
        
def merchant_offer_response(merchant,offer_id,status,reason,feedback,id):
    merchant=frappe.db.exists("Merchant",merchant)
    if not merchant:
        frappe.local.response["message"] = "Merchant not found"
        frappe.throw("Merchant not found")
    
    offer=frappe.db.get_value("Merchant Offer",offer_id,"name")	
    if not offer:
        frappe.local.response["message"] = "Offer not found"
        frappe.throw("Offer not found")
    
    offer=frappe.get_doc("Merchant Offer",offer)
    if offer.status != "Waiting For Response":
        frappe.local.response["message"] = "Offer response Already submitted "
        frappe.throw("Offer response Already submitted")
    
    if status == "Decline":
           offer.status="Negotiate"
           offer.decline_reason= reason
           offer.feedback=feedback
    found=0
    if status == "Accept":
        for plan in offer.payment_plan_offer:

            if plan.name == id:
                plan.selection=1
                found=1
                offer.monthly_price=round(plan.investment/plan.months,2)
                
        offer.status="Accepted"
        if not found:
            frappe.local.response["message"] = "Choose ID not found"
            frappe.throw("Choose ID not found")
    offer.save()

    return "success"




