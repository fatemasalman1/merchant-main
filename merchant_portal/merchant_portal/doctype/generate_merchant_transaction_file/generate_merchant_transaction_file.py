import frappe
import requests
import json
import os
from frappe.model.document import Document
from frappe import _
from frappe.utils.file_manager import save_file

class GenerateMerchantTransactionFile(Document):
    def validate(self):
        # 1. Retrieve W4U contract ID
        contract_id = self.fetch_contract_id()

        # 2. Call report-generation API
        data = self.call_report_api(contract_id)

        # 3. Process response
        if data and data.get('files'):
            # Remove previous attachments
            self.clear_attachment()
            # Resolve UNC and local path
            unc_path = data['files'][0]
            local_path = self.resolve_local_path(unc_path)
            # Save new report
            file_doc = self.save_report(local_path)
            self.file = file_doc.file_url
            self.error_message = ''
        else:
            # On failure, remove attachments & set error
            self.clear_attachment()
            self.file = None
            self.error_message = json.dumps(data or {})

    def clear_attachment(self):
        """
        Delete all existing File attachments for this document.
        """
        attachments = frappe.get_all(
            'File',
            fields=['name', 'file_name', 'file_url', 'is_private'],
            filters={'attached_to_doctype': self.doctype, 'attached_to_name': self.name}
        )
        for attachment in attachments:
            frappe.delete_doc('File', attachment.name, force=True)

    def fetch_contract_id(self):
        """
        Retrieve the active W4U contract ID for this merchant.
        """
        contract_id = frappe.get_value(
            'Merchant Subvention Agreement',
            {'merchant': self.merchant},
            'w4u_contract_id'
        )
        if not contract_id:
            frappe.throw(_(
                'No active Merchant Subvention Agreement found for merchant {0}'
            ).format(self.merchant))
        self.w4u_contract_id = contract_id
        return contract_id

    def call_report_api(self, contract_id):
        """
        Call external API to generate the report and return parsed JSON.
        """
        url = 'http://w4-ufx-api.tasheelfinance.com/api/merchant/generate-reports/'
        payload = {
            'requestedMerchants': [contract_id],
            'fromDate': self.from_date,
            'toDate': self.to_date
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        self.response_status = response.status_code
        return response.json() if response.ok else None

    def resolve_local_path(self, unc_path):
        """
        Convert a UNC path to the mounted local filesystem path.
        """
        parts = unc_path.lstrip('\\').split('\\')
        try:
            idx = parts.index('MERCHANT_TRANSACTIONS')
        except ValueError:
            frappe.throw(_(
                'Unexpected UNC structure, cannot find MERCHANT_TRANSACTIONS: {0}'
            ).format(unc_path))
        rel_parts = parts[idx+1:]

        mount_base = frappe.conf.get('merchant_transaction_mount') or "/mnt/merchant_transactions/Email_documents_UCFS/MERCHANT_TRANSACTIONS"
        local_path = os.path.join(mount_base, *rel_parts)
        if not os.path.exists(local_path):
            frappe.throw(_(
                'File not found at local path: {0}'
            ).format(local_path))
        return local_path

    def save_report(self, local_path):
        """
        Read bytes from local_path and save as Frappe File.
        """
        with open(local_path, 'rb') as f:
            file_bytes = f.read()
        file_name = os.path.basename(local_path)
        file_doc = save_file(file_name, file_bytes, self.doctype, self.name)
        return file_doc
