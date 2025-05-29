import frappe
from frappe.utils.pdf import get_pdf
import csv
from frappe.utils import now_datetime
import frappe.utils.file_manager
import io

@frappe.whitelist()
def import_suppliers(file_url):
    
    try:
        # Vérifier les permissions pour Supplier et Country
        if not frappe.has_permission("Supplier", "create"):
            frappe.throw("Vous n'avez pas la permission de créer des fournisseurs.", frappe.PermissionError)
        if not frappe.has_permission("Country", "create"):
            frappe.throw("Vous n'avez pas la permission de créer des pays.", frappe.PermissionError)

        # Récupérer le fichier depuis l'URL
        file_doc = frappe.get_doc("File", {"file_url": file_url})
        if not file_doc:
            frappe.throw(f"Fichier non trouvé pour l'URL : {file_url}")

        # Obtenir le chemin physique du fichier
        file_path = frappe.get_site_path("public", file_doc.file_url.lstrip("/"))

        # Lire le contenu du fichier
        with open(file_path, mode="r", encoding="utf-8") as f:
            csv_reader = csv.DictReader(f, delimiter=',')

            # Vérifier les en-têtes attendus
            expected_headers = ["supplier_name", "country", "type"]
            if not all(header in csv_reader.fieldnames for header in expected_headers):
                frappe.throw(f"Le fichier CSV doit contenir les colonnes : {', '.join(expected_headers)}")

            # Créer des listes temporaires pour les documents
            countries_temp = []
            suppliers_temp = []
            errors = []

            # Étape 1 : Valider toutes les lignes et préparer les documents
            for row in csv_reader:
                supplier_name = row.get("supplier_name", "").strip()
                country = row.get("country", "").strip()
                supplier_type = row.get("type", "").strip()

                # Validation des données
                if not supplier_name:
                    errors.append(f"Ligne {csv_reader.line_num}: supplier_name est vide.")
                    raise frappe.ValidationError(errors[-1])
                if not country:
                    errors.append(f"Ligne {csv_reader.line_num}: country est vide pour le fournisseur '{supplier_name}'.")
                    raise frappe.ValidationError(errors[-1])
                if supplier_type not in ["Company", "Individual"]:
                    errors.append(f"Ligne {csv_reader.line_num}: type '{supplier_type}' invalide pour le fournisseur '{supplier_name}'. Valeurs valides : Company, Individual.")
                    raise frappe.ValidationError(errors[-1])

                # Vérifier si le fournisseur existe déjà
                if frappe.db.exists("Supplier", {"supplier_name": supplier_name}):
                    errors.append(f"Ligne {csv_reader.line_num}: Le fournisseur '{supplier_name}' existe déjà.")
                    raise frappe.ValidationError(errors[-1])

                # Vérifier si le pays existe, sinon le créer (en mémoire)
                if not frappe.db.exists("Country", {"name": country}):
                    country_doc = frappe.get_doc({
                        "doctype": "Country",
                        "name": country,
                        "country_name": country,  # Ajout du champ requis
                        "creation": now_datetime(),
                        "modified": now_datetime(),
                        "owner": frappe.session.user,
                        "code":"NA"
                    })
                    countries_temp.append(country_doc)

                # Créer un document temporaire pour le fournisseur
                supplier = frappe.get_doc({
                    "doctype": "Supplier",
                    "supplier_name": supplier_name,
                    "country": country,
                    "supplier_type": supplier_type,
                    "creation": now_datetime(),
                    "modified": now_datetime(),
                    "owner": frappe.session.user
                })
                suppliers_temp.append(supplier)

            # Étape 2 : Insérer tous les documents dans une transaction
            try:
                frappe.db.savepoint("import_suppliers")  # Point de rollback

                # Insérer les nouveaux pays
                for country_doc in countries_temp:
                    country_doc.insert(ignore_permissions=False)

                # Insérer les fournisseurs
                for supplier in suppliers_temp:
                    supplier.insert(ignore_permissions=False)

                frappe.db.commit()
                message = f"Importation terminée : {len(suppliers_temp)} fournisseurs importés, {len(countries_temp)} pays créés."
                frappe.msgprint(message, title="Succès de l'importation")
                return {
                    "status": "success",
                    "message": message,
                    "imported_suppliers": len(suppliers_temp),
                    "created_countries": len(countries_temp),
                    "skipped": 0
                }

            except Exception as e:
                frappe.db.rollback(save_point="import_suppliers")
                message = f"Importation annulée en raison d'une erreur : {str(e)}"
                frappe.log_error(title="Supplier CSV Import Error", message=message)
                frappe.msgprint(message, title="Échec de l'importation")
                return {
                    "status": "error",
                    "message": message,
                    "imported_suppliers": 0,
                    "created_countries": 0,
                    "skipped": len(suppliers_temp)
                }

    except frappe.PermissionError:
        frappe.log_error("Permission Error in import_csv2", frappe.get_traceback())
        frappe.throw("Vous n'avez pas les permissions nécessaires pour importer des fournisseurs ou des pays.", frappe.PermissionError)
    except Exception as e:
        frappe.log_error(f"Error in import_csv2: {str(e)}", frappe.get_traceback())
        frappe.throw(f"Erreur lors de l'importation des fournisseurs : {str(e)}")