import json
from datetime import datetime

import frappe
from frappe import _  # For translations
from frappe.utils import get_url
from frappe.utils.background_jobs import enqueue


def background_job_handler(lead_name, valid_data):
    """
    Handles the background job for processing leads and creating registration questionnaires.
    """
    try:
        # frappe.throw("hello")
        registration_name = create_registration_questionnaire(lead_name["name"])
        
        frappe.logger().info(f"Background job completed for lead: {lead_name}, registration: {registration_name}")
       
    except frappe.model.workflow.WorkflowPermissionError as workflow_error:
        pass  # Silently handle the error without interrupting the job
    except frappe.ValidationError as validation_error:
        # Handle other validation errors
        set_lead_error(lead_name["name"],validation_error)
        frappe.logger().error(f"Validation error while processing lead: {lead_name}. Error: {validation_error}")
      
    except Exception as general_error:
        set_lead_error(lead_name["name"],general_error)
        # Catch-all for other unexpected errors
        frappe.logger().error(f"Unexpected error while processing lead: {lead_name}. Error: {general_error}")

def create_registration_questionnaire(merchant_lead):
        """
        Creates a Registration Questionnaire document based on the Merchant Lead data.
        """
    # try:
        # Fetch the Merchant Lead document
        merchant_lead_doc = frappe.get_doc("Merchant Lead", merchant_lead)

        # Create a new Registration Questionnaire
        registration = frappe.new_doc("Registration Questionnaire")
        wathq_status="Active" if merchant_lead_doc.wathq_status=="Success" else "Inactive"
        registration.update({
            "company_name": merchant_lead_doc.company_name,
            "email_address": merchant_lead_doc.email,
            "first_name": merchant_lead_doc.full_name,
            "phone_number": merchant_lead_doc.phone_number,
            "company_link": merchant_lead_doc.company_link,
            "integration_q": merchant_lead_doc.integration_q,
            "paid_amount":merchant_lead_doc.paid_amount,
            "type_of_business": merchant_lead_doc.type_of_business,
            "business_category": merchant_lead_doc.business_category,
            "commercial_register": merchant_lead_doc.commercial_register,
            "annual_sales": merchant_lead_doc.annual_sales,
            "annual_sales_digit":frappe.db.get_value("Merchant Annual Sales",merchant_lead_doc.annual_sales,"digit"),
            "merchant_ticket_size": merchant_lead_doc.merchant_ticket_size,
            "active_zakat": merchant_lead_doc.active_zakat,
            "number_of_outlets": merchant_lead_doc.number_of_outlets,
            "business_starting_date": merchant_lead_doc.business_starting_date,
            "status": "Pending",
            "active_vat": merchant_lead_doc.active_vat,
            "commercial_register_status": merchant_lead_doc.get("commercial_register_status"),
            "annual_sales_digit": merchant_lead_doc.get("annual_sales_digit"),
            "merchant_lead": merchant_lead_doc.name,
            "merchant_representative":merchant_lead_doc.merchant_representative,
            "job_title":merchant_lead_doc.job_title,
            "wathq":merchant_lead_doc.wathq,
            "commercial_register_status":wathq_status,
            "response_json":merchant_lead_doc.response_json,
            "response_code":merchant_lead_doc.response_code,
            "response":merchant_lead_doc.response
            
        })

        # Append service types
        for service in merchant_lead_doc.get("service_type", []):
            registration.append("service_type", {"service_type": service.service_type})

        # Attach files if available
        file_fields = ["zakat_attacment", "vat_attachment", "iban"]
        for file_field in file_fields:
            file_url = merchant_lead_doc.get(file_field)
            if file_url:
                registration.set(file_field, file_url)

        # Save and return the Registration Questionnaire
        registration.flags.ignore_permissions = True
        registration.flags.ignore_mandatory = True
        registration.insert()

            # # Update Merchant Lead status
            # merchant_lead_doc.status = "Convert to Registration"
            # merchant_lead_doc.flags.ignore_permissions = True
            # merchant_lead_doc.save()
            
        return registration.name

    # except frappe.model.workflow.WorkflowPermissionError as workflow_error:
    #         # Log and continue without failing
    #         frappe.logger().warning(f"Workflow error while creating Registration Questionnaire for lead: {merchant_lead}. Error: {str(workflow_error)}")
    #         pass
    # except Exception as e:
    #         set_lead_error(merchant_lead,e)
    #         frappe.logger().error(f"Error while creating Registration Questionnaire: {str(e)}")
    #         raise frappe.ValidationError(_("Failed to create Registration Questionnaire. Error: {0}".format(str(e))))

def set_lead_error(lead_name,error):
    frappe.db.set_value("Merchant Lead",lead_name,"status","Failed")
    traceback = frappe.get_traceback(with_context=True)
    frappe.db.set_value("Merchant Lead",lead_name,"failed_message",str(traceback))
    failed_number=frappe.db.get_value("Merchant Lead",lead_name,"failed_number")
    if not failed_number:
        frappe.db.set_value("Merchant Lead",lead_name,"failed_number","1")
    else:
        frappe.db.set_value("Merchant Lead",lead_name,"failed_number",int(failed_number)+1)
    # frappe.db.commit()