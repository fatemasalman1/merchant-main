# Copyright (c) 2024, Ahmed Ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now
from frappe.utils.background_jobs import enqueue


class MerchantLead(Document):
    def validate(self):
        pass
        # if not frappe.db.get_value("Registration Questionnaire",{"merchant_lead":self.name},"name"):
        #     if self.iban_number:
        #         try:
        #             frappe.enqueue(
        #                         queue="long",
        #                         method=self.create_registration_questionnaire(),
        #                         timeout=600,
                            
        #                         )
        #         except Exception:
        #             pass
        #         self.status="Convert to Registration"
    def before_submit(self):
        """Set the status to 'Convert to Registration' before submission."""
        self.status = "Convert to Registration"
      
    @frappe.whitelist()
    def create_registration_questionnaire(self):

        registration=frappe.new_doc("Registration Questionnaire")
        registration.company_name=self.company_name
        registration.email_address=self.email
        registration.first_name=self.full_name
        registration.paid_amount:self.paid_amount
        registration.company_link=self.company_link
        registration.integration_q=self.integration_q
        registration.co_markting_q=self.co_markting_q
        registration.phone_number=self.phone_number
        registration.iban_number=self.iban_number
        registration.type_of_business=self.type_of_business
        registration.business_category=self.business_category
        registration.wathq_status=self.wathq_status
        registration.response_code=self.response_code
        registration.response=self.response
        registration.merchant_representative = self.merchant_representative
        registration.job_title = self.job_title
        registration.wathq = self.wathq
        registration.response_json=self.response_json
        registration.commercial_register_status=self.commercial_register_status
        registration.commercial_register=self.commercial_register
        registration.annual_sales=self.annual_sales
        registration.annual_sales_digit=frappe.db.get_value("Merchant Annual Sales",self.annual_sales,"digit")
        registration.merchant_ticket_size=self.merchant_ticket_size
        registration.active_zakat=self.active_zakat
        registration.number_of_outlets=self.number_of_outlets
        registration.business_starting_date=self.business_starting_date
        registration.zakat_attacment=self.zakat_attacment
        for i in self.service_type:
            registration.append("service_type",{
                "service_type":i.service_type
            })
        registration.status="Pending"
        registration.active_vat=self.active_vat
        registration.vat_attachment=self.vat_attachment
        registration.iban=self.iban
        
       
        registration.national_id=self.national_id
        registration.commercial_register_status=self.commercial_register_status
        registration.annual_sales_digit=self.annual_sales_digit
        registration.merchant_lead=self.name
        registration.flags.ignore_permissions = True
        registration.flags.ignore_mandatory = True
     
        registration.insert()
       
       
        
        
         
    
        
        # frappe.msgprint("Registration Questionnaire Created")

    @frappe.whitelist()
    def check_sub_category(self, business_category):
        """
        Checks for subcategories within the given business category.
        Updates 'has_sub' and clears sub_category if subcategories are found.
        """
        if business_category:
            # Retrieve all subcategories for the selected business category
            subs = frappe.db.get_all(
                "Merchant Business Category Sub",
                filters={"parent": business_category},
                pluck="name"
            )
            # Update fields based on whether subcategories exist
            self.has_sub = 1 if subs else 0
            self.sub_category = [] if subs else self.sub_category
        else:
            self.has_sub = 0


 
   


    
    

   
