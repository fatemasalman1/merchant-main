// Copyright (c) 2025, ahmed ramzi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Merchant Portal Setting", {
  refresh(frm) {
    frm.events.item_filter(frm);
  },
  item_filter: function (frm) {
    frm.set_query("billing_fee_item", function () {
      return {
        filters: {
          is_stock_item: 0,
        },
      };
    });
  },
});
