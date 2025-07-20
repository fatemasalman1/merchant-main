import frappe
from merchant_portal.controller.payment_request import \
    manual_send_payment_request


def execute():
   invoices=frappe.db.get_all("Sales Invoice",filters={"custom_merchant_subvention_agreement":["!=",None],"docstatus":1,"outstanding_amount":[">",0],"custom_payment_request_sent":0},pluck ="name")
   for i in invoices:
       manual_send_payment_request(i)