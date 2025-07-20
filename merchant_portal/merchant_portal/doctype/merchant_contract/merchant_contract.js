// Copyright (c) 2024, ahmed ramzi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Merchant Contract", {
  refresh(frm) {
    frm.events.generate_pdf_contract(frm);
    frm.set_df_property("contract_document", "cannot_add_rows", true);
    frm.set_df_property("contract_document", "cannot_delete_rows", true);
    frm.events.sent_contract_to_customer(frm);
    frm.events.cancel_contract(frm);
    frm.events.review_contract(frm);
  },
  review_contract: function (frm) {
    if (
      frappe.user.has_role(["System Manager", "Administrator"]) ||
      frappe.user.has_role("Commercial  Officer") ||
      frappe.user.has_role("Commercial Chief") ||
      frappe.user.has_role("Head of Commercial") ||
      frappe.user.has_role("Merchant Portal Admin")
    ) {
      if (
        frm.doc.signed_contract_status == "Pending" &&
        frm.doc.status == "Waiting Review Uploaded Contract"
      ) {
        frm.add_custom_button("Review Contract", () => {
          let d = new frappe.ui.Dialog({
            title: "Review Contract",
            fields: [
              {
                label: "Status",
                fieldname: "status",
                fieldtype: "Select",
                options: ["Accepted", "Rejected"],
                reqd: 1,
              },
              {
                label: "Template",
                fieldname: "template",
                fieldtype: "Link",
                depends_on: "eval:doc.status == 'Rejected'",
                options: "Invalid Contract Template",
                onchange() {
                  frappe.db
                    .get_value(
                      "Invalid Contract Template",
                      d.get_value("template"),
                      ["message", "subject"]
                    )
                    .then((r) => {
                      let values = r.message;

                      d.set_value("subject", values.subject);
                      d.set_value("message", values.message);
                    });
                },
              },
              {
                label: "Subject",
                fieldname: "subject",
                fieldtype: "Data",
                depends_on: "eval:doc.status == 'Rejected'",
                mandatory_depends_on: "eval:doc.status == 'Rejected'",
              },
              {
                label: "Message",
                fieldname: "message",
                fieldtype: "Text",
                depends_on: "eval:doc.status == 'Rejected'",
                mandatory_depends_on: "eval:doc.status == 'Rejected'",
              },
            ],

            primary_action_label: "Submit",
            primary_action(values) {
              frappe.call({
                doc: frm.doc,
                args: {
                  answer: values.status,
                  subject: values.subject,
                  message: values.message,
                },
                method: "review_signed_cotract",
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
    }
  },
  generate_pdf_contract: function (frm) {
    if (frm.has_perm("write")) {
      frappe.call({
        method:
          "merchant_portal.merchant_portal.doctype.merchant_contract.merchant_contract.get_merchant_contract_documents",
        args: {
          contract_name: frm.doc.name,
        },
        callback: function (response) {
          const records = response.message;
          if (
            records.length === 0 &&
            !in_list(["Closed", "Merchant Accepted"], frm.doc.status) &&
            !frm.is_new() &&
            frm.doc.docstatus == 0
          ) {
            frm.add_custom_button("Generate Contract", () => {
              frm.call({
                method: "generate_pdf_contract",
                doc: frm.doc,
                freeze: true,
                freeze_message: __("...Generating Contract , Please Wait"),
                callback: function (r) {
                  frm.reload_doc();
                },
              });
            });
          }
        },
      });
    }
  },

  sent_contract_to_customer: function (frm) {
    if (frm.has_perm("write")) {
      frappe.call({
        method:
          "merchant_portal.merchant_portal.doctype.merchant_contract.merchant_contract.get_pending_contract_documents",
        args: {
          contract_name: frm.doc.name,
        },
        callback: function (response) {
          const records = response.message;
          if (records.length > 0) {
            if (frm.doc.not_first_time && frm.doc.ready_to_send == 0) {
              return;
            }
            frm.add_custom_button("Send Contract", () => {
              frm.call({
                method: "send_contract",
                doc: frm.doc,
                freeze: true,
                freeze_message: __("...Sending Contract , Please Wait"),
                callback: function (r) {
                  frm.refresh();
                },
              });
            });
          }
        },
      });
    }
  },

  cancel_contract: function (frm) {
    if (frm.has_perm("write")) {
      frappe.call({
        method:
          "merchant_portal.merchant_portal.doctype.merchant_contract.merchant_contract.get_pending_contract_for_cancellation",
        args: {
          contract_name: frm.doc.name,
        },
        callback: function (response) {
          const records = response.message;
          if (records.length > 0) {
            if (frm.doc.not_first_time && frm.doc.ready_to_send == 0) {
              return;
            }
            frm.add_custom_button("Remove Pending Contract", () => {
              frm.call({
                method: "cancel_contract",
                doc: frm.doc,
                freeze: true,
                freeze_message: __("...Cancel Contract , Please Wait"),
                callback: function (r) {
                  frm.reload_doc();
                },
              });
            });
          }
        },
      });
    }
  },
});
