import frappe
from erpnext.api.import_material import import_materials
from erpnext.api.import_supplier_quotation import import_supplier_quotations
from erpnext.api.import_supplier import import_suppliers

@frappe.whitelist()
def import_generals(csv_supplier, csv_material, csv_supplier_quotation):
    try:
        required_doctypes = ["Supplier", "Country", "Material Request", "Item", "Item Group", "Warehouse", "Request for Quotation"]
        for doctype in required_doctypes:
            if not frappe.has_permission(doctype, "create"):
                frappe.throw(f"Vous n'avez pas la permission de créer des {doctype}.", frappe.PermissionError)

        # Vérifier que les URLs des fichiers sont fournies
        if not csv_supplier or not csv_material or not csv_supplier_quotation:
            frappe.throw("Les URLs des fichiers CSV pour les fournisseurs, les demandes de matériel et les demandes de devis sont requises.")

        # Créer un point de sauvegarde pour le rollback
        frappe.db.savepoint("import_generals")

        # Étape 1 : Importer les fournisseurs
        try:
            supplier_result = import_suppliers(csv_supplier)
            if supplier_result.get("status") != "success":
                frappe.throw(f"Échec de l'importation des fournisseurs : {supplier_result.get('message')}")
        except Exception as e:
            frappe.db.rollback(save_point="import_generals")
            frappe.throw(f"Échec de l'importation des fournisseurs : {str(e)}")

        # Étape 2 : Importer les demandes de matériel
        try:
            material_result = import_materials(csv_material)
            if material_result.get("status") != "success":
                frappe.throw(f"Échec de l'importation des demandes de matériel : {material_result.get('message')}")
        except Exception as e:
            frappe.db.rollback(save_point="import_generals")
            frappe.throw(f"Échec de l'importation des demandes de matériel : {str(e)}")

        # Étape 3 : Importer les demandes de devis
        try:
            quotation_result = import_supplier_quotations(csv_supplier_quotation)
            if quotation_result.get("status") != "success":
                frappe.throw(f"Échec de l'importation des demandes de devis : {quotation_result.get('message')}")
        except Exception as e:
            frappe.db.rollback(save_point="import_generals")
            frappe.throw(f"Échec de l'importation des demandes de devis : {str(e)}")

        # Tout s'est bien passé, valider la transaction
        frappe.db.commit()
        message = (
            f"Importation globale terminée avec succès : "
            f"{supplier_result.get('imported_suppliers', 0)} fournisseurs importés, "
            f"{supplier_result.get('created_countries', 0)} pays créés, "
            f"{material_result.get('imported_requests', 0)} demandes de matériel importées, "
            f"{material_result.get('created_items', 0)} articles créés, "
            f"{material_result.get('created_item_groups', 0)} groupes d'articles créés, "
            f"{material_result.get('created_warehouses', 0)} entrepôts créés, "
            f"{quotation_result.get('imported_rfqs', 0)} demandes de devis créées."
        )
        frappe.msgprint(message, title="Succès de l'importation globale")
        return {
            "status": "success",
            "message": message,
            "suppliers": supplier_result,
            "materials": material_result,
            "quotations": quotation_result
        }

    except Exception as e:
        # En cas d'erreur, rollback à l'état initial
        try:
            frappe.db.rollback(save_point="import_generals")
        except Exception as rollback_e:
            frappe.log_error(f"Erreur lors du rollback : {str(rollback_e)}", "Rollback Error")
        message = f"Importation globale annulée en raison d'une erreur : {str(e)}"
        frappe.log_error(title="Global CSV Import Error", message=message)
        frappe.msgprint(message, title="Échec de l'importation globale")
        return {
            "status": "error",
            "message": message,
            "suppliers": {},
            "materials": {},
            "quotations": {}
        }