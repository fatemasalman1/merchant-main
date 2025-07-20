app_name = "merchant_portal"
app_title = "Merchant Portal"
app_publisher = "ahmed ramzi"
app_description = "merchant portal"
app_email = "ahmed.ramzi222@gmail.com"
app_license = "mit"
fixtures = [ {"dt": "Integration Type"},{"dt": "Issue Type"},{"dt": "Translation"},{"dt": "Role Profile"},{"dt": "Module Profile"},{"dt": "Translation"},{"dt": "Merchant Business Category"},{"dt": "Type of Business"},{"dt": "Business Category Sub"},{"dt": "Target Audience"},{"dt": "Workflow State"},{"dt": "Workflow"},{"dt": "Workflow Action Master"},{"dt":"Merchant Annual Sales"},{"dt":"Commercial Proposition Engine"},{"dt": "Role", "filters": [ [ "name", "in", ["Commercial Chief","Merchant","Head of Commercial","Commercial  Officer","Head of Finance","Legal Officer","Risk Team","Merchant Portal Admin"] ] ]}]
# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/merchant_portal/css/merchant_portal.css"
# app_include_js = "/assets/merchant_portal/js/merchant_portal.js"

# include js, css files in header of web template
# web_include_css = "/assets/merchant_portal/css/merchant_portal.css"
# web_include_js = "/assets/merchant_portal/js/merchant_portal.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "merchant_portal/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Sales Invoice" : "public/js/sales_invoice.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "merchant_portal/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "merchant_portal.utils.jinja_methods",
# 	"filters": "merchant_portal.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "merchant_portal.install.before_install"
# after_install = "merchant_portal.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "merchant_portal.uninstall.before_uninstall"
# after_uninstall = "merchant_portal.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "merchant_portal.utils.before_app_install"
# after_app_install = "merchant_portal.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "merchant_portal.utils.before_app_uninstall"
# after_app_uninstall = "merchant_portal.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "merchant_portal.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"File": {
		
		"on_trash": "merchant_portal.controller.file.check_logo"
	},
 "Process Payment Reconciliation":
     {
     "before_insert":"merchant_portal.controller.payment_reconciliation.set_default_advanced_account"
     },
     "Sales Invoice":{
		      "on_submit":"merchant_portal.controller.payment_request.handle_new_invoice"

	 },
     "Email Queue":{
			 "validate":"merchant_portal.controller.email_queue.clean_recipients_on_validate",
    		"before_insert":"merchant_portal.controller.email_queue.clean_recipients_on_validate"
		 }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	 "cron": {
        "0 0 * * *": [
          
            "merchant_portal.tasks.invoice_tracker.generate_opening_invoices",
            "merchant_portal.tasks.invoice_tracker.fetch_billing_for_merchants"
            # ... your other schedulers ...
        ]
    },
# 	"all": [
# 		"merchant_portal.tasks.all"
# 	],
	"daily": [
     "merchant_portal.tasks.payments_tracker.fetch_payments_for_merchants",
		"merchant_portal.tasks.contract_status.track_contract_status",
  "merchant_portal.tasks.requeued_process_payment_reconciliation.requeued_process_payment_reconciliation"
  		
	],
	"hourly": [
		"merchant_portal.tasks.validate_offer_expire.validate_offer_expire",
  		"merchant_portal.tasks.mid_registration.register_pending_mid",
		"erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.trigger_reconciliation_for_queued_docs"
	],

# 	"monthly": [
# 		"merchant_portal.tasks.monthly"
# 	],
}

# Testing
# -------

# before_tests = "merchant_portal.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "merchant_portal.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "merchant_portal.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["merchant_portal.utils.before_request"]
# after_request = ["merchant_portal.utils.after_request"]

# Job Events
# ----------
# before_job = ["merchant_portal.utils.before_job"]
# after_job = ["merchant_portal.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"merchant_portal.api.v2.jwt.jwt.validate_jwt"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

