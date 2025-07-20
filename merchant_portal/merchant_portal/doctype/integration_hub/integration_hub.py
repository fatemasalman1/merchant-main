# Copyright (c) 2025, ahmed ramzi and contributors
# For license information, please see license.txt

import json
from datetime import datetime

import frappe
import requests
from frappe.model.document import Document
from requests.adapters import HTTPAdapter
from requests.exceptions import (ConnectTimeout, HTTPError, RequestException,
                                 Timeout)
from urllib3.util.retry import Retry


class IntegrationHub(Document):
    
           
    def before_insert(self):
         self.call_request()
         
    @frappe.whitelist()
    def call_request(self,auto_save=0):
        if self.reference_type=="Merchant Subvention Agreement":
           
            self.call_agreement_request()
             
            if auto_save==1:   # Return only relevant updated fields to client
                self.save()
    def call_agreement_request(self):
        mids=frappe.db.get_all("Integration Hub MID",filters={"parent":self.name},pluck="mid")
        
        if not len(mids):
                return
            
        if self.type == "RegisterMerchant":
        
            registered, subvention_rate, contract_start_date, contract_end_date = frappe.db.get_value(
                self.reference_type, self.reference_name, 
                ["registered", "subvention_rate", "contract_start_date", "contract_end_date"]
            )
            
            company_name=frappe.db.get_value("Merchant",self.merchant,"company_name")

            payload = {
                "CommercialRegistration":self.commercial_register,#testing
                "MerchantName": company_name,
                "SubventionRate": subvention_rate,
                "ContractStartDate": str(contract_start_date),
                "ContractEndDate": str(contract_end_date),
                "MIDs": mids,
                "ProfitRateConfiguration": [
                    {"Tenure": "01", "ProfitRate": 1.5}, {"Tenure": "03", "ProfitRate": 1.5},
                    {"Tenure": "04", "ProfitRate": 1.5}, {"Tenure": "06", "ProfitRate": 2.0},
                    {"Tenure": "09", "ProfitRate": 2.0}, {"Tenure": "12", "ProfitRate": 2.0},
                    {"Tenure": "18", "ProfitRate": 2.0}, {"Tenure": "24", "ProfitRate": 2.0},
                    {"Tenure": "30", "ProfitRate": 2.0}, {"Tenure": "36", "ProfitRate": 2.0}
                ]
            }
           
            self.request(payload, self.type, "POST")
        if self.type == "AddMid":
           
            payload = {
                "CommercialRegistration":self.commercial_register,#testing
                "MID": self.mids[0].mid,
       
            }
            self.request(payload, self.type, "POST")
            
        if self.type =="RemoveMid":
            payload={
                "CommercialRegistration":self.commercial_register,#testing
                "MID": self.mids[0].mid,
              
            }
            self.request(payload, self.type, "POST")
            
    def request(self, payload, request_type, method):
       
        full_url = frappe.db.get_single_value('Integration End Point', 'url')
        endpoints = frappe.db.get_all("Integration End Points", filters={"type": request_type}, pluck="end_point")
       
        if not endpoints:
            frappe.throw(f"No endpoint found for type: {request_type}")

        url = f"{full_url}{endpoints[0]}"
        self.url=url
        self.payload=str(payload)

        headers = {"Content-Type": "application/json"}
        json_payload = json.dumps(payload, ensure_ascii=False)  # Ensure proper JSON format
        
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))

        try:
            
            response = session.request(method, url, headers=headers, data=json_payload, timeout=30)
            # response.raise_for_status()  # Raise HTTP errors
            self.response = str(response.json())
            self.handle_response_data(response)
            
        except ConnectTimeout as e:
            self.status = "Failed"
            self.response_code = 408
            self.response = "Connection to endpoint timed out."
            self.set_mid_failed()
            frappe.log_error(title="Connection to endpoint timed out.",message=frappe.get_traceback())
            
        except Timeout as e:
            self.status = "Failed"
            self.response_code = 408
            self.response = "The request timed out."
            frappe.log_error(title="The request timed out.",message=frappe.get_traceback())
            
        except HTTPError as e:
            self.status = "Failed"
            self.response_code = e.response.status_code
            self.response = f"HTTP error: {e}"
            self.set_mid_failed()
            frappe.log_error(title="HTTP error",message=frappe.get_traceback())
            
        except RequestException as e:
            self.status = "Failed"
            self.response_code = 500
            self.response = f"Request failed: {e}"
            self.set_mid_failed()
            frappe.log_error(title="Request failed",message=frappe.get_traceback())
        
        except Exception as e :
            self.status = "Failed"
            self.response_code = 403
            self.response = f"Request failed: {e}"
            self.set_mid_failed()
            frappe.log_error(title="Request failed",message=frappe.get_traceback())
    def handle_response_data(self,response):
        self.response_code=response.status_code
        response= response.json()
        success = response.get("Success")

        # If Success key is missing or is False
        if not success:
            self.status = "Failed"
            self.response_code = 400
            self.response = str(response)
            self.set_mid_failed()
            frappe.log_error(title="Request failed",message=frappe.get_traceback())
            return
        
        if response["Success"]==False:
            self.status="Failed"
            self.set_mid_failed()
            return
        self.status="Success"
        
        # RegisterMerchant
        if self.type == "RegisterMerchant":
            viban=response["VertualIban"]
            w4u_contract_id=response["ContractNumber"]
            frappe.db.set_value("Merchant Subvention Agreement", self.reference_name, {
                "registered": 1,
                "viban": viban,
                "w4u_contract_id": w4u_contract_id
            })
            
            for mid in self.mids:

                frappe.db.sql("""
                    UPDATE `tabMerchant ID`
                    SET status = 'Active'
                    WHERE parent = %s AND mid = %s
                """, (self.reference_name, mid.mid))

                frappe.db.commit()
        # AddMid
        if self.type == "AddMid":
            
            frappe.db.sql("""
                UPDATE `tabMerchant ID`
                SET status = 'Active'
                WHERE parent = %s AND mid = %s
            """, (self.reference_name, self.mids[0].mid))

            frappe.db.commit()
        # RemoveMid
        if self.type =="RemoveMid":
            frappe.db.sql("""
                UPDATE `tabMerchant ID`
                SET status = 'Disabled'
                WHERE parent = %s AND mid = %s
            """, (self.reference_name, self.mids[0].mid))

            frappe.db.commit()
            
    def set_mid_failed(self):
        if self.type =="RemoveMid":
             return
         
        for mid in self.mids:

            frappe.db.sql("""
                UPDATE `tabMerchant ID`
                SET status = 'Failed'
                WHERE parent = %s AND mid = %s
            """, (self.reference_name, mid.mid))

            frappe.db.commit() 
            
def convert_date_format(date_input):
    date_input=str(date_input)
    """Convert date from DD-MM-YYYY format to YYYY-MM-DD format."""
    if isinstance(date_input, datetime):
        
        return date_input.strftime("%Y-%m-%d")  # Already a datetime object
    elif isinstance(date_input, str):
       
        
        date_obj = datetime.strptime(date_input, "%d-%m-%Y")
       
        return date_obj.strftime("%Y-%m-%d")
    
