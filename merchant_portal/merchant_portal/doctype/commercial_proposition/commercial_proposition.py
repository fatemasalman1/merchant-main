# Copyright (c) 2024, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, add_years, today
from frappe.utils.background_jobs import enqueue


class CommercialProposition(Document):
    def before_insert(self):
        frappe.db.set_value("Merchant",self.merchant,"status","Onbording (Waiting to Offer)")
    def on_trash(self):
        frappe.db.set_value("Merchant",self.merchant,"status","Pending (Waiting to Onbording)")
        
    def  validate(self):
        self.check_proposition_selection()
        self.set_monthly_price()
    
    def set_monthly_price(self):
        if len(self.payment_plan_offer):
            self.monthly_price=round(self.payment_plan_offer[0].investment/self.payment_plan_offer[0].months,2)
            
    def check_proposition_selection(self):
        self.validate_muilti_selection()
        for i in self.payment_plan_offer:
            if i.selection == 1:
                if i.investment > 0:

                    self.monthly_price= round(i.investment/i.months,2)

    def validate_muilti_selection(self):
        value=0

        for i in self.payment_plan_offer:
            value+=i.selection

        if value > 1:
            frappe.throw("Please select one offer")

    @frappe.whitelist()
    def get_offer_data(self):
        # Convert the current document to a dictionary
        doc = self.as_dict()
        
        # Required fields for validation
        required_fields = ["offer_type", "business_category", "size"]
        
        # Validate required fields
        for field in required_fields:
            if not doc.get(field):
                frappe.throw(f"Please set <b>{field}</b>")
        
        # Fetch Commercial Proposition Engine based on business category and offer type
        pricing_controller = frappe.db.get_value(
            "Commercial Proposition Engine", 
            {
                "business_category": self.business_category,
                "offer_type": self.offer_type,
                "type": ["!=", "Customer Acquisition Support"]
            }, 
            "name"
        )
        
        if not pricing_controller:
            frappe.throw(f"Commercial Proposition Engine Not Found > Business Category: <b>{self.business_category}</b> && Offer Type: <b>{self.offer_type}</b>")
        
        pricing_controller_doc = frappe.get_doc("Commercial Proposition Engine", pricing_controller).as_dict()
        data = {}
        
        # Fetch relevant pricing data based on the offer type
        pricing_type = pricing_controller_doc.get("type")
        if pricing_type == "Subvention":
            data = self.get_subvention_data(pricing_controller_doc, data)
            self.type="Subvention"
        elif pricing_type == "Transaction Rebate":
            data = self.get_transaction_rebate_data(pricing_controller_doc, data)
            self.type="Transaction Rebate"
        if not data:
            frappe.throw(f"Commercial Proposition Engine Data Not Found > Business Category: <b>{self.business_category}</b> && Offer Type: <b>{self.offer_type}</b> && Size: {self.size}")
        
        # Populate payment plan offers
        self.payment_plan_offer = []
        plan_months={
            "3 Months": 3,
            "4 Months": 4,
            "6 Months": 6,
            "12 Months":12
        }
        for plan, investment in data.items():
            self.append("payment_plan_offer", {
                "payment_plan_offer": plan,
                "investment": investment,
                "months":plan_months[plan]
            })
        
        self.save()
        frappe.db.commit()
        
        # Handle co-marketing query and customer acquisition
        self.update_customer_acquisition()
        self.update_entry_pricing(pricing_controller_doc)

    def update_entry_pricing(self,pricing_controller_doc):
        if self.commercial_proposition_type == "New" and self.type== "Subvention":
            percent=frappe.db.get_value("Entry Pricing",{"parent":pricing_controller_doc.name,"size":self.size},"percent")
           
            if percent!= None:
                frappe.db.set_value("Commercial Proposition", self.name, "entry_support_percentage", f"{percent}%")
            else:
                frappe.db.set_value("Commercial Proposition", self.name, "entry_support_percentage","")




    def update_customer_acquisition(self):
        if self.co_markting_q == "Yes":
            rate = self.get_customer_acquisition_support_rate()
            frappe.db.set_value("Commercial Proposition", self.name, "customer_acquisition", f"{rate} ر.س")
            if rate == 0:
                return True
        else:
            frappe.db.set_value("Commercial Proposition", self.name, "customer_acquisition", "")

    def get_customer_acquisition_support_rate(self):
        rate = 0
        pricing_controller = frappe.db.get_value(
            "Commercial Proposition Engine", 
            {
                "business_category": self.business_category,
                "type": "Customer Acquisition Support"
            }, 
            "name"
        )
        
        if pricing_controller:
            pricing_controller_doc = frappe.get_doc("Commercial Proposition Engine", pricing_controller).as_dict()
            customer_acquisition_support = pricing_controller_doc.get("customer_acquisition_support", [])
            
            for support in customer_acquisition_support:
                if support.get("size") == self.size:
                    rate = support.get("rate", 0)
        
        return rate

    def get_subvention_data(self, pricing_controller_doc, data):
        subvention_tables = {
            "3 Months": "subvention_pricing_3",
            "4 Months": "subvention_pricing_4",
            "6 Months": "subvention_pricing_6",
            "12 Months": "subvention_pricing_12"
        }
        
        for label, table in subvention_tables.items():
            if table in pricing_controller_doc:
                for entry in pricing_controller_doc[table]:
                    if entry.get("size") == self.size:
                        data[label] = entry.get("percent")
        
        return data

    def get_transaction_rebate_data(self, pricing_controller_doc, data):
        rebate_table = "transaction_rebate"
        
        if rebate_table in pricing_controller_doc:
            for entry in pricing_controller_doc[rebate_table]:
                if entry.get("size") == self.size:
                    data["% of Total Transaction Value"] = entry.get("percent")
        
        return data

    @frappe.whitelist()
    def fetch_analysis_template(self):
        if self.competitive_analysis_template:
            self.competitive_analysis=[]
            
            template=frappe.db.get_all("Competitive Analysis",filters={"parent":self.competitive_analysis_template},fields=["*"])
            
            if len(template):
                
                for i in template:
                    self.append("competitive_analysis",{
                        "competitor":i.competitor,
                        "strengths":i.strengths,
                        "weaknesses":i.weaknesses
                    })

    @frappe.whitelist()
    def create_offer(self):
        if self.status!="Accepted":
            frappe.throw("Offer need approval")
        
        if self.merchant_approval_status not in ["Negotiate", "Pending","Closed","Expired"]:
            frappe.throw("Merchant Approval status must be one of  [Negotiate, Pending,Expired] to create new offer")

        offer= frappe.new_doc("Merchant Offer")
        offer.commercial_proposition=self.name
        offer.merchant=self.merchant
        offer.commercial_proposition_type=self.commercial_proposition_type
        offer.offer_type=self.offer_type
        offer.business_category=self.business_category
        offer.size=self.size
        offer.co_markting_q=self.co_markting_q
        offer.monthly_price=self.monthly_price
        offer.type=self.type
        offer.user=frappe.db.get_value("Merchant",self.merchant,"user")
        if self.customer_acquisition:
            offer.customer_acquisition=self.customer_acquisition
        offer.entry_support_percentage=self.entry_support_percentage
        offer.valid_for=self.valid_for
        if self.valid_for:
            if self.valid_for>0:
                offer.offer_start_date=today()
                offer.offer_end_date=add_days(today(),self.valid_for)

        # offer.status="Waiting For Response"
        for i in self.payment_plan_offer:
            offer.append("payment_plan_offer",{
                "payment_plan_offer":i.payment_plan_offer,
                "investment":i.investment,
                "months":i.months,
            
            })
        offer.flags.ignore_permissions = True
        offer.insert()
        frappe.db.set_value("Commercial Proposition",self.name,"merchant_approval_status","Offered")
        self.send_email()
        Url = frappe.utils.get_url_to_form("Merchant Offer",offer.name)
        frappe.msgprint("Merchant Offer created successfully ,  <a href={1} > {0} </a>".format(offer.name,Url))
    
    def send_email(self):
        email_args = {
            "recipients": self.user,
            "sender": None,
            "subject": "New Offer Available on Baseeta Merchant Portal",
            "message": """
                Dear {0},

                We’re excited to inform you that you have received a new offer. Please log in to the Baseeta Merchant Portal to review the offer details.

                You can access it in the Verification Center for further action.

                Best regards,
                Baseeta Merchant Portal Team
            """.format(self.company_name),
            "header": ["New Offer Notification", "blue"],
            "delayed": False,
        }

        enqueue(
            method=frappe.sendmail,
            queue="short",
            timeout=300,
            is_async=True,
            **email_args,
        )

    @frappe.whitelist()
    def create_merchan_contract(self):

        accepted_offer=frappe.db.get_all("Payment Plan Offer",filters={"parent":self.name,"selection":1},fields=["*"])
        if not len(accepted_offer):
            frappe.throw("Please select accepted offer")

        if self.status!="Accepted" or self.merchant_approval_status!="Accepted":
            frappe.throw("Offer need approval")
        merchant_doc=frappe.db.get_all("Merchant",filters={"name":self.merchant},fields=["*"])
       
        contract= frappe.new_doc("Merchant Contract")
        contract.merchant=self.merchant
        contract.user=self.user
        contract.posting_date=today()
        contract.end_date=add_years(today(),1)
        contract.commercial_register=merchant_doc[0]["commercial_register"]
        contract.issue_date=merchant_doc[0]["business_starting_date"]
        contract.merchant_mail=merchant_doc[0]["email_address"]
        contract.merchant_building_number=merchant_doc[0]["building_number"]
        contract.merchant_zip_code=merchant_doc[0]["zip_code"]
        contract.fax=merchant_doc[0]["fax"]
        contract.address=merchant_doc[0]["address"]
        contract.merchant_unit_number=merchant_doc[0]["unit_number"]
        contract.merchant_street_name=merchant_doc[0]["street_name"]
        contract.merchant_district_name=merchant_doc[0]["district_name"]
        contract.postal_box_1=merchant_doc[0]["postal_box_1"]
        contract.postal_box_2=merchant_doc[0]["postal_box_2"]
        contract.telephone_1=merchant_doc[0]["telephone_1"]
        contract.merchant_name=merchant_doc[0]["merchant_representative"]
        contract.merchant_job_title=merchant_doc[0]["job_title"]
        contract.commercial_proposition=self.name
        contract.merchant_offer=frappe.db.get_value("Merchant Offer",{"commercial_proposition":self.name,"status":"Accepted"},"name")
        contract.company_name=self.company_name
        contract.monthly_price=self.monthly_price
        contract.type=self.type
        contract.customer_acquisition_srbooking=self.customer_acquisition
        contract.entry_support_percentage=self.entry_support_percentage
        contract.payment_plan_offer=accepted_offer[0]["payment_plan_offer"]
        contract.investment=accepted_offer[0]["investment"]
        contract.company_representative_templete=frappe.db.get_value("Company Representative Templete",{"default":1},"name")
        contract.template=frappe.db.get_value("Price and method of payment template",{"default":1},"name")
        contract.flags.ignore_mandatory = True
        contract.insert()

        Url = frappe.utils.get_url_to_form("Merchant Contract",contract.name)
        frappe.msgprint("Merchant Contract created successfully ,  <a href={1} > {0} </a>".format(contract.name,Url))
        
            