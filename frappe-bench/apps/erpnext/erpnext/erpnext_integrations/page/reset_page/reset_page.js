frappe.pages['reset-page'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Reset Customer Data',
        single_column: true
    });

    let $content = $(`
        <div style="text-align: center; padding: 50px;">
            <h1>Reset Customer Data</h1>
            <p>Click the button below to delete all customer data. This action is irreversible and restricted to administrators.</p>
            <div style="margin-top: 20px;">
                <button class="btn btn-danger btn-reset">Reset All Customers</button>
            </div>
        </div>
    `);

    page.main.html($content);

    $content.find('.btn-reset').on('click', function() {
        frappe.confirm(
            'Are you sure you want to delete all customer data? This action cannot be undone.',
            function() {
                frappe.call({
                    method: "erpnext.api.util.reset_customer_data",
                    callback: function(response) {
                        if (response.message) {
                            frappe.msgprint({
                                title: response.message.status === "success" ? "Success" : "Error",
                                message: response.message.message,
                                indicator: response.message.status === "success" ? "green" : "red"
                            });
                        } else {
                            frappe.msgprint({
                                title: "Error",
                                message: "An unexpected error occurred. Please check the server logs.",
                                indicator: "red"
                            });
                        }
                    },
                    error: function(err) {
                        frappe.msgprint({
                            title: "Error",
                            message: "Failed to execute the reset operation: " + err.message,
                            indicator: "red"
                        });
                    }
                });
            }
        );
    });
};