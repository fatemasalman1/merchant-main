// Copyright (c) 2024, ahmed ramzi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Merchant Offer", {
  refresh: function (frm) {
    frm.events.set_status_btn(frm);
  },
  set_status_btn: function (frm) {
    if (frm.doc.status == "Waiting For Response") {
      frm.add_custom_button("Set Status", () => {
        let d = new frappe.ui.Dialog({
          title: "Enter Status",
          fields: [
            {
              label: "Status",
              fieldname: "status",
              fieldtype: "Select",
              options: ["Accepted", "Negotiate", "Closed"],
              reqd: 1,
            },
          ],
          size: "small",
          primary_action_label: "Submit",
          primary_action(values) {
            frappe.call({
              doc: frm.doc,
              args: { status: values.status },
              method: "set_status",
              callback: (r) => {
                frm.reload_doc();
              },
            });

            d.hide();
          },
        });

        d.show();
      });
    }
  },
});
