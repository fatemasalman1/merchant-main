# Copyright (c) 2024, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CommercialPropositionEngine(Document):
	def validate(self):
		self.duplicate_size()
		if self.type=="Customer Acquisition Support":
			self.offer_type="None"

		self.check_type_not_change()
		if self.type == "Transaction Rebate" or self.type == "Subvention":
			if self.offer_type=="None":
				frappe.throw("Offer type must be on of (Hi-Proposition / Med-Proposition / Low-Proposition)")
	
	def check_type_not_change(self):
		if self.type !="Customer Acquisition Support":
			type=frappe.db.get_all(
			"Commercial Proposition Engine", filters=
			{"business_category": self.business_category, "name": ["!=", self.name],"type":["!=","Customer Acquisition Support"]},pluck="type")
			if not len(type):
				return
			
			if self.type not in type:
				frappe.throw("Wrong Type , {0}  >> {1} , you can change this by delete onther doctype , Type is unique in engine".format(self.business_category,self.type))

	def duplicate_size(self):
		doc= self.as_dict()
		tables=["entry_pricing","subvention_pricing_3","subvention_pricing_4","subvention_pricing_6","subvention_pricing_12","transaction_rebate","customer_acquisition_support"]
		for table in tables:
			if len(doc[table]):
				sizes = set()
				for i in  doc[table]:
					if i.size in sizes:
							frappe.throw(("The size {0} is already added . Please avoid duplicates.").format(i.size))
						
					sizes.add(i.size)