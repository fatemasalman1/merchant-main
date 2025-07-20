// Copyright (c) 2024, ahmed ramzi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Registration Questionnaire", {
  refresh(frm) {
    frm.events.fetch_data_from_wathq(frm);
    frm.events.set_faild_msg_wathq(frm);
    frm.events.set_business_category_filter(frm);
    frm.events.set_sub_category(frm);
    frm.events.create_merchant(frm);
    frm.events.denial_btn(frm);
  },
  denial_btn: function (frm) {
    if (frm.doc.status != "Pending") {
      return;
    }

    frm.add_custom_button(
      "Denial",
      () => {
        if (frm.doc.approved || frm.doc.automate_approval) {
          frappe.confirm(
            "Are you sure you want to Denail?, Registration is Approved",
            () => {
              denail_call(frm);
            },
            () => {
              // action to perform if No is selected
            }
          );
        } else {
          denail_call(frm);
        }
      },
      "Action"
    );
  },

  set_sub_category: function (frm) {
    frm.fields_dict["sub_category"].grid.get_field(
      "business_category_sub"
    ).get_query = function (doc, cdt, cdn) {
      var row = locals[cdt][cdn];
      return {
        query:
          "merchant_portal.merchant_portal.doctype.registration_questionnaire.registration_questionnaire.set_sub_catogery_filter",
        filters: {
          business_category: frm.doc.business_category,
        },
      };
    };
  },
  create_merchant: async function (frm) {
    let merchant = await frappe.db
      .get_value(
        "Merchant",
        { registration_questionnaire: frm.doc.name },
        "name"
      )
      .then((r) => {
        return r.message.name;
      });
    if (merchant) {
      return;
    }
    if (frm.doc.docstatus == 1 && frm.doc.status != "Denial") {
      frm.add_custom_button("Create Merchant", () => {
        frm.call({
          method: "create_merchant",
          doc: frm.doc,
          freeze: true,
          freeze_message: __("...Creating Merchant"),
          callback: function (r) {
            frm.reload_doc();
          },
        });
      });
    }
  },
  set_faild_msg_wathq: function (frm) {
    if (frm.doc.wathq_status == "Failed") {
      frm.set_intro(
        `     Wathq : Failed<br>
              Message : ${frm.doc.response},<br>
              You can set data manually or try again

            `,
        "red"
      );
    } else if (frm.doc.wathq_status == "Success") {
      frm.set_intro(
        `     Wathq : Data Successfully Fetched<br>
     
            `,
        "green"
      );
    }
  },
  type_of_business: function (frm) {
    if (frm.doc.type_of_business) {
      frm.set_value("business_category", "");
      frm.set_value("has_sub", 0);
      frm.set_value("sub_category", 0);
    }
  },
  set_business_category_filter: function (frm) {
    frm.set_query("business_category", function (doc) {
      return {
        query:
          "merchant_portal.merchant_portal.doctype.registration_questionnaire.registration_questionnaire.set_catogery_filter",
        filters: {
          type_of_business: frm.doc.type_of_business,
        },
      };
    });
  },
  business_category: function (frm) {
    frm.call({
      doc: frm.doc,
      method: "check_sub_category",
      args: {
        business_category: frm.doc.business_category,
      },
      callback: function (r) {},
    });
  },
  fetch_data_from_wathq: function (frm) {
    if (
      frm.is_new() ||
      frm.doc.wathq_status == "Success" ||
      frm.doc.docstatus == 1
    ) {
      return;
    }
    frm.add_custom_button("Get Data From Wathq", () => {
      frm.call({
        doc: frm.doc,
        method: "get_commercial_register",
        args: { commercial_register: frm.doc.commercial_register },
        freeze: true,
        freeze_message: __("...Fetching Data From Wathq"),
        callback: function (r) {
          frm.reload_doc();
        },
      });
    });
  },
  annual_sales: function (frm) {
    // if (frm.doc.annual_sales) {
    //   frm.call({
    //     doc: frm.doc,
    //     method: "calc_annual_sales",
    //     callback: function (r) {
    //       frm.set_value("annual_sales_digit", r.message);
    //     },
    //   });
    // } else {
    //   frm.set_value("annual_sales_digit", "");
    // }
  },
  business_starting_date: function (frm) {
    if (frm.doc.business_starting_date) {
      frm.call({
        doc: frm.doc,
        method: "get_months",
        callback: function (r) {
          frm.set_value("business_starting_by_months", r.message);
        },
      });
    } else {
      frm.set_value("business_starting_by_months", "");
    }
  },
});

function denail_call(frm) {
  let d = new frappe.ui.Dialog({
    title: "Message",
    fields: [
      {
        label: "Message",
        fieldname: "message",
        fieldtype: "Link",
        options: "Registration Denail Message",
      },
    ],
    size: "small", // small, large, extra-large
    primary_action_label: "Submit",
    primary_action(values) {
      frm.call({
        doc: frm.doc,
        method: "make_denail",
        args: { message: values.message },
        callback: function (r) {
          frm.reload_doc();
        },
      });
      d.hide();
    },
  });

  d.show();
}
