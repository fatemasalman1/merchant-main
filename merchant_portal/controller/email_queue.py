import frappe
from frappe.model.document import Document


def clean_recipients_on_validate(doc, method):
    pass
    # List of emails to remove
    # blacklist = [
    #     "basmah.alghamdi@tasheelfinance.com",
    #     "rahaf.albelali@tasheelfinance.com",
    #     "ibrahim.magrabi@tasheelfinance.com",
    #     "haytham.bayoumy@tasheelfinance.com",
    #     "norah.alsaleem@tasheelfinance.com",
    #     "shooq.alzahrani@tasheelfinance.com",
    #     "sultan.asaad@tasheelfinance.com",
    #     "futun.alwabel@tasheelfinance.com",
    
    # ]

    # # Filter out matching recipients
    # doc.recipients = [
    #     r for r in doc.recipients
    #     if r.recipient and r.recipient.lower() not in blacklist
    # ]
