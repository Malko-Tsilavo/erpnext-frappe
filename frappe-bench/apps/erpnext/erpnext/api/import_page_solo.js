frappe.pages['import-page'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Importation personnalisée',
        single_column: true
    });

    let $content = $(`
        <div style="text-align: center; padding: 50px;">
            <h1>Importer un fichier CSV</h1>
            <input type="file" id="csv-file" accept=".csv" style="margin-top: 20px;" />
            <div style="margin-top: 20px;">
                <button class="btn btn-success" id="btn-import">Importer</button>
            </div>
        </div>
    `);

    page.main.html($content);

    $content.find('#btn-import').on('click', function () {
        const fileInput = document.getElementById('csv-file');
        if (!fileInput.files.length) {
            frappe.msgprint(__('Veuillez sélectionner un fichier CSV.'));
            return;
        }

        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append("file", file);
        formData.append("is_private", 0);

        frappe.show_progress("Upload en cours", 30, 100, "Chargement...");

        // Upload via Frappe API
        fetch("/api/method/upload_file", {
            method: "POST",
            body: formData,
            headers: {
                "X-Frappe-CSRF-Token": frappe.csrf_token
            }
        })
        .then(res => res.json())
        .then(res => {
            frappe.hide_progress();

            if (res.message && res.message.file_url) {
                const file_url = res.message.file_url;

                // Appel à ta fonction Python
                frappe.call({
                    method: "erpnext.api.import_supplier_quotation.import_supplier_quotations",  // adapte selon ton chemin réel
                    args: { file_url },
                    callback: function(r) {
                        frappe.msgprint({
                            title: r.message.status === "success" ? "Succès" : "Erreur",
                            message: r.message.message,
                            indicator: r.message.status === "success" ? "green" : "red"
                        });
                    }
                });
            } else {
                frappe.msgprint({
                    title: "Erreur",
                    message: "Le fichier n'a pas été uploadé correctement.",
                    indicator: "red"
                });
            }
        })
        .catch(err => {
            frappe.hide_progress();
            frappe.msgprint("Erreur lors de l'upload : " + err.message);
        });
    });
};
