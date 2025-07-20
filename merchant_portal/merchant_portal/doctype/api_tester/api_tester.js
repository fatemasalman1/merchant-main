// Copyright (c) 2025, ahmed ramzi and contributors
// For license information, please see license.txt

frappe.ui.form.on("API Tester", {
  refresh(frm) {
    if (!frm.is_new()) {
      frm.add_custom_button("Run Test", () => {
        frm.call({
          method: "run_test",
          doc: frm.doc,
          callback: function (r) {
            if (r.message) {
              frm.set_value("response_body", r.message);
              frappe.show_alert("✅ Response updated", 3);
            }
          },
        });
      });
    }
  },
});
