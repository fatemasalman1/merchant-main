import frappe
from functools import wraps

def set_language_from_header(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        lang = frappe.local.request.headers.get("lang") 
        
        if lang:
            frappe.local.lang = lang  # Set language if provided
        return func(*args, **kwargs)
    return wrapper