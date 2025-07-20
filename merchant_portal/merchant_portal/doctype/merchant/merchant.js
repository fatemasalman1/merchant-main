// Copyright (c) 2024, ahmed ramzi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Merchant", {
  refresh(frm) {
    frm.events.commercial_proposition_btn(frm);
  },
  commercial_proposition_btn: async function (frm) {
    let merchant = await frappe.db
      .get_value(
        "Commercial Proposition",
        {
          merchant: frm.doc.name,
          merchant_approval_status: [
            "in",
            ["Pending", "Offered", "Waiting For Response", "Negotiate"],
          ],
        },
        "name"
      )
      .then((r) => {
        return r.message.name;
      });
    if (merchant) {
      return;
    }
    if (frm.has_perm("write")) {
      frm
        .add_custom_button("Create Commercial Proposition", () => {
          frm.call({
            method: "create_commercial_proposition",
            doc: frm.doc,
            callback: function (r) {
              frm.reload_doc();
            },
          });
        })
        .addClass("btn-primary");
    }
  },
});
