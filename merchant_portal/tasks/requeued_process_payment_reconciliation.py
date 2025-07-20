import frappe


def requeued_process_payment_reconciliation():
        agreements=frappe.db.get_all("Merchant Subvention Agreement",filters={"docstatus":1},pluck="name")
      
        if not len(agreements):
            return
        
        for g in agreements:
            customer= frappe.db.get_value("Customer",{"custom_merchant_subvention_agreement":g},"name")
            if not customer:
                continue
          
            payment=frappe.get_doc({
                "doctype": "Process Payment Reconciliation",
                "party_type": "Customer",
                "party": customer,
                "receivable_payable_account": get_default_receivable_payable_account(),
                "default_advance_account":get_default_receivable_payable_account(),
            }).insert(ignore_permissions=True, ignore_mandatory=True)
            payment.flags.ignore_mandatory = True

            payment.flags.ignore_permissions = True
            payment.submit() 
                
def get_default_receivable_payable_account():
        """Fetch the company’s default receivable account from the Company master."""
        company = frappe.defaults.get_global_default("company")
        if not company:
            frappe.throw("No Default Company set in Global Defaults")
        company_doc = frappe.get_doc("Company", company)
        return company_doc.default_receivable_account
