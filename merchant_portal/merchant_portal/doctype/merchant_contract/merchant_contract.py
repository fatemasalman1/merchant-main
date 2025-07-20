# Copyright (c) 2024, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now
from frappe.utils.background_jobs import enqueue
from hijri_converter import Gregorian, Hijri

from merchant_portal.utils import (get_server_url, upload_file,
                                   validate_sign_up_user)


class MerchantContract(Document):
    def validate(self):
        self.get_hijiri_date()
        self.validate_contract_document()
        self.set_status()
        
    def before_submit(self):
        self.validate_subvention_data() 
        self.create_Merchant_subvention_agreement()
        
    def validate_subvention_data(self):
        fields=[{"payment_plan_offer":"Payment Plan Offer"},{"posting_date":"Contract Start Date"},{"end_date":"End Date"},{"investment":"Investment (Subvention Rate)"},{"monthly_price":"Monthly Price"}]
        self=self.as_dict()
        for f  in fields:
            for k,v in f.items():
                
                if not self[k]:
                    frappe.throw(_("{0} not found".format(v)))
                
    def create_Merchant_subvention_agreement(self):
        commercial_register,phone_number=frappe.db.get_value("Merchant",self.merchant,["commercial_register","phone_number"])
        subvention_agreement=frappe.new_doc("Merchant Subvention Agreement")
        subvention_agreement.merchant=self.merchant
        subvention_agreement.company_name=self.company_name
        subvention_agreement.commercial_register=commercial_register
        subvention_agreement.phone_number=phone_number
        subvention_agreement.merchant_offer=self.merchant_offer
        subvention_agreement.merchant_contract=self.name
        subvention_agreement.contract_start_date=self.posting_date
        subvention_agreement.contract_end_date=self.end_date
        subvention_agreement.payment_plan_offer=self.payment_plan_offer
        subvention_agreement.subvention_rate=self.monthly_price
        subvention_agreement.customer_acquisition=self.customer_acquisition_srbooking
        subvention_agreement.save()
        subvention_agreement.submit()
        frappe.msgprint("Merchant Subvention Agreement created succufully")
        
    def validate_contract_document(self):
        status_set = set()

        for row in self.contract_document:

            if row.status in status_set:
                if row.status!="Feedback Received":
                    frappe.throw(f"Duplicate status '{row.status}' is not allowed in the table.")

            status_set.add(row.status)
               
    
    @frappe.whitelist()
    def get_hijiri_date(self):
        if self.posting_date:
            gregorian_date = frappe.utils.data.getdate(self.posting_date)
            hijri_date = Gregorian(gregorian_date.year, gregorian_date.month, gregorian_date.day).to_hijri()
            self.hijiri_date = f"{hijri_date.year}-{hijri_date.month}-{hijri_date.day}"
    
    @frappe.whitelist()
    def send_contract(self):
        for row in self.contract_document:
            if row.status == "Pending":
                row.status= "Sent To Merchant"
                row.send_time=now()
                row.send_by=frappe.session.user
                self.create_log(row)
                self.save()
                self.send_contract_email()
                
    def send_contract_email(self):
        # Fetch the PDF file path from the `Merchant Contract` doctype
        pdf_file_path = self.pdf_file  # Ensure this points to the actual field storing the PDF file

        # Prepare the email arguments
        email_args = {
            "recipients": self.user,
            "sender": None,
            "subject": "New Contract Available on Baseeta Merchant Portal",
            "message": """
                Dear {0},

                We’re pleased to inform you that a new contract is available for you to review and sign. Please find the contract attached to this email, and log in to the Baseeta Merchant Portal for more details.

                Best regards,
                Baseeta Merchant Portal Team
            """.format(self.company_name),
            "header": ["New Contract Notification", "blue"],
            "attachments": [frappe.attach_print('Merchant Contract', self.name, file_name=pdf_file_path)],
            "delayed": False,
        }

        # Queue the email job to send the email with the PDF attachment
        enqueue(
            method=frappe.sendmail,
            queue="short",
            timeout=300,
            is_async=True,
            **email_args,
        )
        
  
    def create_log(self,row):
        log=frappe.new_doc("Merchant Contract Log")
        log.merchant_contract=self.name
        log.posting_datetime=now()
        log.row_name=row.name
        log.contract_pdf=row.document
        log.email=self.merchant_mail
        log.sent_by=frappe.session.user
        log.monthly_price=self.monthly_price
        log.type=self.type
        log.customer_acquisition_srbooking=self.customer_acquisition_srbooking
        log.entry_support_percentage=self.entry_support_percentage
        log.payment_plan_offer=self.payment_plan_offer
        log.stop_the_service_days=self.stop_the_service_days
        log.late_fine_days=self.late_fine_days
        log.late_fine_percentage=self.late_fine_percentage
        log.insert()
        
    @frappe.whitelist()
    def review_signed_cotract(self,answer,subject=None,message=None):
        
        if answer=="Rejected":
            self.status="Waiting Merchant Upload Contract"
            self.signed_contract_status="Rejected"
            self.subject=subject
            self.message=message
            self.create_contract_log(subject,message)
            self.send_invalid_contract_email(subject,message)
            
        if answer=="Accepted":
            self.signed_contract_status="Accepted"
            self.status="Contracted"
            self.docstatus=1
            frappe.db.set_value("Merchant",self.merchant,"status","Active (Contracted)") 
        
        self.save() 
            
    def send_invalid_contract_email(self,subject,message):
        # Fetch the PDF file path from the `Merchant Contract` doctype
        pdf_file_path = self.pdf_file  # Ensure this points to the actual field storing the PDF file

        # Prepare the email arguments
        email_args = {
            "recipients": self.user,
            "sender": None,
            "subject": subject,
            "message": """
                Dear {0},

               {1}

                Best regards,
                Baseeta Merchant Portal Team
            """.format(self.company_name,message),
            "header": ["New Contract Notification", "blue"],
            "attachments": [frappe.attach_print('Merchant Contract', self.name, file_name=pdf_file_path)],
            "delayed": False,
        }

        # Queue the email job to send the email with the PDF attachment
        enqueue(
            method=frappe.sendmail,
            queue="short",
            timeout=300,
            is_async=True,
            **email_args,
        )        
    def create_contract_log(self,subject,message):
        
        log=frappe.new_doc("Merchant Contract Log")
        log.merchant_contract=self.name
        log.posting_datetime=now()
        log.contract_pdf=self.pdf_file
        log.log_type="Update Contract (Issue)"
        log.email=self.merchant_mail
        log.sent_by=frappe.session.user
        log.monthly_price=self.monthly_price
        log.subject=subject
        log.message=message
        log.invaild_contract=self.signed_contract
        log.type=self.type
        log.customer_acquisition_srbooking=self.customer_acquisition_srbooking
        log.entry_support_percentage=self.entry_support_percentage
        log.payment_plan_offer=self.payment_plan_offer
        log.stop_the_service_days=self.stop_the_service_days
        log.late_fine_days=self.late_fine_days
        log.late_fine_percentage=self.late_fine_percentage
        log.insert()
         
    @frappe.whitelist()
    def generate_pdf_contract(self):
        self.validate_mandatory()
        pdf_file = frappe.get_print(
            self.doctype, self.name, "Merchant Contract",doc=self, as_pdf=True, letterhead="tasheel", no_letterhead=0
        )
        

  
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": f"{self.name}_contract.pdf",
            "content": pdf_file,
            "is_private": 0,
            "attached_to_doctype": self.doctype,
            "attached_to_name": self.name
        })
        

        file_doc.save()
        doc=frappe.get_doc("Merchant Contract",self.name)
        doc.append("contract_document",{
            "document":file_doc.file_url,
            "status":"Pending",
            "posting_date":now()
        })
        doc.status="Pending"
        
        doc.ready_to_send=0
           
        doc.pdf_file=file_doc.file_url
        doc.save()
        frappe.db.commit()
        if self.workflow_state != "Pending" :
            frappe.db.set_value("Merchant Contract",self.name,"workflow_state","Pending")
        frappe.msgprint(_("Contract PDF has been generated and attached successfully."))
        self.set_status()

    def set_status(self):
    
        if len(self.contract_document)+1>1:
              frappe.db.set_value("Merchant Contract",self.name,"not_first_time",1)
              frappe.db.set_value("Merchant Contract",self.name,"status","Pending (Waiting Review)")
            
        else:frappe.db.set_value("Merchant Contract",self.name,"not_first_time",0)
               
        if len(self.contract_document):
            if self.contract_document[-1].status in ["Sent To Merchant" , "Feedback Received"] and len(self.contract_document)<=3 and self.status!="Contracted":
                    
                    self.status=self.contract_document[-1].status
            if self.contract_document[-1].status =="Merchant Accepted" and len(self.contract_document)<=3 :
                    if self.status not in ["Waiting Review Uploaded Contract","Waiting Merchant Upload Contract","Contracted"]:
                        self.status="Waiting Review Uploaded Contract"
       
            if len(self.contract_document)>=3:
                status_list=[]
                for row in self.contract_document:
                    if row.status== "Feedback Received":
                        status_list.append(row.status)

                if len(status_list)>=3:
                    self.status="Closed"
                  
                    
                    self.docstatus=1
    def validate_mandatory(self):
        pass
        """Validates all mandatory fields"""
        
        fields = [
            "commercial_register",
            "issue_date",
            "telephone_1",
            "merchant_mail",
            "merchant_name",
            "merchant_job_title",
            "late_fine_days",
            "late_fine_percentage",
            "stop_the_service_days",
            "company_name",
            "address"
           
        ]
        for d in fields:
            if not self.get(d):
                frappe.throw(_("{0} is mandatory").format(self.meta.get_label(d)))

    @frappe.whitelist()
    def cancel_contract(self):
        for row in self.contract_document:
            if row.status =="Pending":
                self.contract_document.remove(row)

        self.save()


def get_merchant_contract(email):
    merchant=frappe.db.exists("Merchant", {"email_address": email})
    response_data={}
    if not merchant:
        return False,None
 
    contracts=frappe.db.get_all("Merchant Contract",{"merchant":merchant},pluck="name")
    if not len(contracts):
        return False,None
    for c in contracts:
        contract_child_table=frappe.db.get_all("Merchant Contract Document",{"status":"Sent To Merchant","parent":c },pluck="name")
        if  len(contract_child_table):
            
       
            response_data["form"]="Contract"
            response_data["doctype"]="Contract"
            response_data["status"]=frappe.db.get_value("Merchant Contract",c,"status")
            response_data["contract_id"]=c
            response_data["contract_document_id"]=contract_child_table[0]
        

            return True ,response_data

        contract_issues=frappe.db.get_all("Merchant Contract",{"status":"Waiting Merchant Upload Contract","name":c },pluck="name")
        
        if len(contract_issues):
            
            response_data["form"]="Contract Issue"
            response_data["doctype"]="Contract"
            response_data["contract_id"]=c
            response_data["subject"]=frappe.db.get_value("Merchant Contract",c,"subject")
            response_data["message"]=frappe.db.get_value("Merchant Contract",c,"message")
            

            return True ,response_data
    return False,None
@frappe.whitelist(methods=["POST"])
def merchant_contract_response(contract_id,contract_document_id,status,reason=None,feedback=None,):
    
    contract=frappe.db.exists("Merchant Contract",contract_id)
    if not contract:
        frappe.local.response["message"] = "Contract not found"
        frappe.throw("Contract not found")
    
 
    
    contract=frappe.get_doc("Merchant Contract",contract)
    if status == "Accept":
        image_dict = upload_file(frappe.request.files, "Merchant Contract", contract.name, "contract")
        pdf=image_dict["file_url"]
        contract.signed_contract=pdf
        contract.signed_contract_status="Pending"
        
        
    for i in contract.contract_document:
        if i.name == contract_document_id:

            if i.status != "Sent To Merchant":
                frappe.local.response["message"] = "Contract response Already submitted "
                frappe.throw("Contract response Already submitted")
    
            if status == "Decline":
                i.status="Feedback Received"
                i.reason= reason
                i.feedback=feedback
           
            if status == "Accept":
                i.status="Merchant Accepted"
                
                
          
            contract.save()

            return "success"
        
    frappe.local.response["message"] = "Contract Documnet Id  not found "
    frappe.throw("Contract Documnet Id  not found ")
    
    
@frappe.whitelist(methods=["POST"])
def merchant_issue_contract_response(contract_id):
    contract=frappe.db.exists("Merchant Contract",contract_id)
    if not contract:
        frappe.local.response["message"] = "Contract not found"
        frappe.throw("Contract not found")
    
 
    
    contract=frappe.get_doc("Merchant Contract",contract)
    
    image_dict = upload_file(frappe.request.files, "Merchant Contract", contract.name, "contract")
    pdf=image_dict["file_url"]
    contract.signed_contract=pdf
    contract.signed_contract_status="Pending"
    contract.status="Waiting Review Uploaded Contract"
    contract.save()
    return "success"
    
def   get_history_contract(email):
    merchant=frappe.db.exists("Merchant", {"email_address": email})
    data=[]
    if not merchant:
        return False,[]
 
    contracts=frappe.db.get_all("Merchant Contract",{"merchant":merchant},pluck="name")
    if not len(contracts):
        return False,[]
    
    for c in contracts:
        contract_child_table=frappe.db.get_all("Merchant Contract Document",filters={"status":["not in",["Sent To Merchant","Pending"]],"parent":c },fields=["*"])
        if not len(contract_child_table):
            return False,[]
        for con in contract_child_table:
            response_data={}
            response_data["doctype"]="Contract"
            response_data["contract_id"]=c
            response_data["contract_document_id"]=con["name"]
            response_data["status"]=con["status"]
            response_data["date"]=con["send_time"]
            data.append(response_data)
        

          
        return True ,data
        
@frappe.whitelist()
def get_merchant_contract_documents(contract_name):
    return frappe.get_all(
        "Merchant Contract Document",
        filters={
            "status": ["!=", "Feedback Received"],
            "parent": contract_name,
        },
        fields=["name"],
        ignore_permissions=True
    )
@frappe.whitelist()
def get_pending_contract_documents(contract_name):
    return frappe.get_all(
        "Merchant Contract Document",
        filters={
            "status": "Pending",
            "parent": contract_name,
        },
        fields=["name"],
        ignore_permissions=True
    )
@frappe.whitelist()
def get_pending_contract_for_cancellation(contract_name):
    return frappe.get_all(
        "Merchant Contract Document",
        filters={
            "status": "Pending",
            "parent": contract_name,
        },
        fields=["name"],
        ignore_permissions=True
    )     