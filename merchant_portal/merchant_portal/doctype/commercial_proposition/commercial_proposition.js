// Copyright (c) 2024, ahmed ramzi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Commercial Proposition", {
  refresh(frm) {
    frm.events.create_merchant_offer(frm);
    frm.events.create_merchan_contract(frm);
  },
  create_merchant_offer: function (frm) {
    if (
      frm.doc.status == "Accepted" &&
      in_list(
        ["Negotiate", "Pending", "Closed", "Expired"],
        frm.doc.merchant_approval_status
      )
    ) {
      frm.add_custom_button("Send Offer", () => {
        frm.call({
          method: "create_offer",
          doc: frm.doc,
          callback: function (r) {
            frm.reload_doc();
          },
        });
      });
    }
  },
  create_merchan_contract: async function (frm) {
    let contract = await frappe.db
      .get_value(
        "Merchant Contract",
        { commercial_proposition: frm.doc.name },
        "name"
      )
      .then((r) => {
        return r.message.name;
      });
    if (contract) {
      return;
    }
    if (
      frm.doc.status == "Accepted" &&
      frm.doc.merchant_approval_status == "Accepted" &&
      frm.doc.docstatus == 1
    ) {
      frm.add_custom_button("Create Contract", () => {
        frm.call({
          method: "create_merchan_contract",
          doc: frm.doc,
          callback: function (r) {
            frm.reload_doc();
          },
        });
      });
    }
  },
  get_offer: function (frm) {
    frm.call({
      method: "get_offer_data",
      doc: frm.doc,
      freeze: true,
      freeze_message: __("...Fetching Offer"),
      callback: async function (r) {
        if (r.message === true) {
          await frappe.show_alert(
            {
              message: __("No Customer Acquisition  Rate Found"),
              indicator: "red",
            },
            5
          );
        }

        await frm.refresh();
        frm.reload_doc();
      },
    });
  },
  competitive_analysis_template: function (frm) {
    if (frm.doc.competitive_analysis_template) {
      frm.call({
        method: "fetch_analysis_template",
        doc: frm.doc,
        callback: function (r) {},
      });
    }
  },
});
