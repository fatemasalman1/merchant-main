# Copyright (c) 2024, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Priceandmethodofpaymenttemplate(Document):
	def validate(self):
		if self.default ==1 :
			check=frappe.db.get_all("Price and method of payment template",filters={"default":1,"name":["!=",self.name]},pluck="name")
			if len(check):
				frappe.throw("Default value already assign to {0}".format(check[0]))

