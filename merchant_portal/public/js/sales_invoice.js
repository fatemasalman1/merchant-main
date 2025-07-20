frappe.ui.form.on("Sales Invoice", {
  refresh(frm) {
    if (frm.doc.docstatus === 1 && !frm.doc.custom_payment_request_sent) {
      frm.add_custom_button(
        __("Send Payment Request"),
        () => {
          frappe.call({
            method:
              "merchant_portal.controller.payment_request.manual_send_payment_request",
            freeze: true,
            freeze_message: __("...Sending"),
            callback: function (r) {
              if (!r.exc) {
                frappe.msgprint(__("Payment Request has been sent."));
                frm.reload_doc();
              }
            },
          });
        },
        __("Actions")
      );
    }
  },
});
