// Copyright (c) 2025, ahmed ramzi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Upload Merchant Tool", {
  refresh(frm) {
    // 1) “Process Records” button on Draft+Pending
    if (frm.doc.docstatus === 0 && frm.doc.status === "Pending") {
      frm.add_custom_button(__("Process Records"), () => {
        frappe.call({
          doc: frm.doc,
          method: "process_records",
          freeze: true,
          freeze_message: __("Processing merchant records…"),
          callback: () => {
            // on completion we’ll reload when we get the final event
          },
        });
      });
    }

    // 2) Listen for per‐row progress
    frappe.realtime.on("merchant_upload_progress", (data) => {
      if (data.docname !== frm.doc.name) return;

      // Update a headline or intro
      frm.dashboard.set_headline(
        __("Processed {0}/{1} (✔ {2} • ✖ {3})", [
          data.success + data.failed,
          data.total,
          data.success,
          data.failed,
        ])
      );

      // (Optional) highlight the child-row status cell
      const row = frm.fields_dict.records.grid.grid_rows[data.row_index];
      if (row) {
        row.set_cell_value("status", data.row_status);
      }
    });

    // 3) Listen for the final “complete” event
    frappe.realtime.on("merchant_upload_complete", (data) => {
      if (data.docname !== frm.doc.name) return;

      frm.dashboard.set_headline(
        __("Overall Status: {0}", [data.overall_status])
      );
      frm.reload_doc(); // now that it’s done, refresh to pull in final statuses
    });
  },
});
