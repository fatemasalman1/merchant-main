// Copyright (c) 2024, Ahmed Ramzi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Merchant Lead", {
  // Runs when the form is refreshed
  refresh: function (frm) {
    frm.events.create_registration_questionnaire(frm);
  },

  // Checks if a Registration Questionnaire exists for the Merchant Lead.
  // If it doesn't exist, adds a button to create one.
  create_registration_questionnaire: async function (frm) {
    try {
      let registration_questionnaire = await frappe.db
        .get_value(
          "Registration Questionnaire",
          { merchant_lead: frm.doc.name },
          "name"
        )
        .then((r) => (r.message ? r.message.name : null));

      // If a questionnaire already exists, exit the function.
      if (registration_questionnaire) return;

      // Adds a custom button to create a Registration Questionnaire if one doesn't exist.
      frm.add_custom_button("Create Registration Questionnaire", () => {
        frm.call({
          doc: frm.doc,
          method: "create_registration_questionnaire",
          callback: function () {
            frm.refresh(); // Refresh the form after creation
          },
        });
      });
    } catch (error) {
      console.error("Error checking for Registration Questionnaire:", error);
    }
  },

  // Triggers when the business category is selected.
  // Calls server method `check_sub_category` to handle sub-category checks.
  business_category: function (frm) {
    frm.call({
      doc: frm.doc,
      method: "check_sub_category",
      args: { business_category: frm.doc.business_category },
      callback: function (response) {
        if (response && response.message) {
          // Handle response here if needed
        }
      },
    });
  },

  // Resets business-related fields when the type of business changes.
  type_of_business: function (frm) {
    if (frm.doc.type_of_business) {
      frm.set_value("business_category", "");
      frm.set_value("has_sub", 0);
      frm.set_value("sub_category", 0);
    }
  },
});
