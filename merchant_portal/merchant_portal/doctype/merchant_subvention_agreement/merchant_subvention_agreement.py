# Copyright (c) 2025, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MerchantSubventionAgreement(Document):
    
    def on_update_after_submit(self):
        self.check_mid_duplicate()
    def before_submit(self):
       
        self.create_agreement_log()
        # self.create_customer()
    
    def before_cancel(self):
        log=frappe.db.get_all("Merchant Subvention Agreement Log",filters={"merchant_subvention_agreement":self.name},pluck="name")
        
        if len(log):
            for i in log:
                frappe.delete_doc("Merchant Subvention Agreement Log", i)
    
                
    def create_agreement_log(self):
        log=frappe.new_doc("Merchant Subvention Agreement Log")
        log.merchant=self.merchant
        log.company_name=self.company_name
        log.phone_number=self.phone_number
        log.merchant_subvention_agreement=self.name
        log.commercial_register=self.commercial_register
        log.merchant_offer=self.merchant_offer
        log.merchant_contract=self.merchant_contract
        log.contract_start_date=self.contract_start_date
        log.subvention_rate=self.subvention_rate
        log.contract_end_date=self.contract_end_date
        log.payment_plan_offer=self.payment_plan_offer
        log.customer_acquisition=self.customer_acquisition
        log.insert()
    
    def create_customer(self):
        customer=frappe.new_doc("Customer")
        customer.customer_name
        
    def check_mid_duplicate(self):
        for i in self.mids:
            parent=frappe.db.get_all("Merchant ID",filters={"mid":i.mid,"name":["!=",i.name]},pluck="mid")
            if len(parent):
                frappe.local.response["message"] = frappe._("MID :{0} already registered".format(i.mid))
                frappe.throw(frappe._("MID :{0} already registered".format(i.mid)))
        