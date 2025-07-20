// Copyright (c) 2025, ahmed ramzi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Integration Hub", {
  refresh(frm) {
    frm.events.retry_btn(frm);
  },
  retry_btn: function (frm) {
    if (frm.doc.status != "Success") {
      frm.add_custom_button("Retry", () => {
        frm.call({
          doc: frm.doc,
          args: { auto_save: 1 },
          method: "call_request",
          freeze: true,
          freeze_message: __("Sending ..."),
          callback: function (r) {},
        });
      });
    }
  },
});
