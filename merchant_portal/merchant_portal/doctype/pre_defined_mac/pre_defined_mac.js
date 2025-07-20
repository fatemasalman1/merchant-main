// Copyright (c) 2024, ahmed ramzi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Pre-Defined MAC", {
  refresh: function (frm) {
    frm.events.get_registration_fields(frm);
  },
  get_registration_fields: function (frm) {
    frappe.model.with_doctype("Registration Questionnaire", () => {
      let fieldnames = frappe
        .get_meta("Registration Questionnaire")
        .fields.filter((d) => {
          return frappe.model.no_value_type.indexOf(d.fieldtype) === -1;
        })
        .map((d) => {
          return { label: `${d.label} (${d.fieldname})`, value: d.fieldname };
        });

      frm.fields_dict.criteria.grid.update_docfield_property(
        "field",
        "options",
        fieldnames
      );
    });
  },
});
