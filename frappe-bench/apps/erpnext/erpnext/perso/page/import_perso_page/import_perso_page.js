frappe.pages['import-perso-page'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Importation Globale',
        single_column: true
    });

    let $content = $(`
        <div style="text-align: center; padding: 50px;">
            <h1>Importer tous les fichiers CSV</h1>
            <div style="margin-top: 20px;">
                <label for="csv-supplier">Fichier CSV Fournisseurs :</label>
                <input type="file" id="csv-supplier" accept=".csv" style="margin-bottom: 10px;" /><br>
                <label for="csv-material">Fichier CSV Demandes de Matériel :</label>
                <input type="file" id="csv-material" accept=".csv" style="margin-bottom: 10px;" /><br>
                <label for="csv-quotation">Fichier CSV Demandes de Devis :</label>
                <input type="file" id="csv-quotation" accept=".csv" style="margin-bottom: 10px;" /><br>
                <button class="btn btn-success" id="btn-import">Importer Tout</button>
            </div>
        </div>
    `);

    page.main.html($content);

    $content.find('#btn-import').on('click', function () {
        const supplierInput = document.getElementById('csv-supplier');
        const materialInput = document.getElementById('csv-material');
        const quotationInput = document.getElementById('csv-quotation');

        if (!supplierInput.files.length || !materialInput.files.length || !quotationInput.files.length) {
            frappe.msgprint(__('Veuillez sélectionner tous les fichiers CSV (fournisseurs, demandes de matériel, demandes de devis).'));
            return;
        }

        const supplierFile = supplierInput.files[0];
        const materialFile = materialInput.files[0];
        const quotationFile = quotationInput.files[0];

        // Uploader les fichiers un par un
        frappe.show_progress("Upload en cours", 0, 100, "Chargement des fichiers...");

        const uploadFile = (file) => {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("is_private", 0);

            return fetch("/api/method/upload_file", {
                method: "POST",
                body: formData,
                headers: {
                    "X-Frappe-CSRF-Token": frappe.csrf_token
                }
            }).then(res => res.json());
        };

        Promise.all([
            uploadFile(supplierFile),
            uploadFile(materialFile),
            uploadFile(quotationFile)
        ])
        .then(([supplierRes, materialRes, quotationRes]) => {
            frappe.hide_progress();

            const supplierUrl = supplierRes.message?.file_url;
            const materialUrl = materialRes.message?.file_url;
            const quotationUrl = quotationRes.message?.file_url;

            if (!supplierUrl || !materialUrl || !quotationUrl) {
                frappe.msgprint({
                    title: "Erreur",
                    message: "Un ou plusieurs fichiers n'ont pas été uploadés correctement.",
                    indicator: "red"
                });
                return;
            }

            // Appeler import_generals
            frappe.call({
                method: "erpnext.api.import_general.import_generals",
                args: {
                    csv_supplier: supplierUrl,
                    csv_material: materialUrl,
                    csv_supplier_quotation: quotationUrl
                },
                callback: function(r) {
                    frappe.msgprint({
                        title: r.message.status === "success" ? "Succès" : "Erreur",
                        message: r.message.message,
                        indicator: r.message.status === "success" ? "green" : "red"
                    });
                }
            });
        })
        .catch(err => {
            frappe.hide_progress();
            frappe.msgprint({
                title: "Erreur",
                message: "Erreur lors de l'upload des fichiers : " + err.message,
                indicator: "red"
            });
        });
    });
};