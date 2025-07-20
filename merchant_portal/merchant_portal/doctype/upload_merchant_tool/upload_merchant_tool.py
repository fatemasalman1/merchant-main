import frappe
from frappe.model.document import Document


class UploadMerchantTool(Document):
    """
    Doctype: Merchant Upload Records
    Child Table: records
    """
    def validate(self):
        self.check_duplicate_fields()

    def check_duplicate_fields(self):
        commercial_registers = set()
        emails = set()

        for row in self.get("records"):
            if row.commercial_register:
                if row.commercial_register in commercial_registers:
                    frappe.throw(
                        _("Duplicate Commercial Register found: {0}").format(row.commercial_register)
                    )
                commercial_registers.add(row.commercial_register)

            if row.email:
                if row.email in emails:
                    frappe.throw(
                        _("Duplicate Email found: {0}").format(row.email)
                    )
                emails.add(row.email)

    def on_submit(self):
        # Trigger processing on submit
        self.process_records()

    def process_records(self):
        total = len(self.records)
        success_count = 0
        fail_count = 0
        statuses = []

        for idx, row in enumerate(self.records):
            if frappe.db.get_value( "Merchant",{"commercial_register":row.commercial_register},"name"):

                continue
            

            
            try:
                frappe.flags.in_import = True
                # 1) Merchant
                merchant_doc = frappe.get_doc({
                    "doctype": "Merchant",
                    "commercial_register": row.commercial_register,
                    "company_name": row.company_name,
                    "email_address": row.email,
                    "phone_number": row.phone_number,
                    "uploaded":1
                })
                if row.contract_status == "INACTIVE":
                    merchant_doc.status = "Inactive (Waiting for renewal)"
                    merchant_doc.disabled = 1
                if row.contract_status == "ACTIVE":
                    merchant_doc.status = "Active (Contracted)"
                merchant = merchant_doc.insert(ignore_permissions=True)

                # 2) User
                user_doc = frappe.get_doc({
                    "doctype": "User",
                    "email": row.email,
                    "first_name": row.company_name,
                    "enabled": 1 if row.contract_status == "ACTIVE" else 0,
                    "send_welcome_email": 0
                }).insert(ignore_permissions=True)
                # Add Merchant role
                user_doc.add_roles("Merchant")

                # 3) Merchant Subvention Agreement
                msa_doc = frappe.get_doc({
                    "doctype": "Merchant Subvention Agreement",
                    "merchant": merchant.name,
                    "commercial_register": row.commercial_register,
                    "initial_transaction_date":row.billing_start_date,
                    "company_name": row.company_name,
                    "phone_number": row.phone_number,
                    "contract_start_date": row.contract_start_date,
                    "contract_end_date": row.contract_end_date,
                    "status": "Active",
                    "subvention_rate": row.subvention_rate,
                    "viban": row.viban,
                    "w4u_contract_id": row.w4u_contract_id,
                    "payment_plan_offer": row.tenor,
                    "registered": 1
                })
                if row.contract_status == "INACTIVE":
                    msa_doc.status = "Inactive"
                msa = msa_doc.insert(ignore_permissions=True)
                msa.flags.ignore_permissions = True
                msa.submit()
                # 4) Customer
                customer = frappe.get_doc({
                    "doctype": "Customer",
                    "customer_name": row.company_name,
                    "custom_merchant": merchant.name,
                    "customer_type":"Company",
                    "territory":"Saudi Arabia",
                    "custom_merchant_subvention_agreement": msa.name,
                    "custom_company_name": row.company_name,
                    "custom_w4u_contract_id": row.w4u_contract_id,
                    "custom_commercial_register": row.commercial_register
                }).insert(ignore_permissions=True)

               

                frappe.db.commit()
                row.status = "Success"
                row.error_message = ""
                success_count += 1

            except Exception:
                frappe.db.rollback()
                row.status = "Failed"
                row.error_message = frappe.get_traceback()
                fail_count += 1

            finally:
                # Publish per-row progress
                frappe.publish_realtime(
                    event="merchant_upload_progress",
                    message={
                        "docname": self.name,
                        "row_index": idx,
                        "row_status": row.status,
                        "total": total,
                        "success": success_count,
                        "failed": fail_count
                    },
                    user=frappe.session.user
                )
                # Persist row status
                row.db_set("status", row.status)
                row.db_set("error_message", row.error_message or "")
                statuses.append(row.status)

        # Compute overall status
        if any(s == "Failed" for s in statuses) and any(s == "Success" for s in statuses):
            overall = "Partially Success"
        elif statuses and all(s == "Success" for s in statuses):
            overall = "Success"
        else:
            overall = "Failed"

        # Update parent status
        self.db_set("status", overall)

        # Publish final completion event
        frappe.publish_realtime(
            event="merchant_upload_complete",
            message={
                "docname": self.name,
                "overall_status": overall,
                "total": total,
                "success": success_count,
                "failed": fail_count
            },
            user=frappe.session.user
        )

    def get_default_receivable_payable_account(self):
        company = frappe.defaults.get_global_default("company")
        if not company:
            frappe.throw(_("No Default Company set in Global Defaults"))
        company_doc = frappe.get_doc("Company", company)
        return company_doc.default_receivable_account
