# Copyright (c) 2025, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MerchantPortalSetting(Document):
    def validate(self):
        self._check_billing_fee_item()
        self._check_billing_day()

    def _check_billing_fee_item(self):
        """
        Ensure the billing fee item exists, is non-stock, and is enabled.
        """
        if not self.billing_fee_item:
            return

        item = frappe.db.get_value(
            "Item",
            self.billing_fee_item,
            ["is_stock_item", "disabled"],
            as_dict=True
        )
        if not item:
            frappe.throw(_("Item '{0}' does not exist.").format(self.billing_fee_item))

        if item.is_stock_item:
            frappe.throw(_("Item '{0}' must be non-stock.").format(self.billing_fee_item))

        if item.disabled:
            frappe.throw(_("Item '{0}' must be enabled.").format(self.billing_fee_item))

    def _check_billing_day(self):
        """
        Ensure billing day is between 1 and 28 inclusive.
        """
        if self.billing_day is None:
            return

        if not (1 <= self.billing_day <= 28):
            frappe.throw(_("Billing Day must be between 1 and 28."))