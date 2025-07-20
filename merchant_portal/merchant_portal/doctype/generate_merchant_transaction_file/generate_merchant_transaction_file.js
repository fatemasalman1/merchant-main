// Copyright (c) 2025, ahmed ramzi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Generate Merchant Transaction File", {
  refresh: function (frm) {
    // // Add button when a report file is available
    // if (frm.doc.file) {
    //   frm
    //     .add_custom_button(__("Download Report"), function () {
    //       // Construct download URL
    //       var download_url =
    //         "/api/method/merchant_portal.doctype.generate_merchant_transaction_file.generate_merchant_transaction_file.download_report";
    //       download_url += "?name=" + encodeURIComponent(frm.doc.name);
    //       // Trigger the file download in a new window
    //       window.open(download_url, "_blank");
    //     })
    //     .addClass("btn-primary");
    // }
  },
});
