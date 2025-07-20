# Copyright (c) 2024, ahmed ramzi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MerchantSizingEngine(Document):
	def validate(self):
		self.validate_duplicate()

	def validate_duplicate(self):
		if len(self.merchant_scoring_point):
			unique_size = []
			for s in self.merchant_scoring_point:
				if s.size in unique_size:
					frappe.throw(
						("Size {0}  appears Multiple times in row {1} ").format(s.size,s.idx)
					)
				else:
					unique_size.append(s.size)



	