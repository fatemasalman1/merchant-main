# Copyright (c) 2025, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

class MIDUploaded(Document):
    """
    DocType: MID Uploaded
    Child Table: mids (MID Uploadeds)
    Fields:
      - posting_date (Date, default today)
      - status (Select: Pending, Partially Success, Success, Failed)
      - error_msg (Text)
      - mids (Table of child doctype MID Uploadeds)
          * mid (Data)
          * contract (Data)
          * status (Select: Success, Failed)
          * error_message (Text)
    """

    def on_submit(self):
        # Trigger MID upload processing when submitted
        self.process_mids()

    def process_mids(self):
        total = len(self.mids)
        success_count = 0
        fail_count = 0
        statuses = []

        for idx, row in enumerate(self.mids):
            try:
                # 1) Find the Merchant Subvention Agreement by w4u_contract_id
                msa_name = frappe.db.get_value(
                    "Merchant Subvention Agreement",
                    {"w4u_contract_id": row.contract},
                    "name"
                )
                if not msa_name:
                    frappe.throw(
                        _(f"No Merchant Subvention Agreement found for contract {row.contract}"),
                        title="MSA Not Found"
                    )

                # 2) Direct SQL insert into the child table `tabMerchant ID`
                frappe.db.sql(
                    """
                    INSERT INTO `tabMerchant ID`
                        (parent, parentfield, parenttype, mid, status)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        msa_name,
                        'mids',
                        'Merchant Subvention Agreement',
                        row.mid,
                        'Active'
                    )
                )
                frappe.db.commit()

                # Mark row success
                row.status = "Success"
                row.error_message = ""
                success_count += 1

            except Exception:
                # On error, capture traceback and mark row failed
                frappe.db.rollback()
                row.status = "Failed"
                row.error_message = frappe.get_traceback()
                fail_count += 1

            finally:
                # Publish per-row progress
                frappe.publish_realtime(
                    event="mid_upload_progress",
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

                # Persist child row status and error_message
                row.db_set("status", row.status)
                row.db_set("error_message", row.error_message or "")
                statuses.append(row.status)

        # Determine overall tool status
        if any(s == "Failed" for s in statuses) and any(s == "Success" for s in statuses):
            overall = "Partially Success"
        elif statuses and all(s == "Success" for s in statuses):
            overall = "Success"
        else:
            overall = "Failed"

        # Update parent record status
        self.db_set("status", overall)

        # Publish final completion event
        frappe.publish_realtime(
            event="mid_upload_complete",
            message={
                "docname": self.name,
                "overall_status": overall,
                "total": total,
                "success": success_count,
                "failed": fail_count
            },
            user=frappe.session.user
        )
