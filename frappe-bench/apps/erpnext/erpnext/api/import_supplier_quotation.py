import frappe
import csv
from frappe.utils import nowdate, now_datetime
from frappe import _
from erpnext.buying.doctype.request_for_quotation.request_for_quotation import make_supplier_quotation_from_rfq

@frappe.whitelist()
def import_supplier_quotations(file_url):
    """
    Importe des Request for Quotation et Supplier Quotation à partir d'un fichier CSV.
    Crée une RFQ pour chaque ref_request_quotation, avec les fournisseurs associés.
    Utilise le champ 'ref_request_quotation' pour lier au Material Request via le champ 'ref'.
    Crée des Supplier Quotation pour chaque fournisseur de chaque RFQ.

    CSV attendu :
        ref_request_quotation,supplier
        1,Sanifer
        1,Exxon
        2,Sanifer

    Args:
        file_url (str): URL du fichier CSV dans le doctype File.

    Returns:
        dict: Statut de l'importation et message.
    """
    try:
        # Vérifier les permissions
        if not frappe.has_permission("Request for Quotation", "create") or not frappe.has_permission("Supplier Quotation", "create"):
            frappe.throw("Vous n'avez pas la permission de créer des Request for Quotation ou Supplier Quotation.", frappe.PermissionError)

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
            expected_headers = ["ref_request_quotation", "supplier"]
            if not all(header in csv_reader.fieldnames for header in expected_headers):
                frappe.throw(f"Le fichier CSV doit contenir les colonnes : {', '.join(expected_headers)}")

            # Listes temporaires pour les documents
            rfqs_temp = []
            warehouses_temp = []  # Pour stocker les nouveaux entrepôts créés
            errors = []

            # Regrouper les lignes par ref_request_quotation
            rfqs_by_ref = {}
            for row in csv_reader:
                ref = row.get("ref_request_quotation", "").strip()
                supplier = row.get("supplier", "").strip()

                if not ref:
                    errors.append(f"Ligne {csv_reader.line_num}: ref_request_quotation est vide.")
                    raise frappe.ValidationError(errors[-1])
                if not supplier:
                    errors.append(f"Ligne {csv_reader.line_num}: supplier est vide.")
                    raise frappe.ValidationError(errors[-1])

                if ref in rfqs_by_ref:
                    rfqs_by_ref[ref].append(row)
                else:
                    rfqs_by_ref[ref] = [row]

            # Étape 1 : Valider toutes les lignes et préparer les documents
            for ref, rows in rfqs_by_ref.items():
                # Vérifier l'existence du Material Request via le champ ref
                material_request_name = frappe.db.get_value(
                    "Material Request",
                    {"ref": ref},
                    "name"
                )
                if not material_request_name:
                    errors.append(f"Ligne {csv_reader.line_num}: Le Material Request avec ref '{ref}' n'existe pas.")
                    raise frappe.ValidationError(errors[-1])

                # Vérifier les fournisseurs et préparer la liste
                suppliers = []
                for row in rows:
                    supplier = row.get("supplier", "").strip()
                    if not frappe.db.exists("Supplier", supplier):
                        errors.append(f"Ligne {csv_reader.line_num}: Le Supplier '{supplier}' n'existe pas.")
                        raise frappe.ValidationError(errors[-1])
                    suppliers.append({"supplier": supplier})

                # Créer un document temporaire pour Request for Quotation
                rfq = frappe.get_doc({
                    "doctype": "Request for Quotation",
                    "transaction_date": nowdate(),
                    "material_request": material_request_name,
                    "message_for_supplier": "Please provide your best quote",
                    "suppliers": suppliers,
                    "items": get_items_material_request(material_request_name, warehouses_temp),
                    "creation": now_datetime(),
                    "modified": now_datetime(),
                    "owner": frappe.session.user
                })
                rfqs_temp.append(rfq)

            # Étape 2 : Insérer tous les documents dans une transaction
            try:
                frappe.db.savepoint("import_quotations")  # Point de rollback

                # Insérer les nouveaux entrepôts créés
                for warehouse_doc in warehouses_temp:
                    try:
                        warehouse_doc.insert(ignore_permissions=False)
                        frappe.log_error(f"Entrepôt inséré : {warehouse_doc.name} pour la compagnie {warehouse_doc.company}", "Debug Warehouse")
                    except frappe.DuplicateEntryError:
                        frappe.log_error(f"Entrepôt '{warehouse_doc.name}' existe déjà, ignoré.", "Debug Warehouse")
                        continue

                # Insérer et soumettre les Request for Quotation
                inserted_rfqs = []
                for rfq in rfqs_temp:
                    frappe.log_error(f"Inserting RFQ: {rfq.name}, Items: {rfq.items}", "Debug RFQ Insertion")
                    rfq.insert(ignore_permissions=False)
                    rfq.submit()
                    inserted_rfqs.append(rfq)

                # Créer les Supplier Quotation à partir des RFQ
                supplier_quotations = create_supplier_quotations(inserted_rfqs)

                # Soumettre les Supplier Quotation
                for quotation in supplier_quotations:
                    frappe.log_error(f"Submitting Supplier Quotation: {quotation.name}, Supplier: {quotation.supplier}", "Debug Supplier Quotation")
                    quotation.submit()

                frappe.db.commit()
                message = f"Importation terminée : {len(inserted_rfqs)} Request for Quotation et {len(supplier_quotations)} Supplier Quotation créées."
                frappe.msgprint(message, title="Succès de l'importation")
                return {
                    "status": "success",
                    "message": message,
                    "imported_rfqs": len(inserted_rfqs),
                    "imported_supplier_quotations": len(supplier_quotations),
                    "skipped": 0
                }

            except Exception as e:
                frappe.db.rollback(save_point="import_quotations")
                message = f"Importation annulée en raison d'une erreur : {str(e)}"
                frappe.log_error(title="Quotation CSV Import Error", message=message)
                frappe.msgprint(message, title="Échec de l'importation")
                return {
                    "status": "error",
                    "message": message,
                    "imported_rfqs": 0,
                    "imported_supplier_quotations": 0,
                    "skipped": len(rfqs_temp)
                }

    except frappe.PermissionError:
        frappe.log_error("Permission Error in import_supplier_quotations", frappe.get_traceback())
        frappe.throw("Vous n'avez pas les permissions nécessaires pour importer des Request for Quotation ou Supplier Quotation.", frappe.PermissionError)
    except Exception as e:
        frappe.log_error(f"Error in import_supplier_quotations: {str(e)}", frappe.get_traceback())
        frappe.throw(f"Erreur lors de l'importation : {str(e)}")

def create_supplier_quotations(rfqs):
    """
    Crée des Supplier Quotation pour chaque fournisseur de chaque Request for Quotation.
    
    Args:
        rfqs (list): Liste des documents Request for Quotation.
    
    Returns:
        list: Liste des Supplier Quotation créées.
    """
    created_quotations = []
    try:
        for rfq in rfqs:
            for supplier in rfq.suppliers:
                quotation = make_supplier_quotation_from_rfq(rfq.name, for_supplier=supplier.supplier)
                quotation.insert()
                created_quotations.append(quotation)
    except Exception as e:
        frappe.throw(f"Erreur lors de la création des Supplier Quotation : {str(e)}")
    return created_quotations

def get_items_material_request(material_request_name, warehouses_temp):
    """
    Récupère les éléments d'un Material Request pour les utiliser dans une Request for Quotation.
    Vérifie si l'entrepôt appartient à la compagnie Test (Demo), sinon en crée un nouveau.
    
    Args:
        material_request_name (str): Nom du Material Request.
        warehouses_temp (list): Liste des entrepôts temporaires à insérer.
    
    Returns:
        list: Liste des éléments formatés pour RFQ.
    """
    material_request = frappe.get_doc("Material Request", material_request_name)
    company = "Test (Demo)"  # Forcer la compagnie à Test (Demo)
    if not frappe.db.exists("Company", company):
        frappe.throw(f"La compagnie 'Test (Demo)' n'existe pas dans ERPNext pour le Material Request {material_request_name}.")

    items = []
    for item in material_request.items:
        # Récupérer l'article pour obtenir la stock_uom
        article = frappe.get_doc("Item", item.item_code)
        stock_uom = article.stock_uom
        uom = item.uom or stock_uom  # Utiliser l'uom du Material Request Item ou stock_uom par défaut

        # Déterminer le conversion_factor
        conversion_factor = item.conversion_factor or 1.0
        if uom != stock_uom:
            # Récupérer le facteur de conversion depuis UOM Conversion Detail
            conversion_factor = frappe.db.get_value(
                "UOM Conversion Detail",
                {"parent": item.item_code, "uom": uom},
                "conversion_factor"
            )
            if not conversion_factor:
                frappe.throw(f"Facteur de conversion manquant pour l'article {item.item_code} avec UOM {uom}. Veuillez configurer les conversions UOM dans la fiche article.")

        # Vérifier l'entrepôt
        warehouse = item.warehouse
        if warehouse:
            # Vérifier si l'entrepôt existe et appartient à la compagnie
            warehouse_info = frappe.db.get_value(
                "Warehouse",
                {"name": warehouse},
                ["name", "company", "warehouse_name"],
                as_dict=True
            )
            if warehouse_info and warehouse_info.company == company:
                # Entrepôt valide, utiliser tel quel
                frappe.log_error(f"Entrepôt valide : {warehouse} pour la compagnie {company}", "Debug Warehouse")
            else:
                # Entrepôt inexistant ou appartenant à une autre compagnie, créer un nouveau
                warehouse_name = warehouse_info.warehouse_name if warehouse_info else warehouse.split(" - ")[0]
                company_abbr = frappe.db.get_value("Company", company, "abbr")
                if not company_abbr:
                    frappe.throw(f"Aucune abréviation définie pour la compagnie '{company}'.")

                new_warehouse_name = f"{warehouse_name} - {company_abbr}"
                # Vérifier si le nouvel entrepôt est déjà dans warehouses_temp
                if not any(doc.name == new_warehouse_name for doc in warehouses_temp):
                    # Vérifier si l'entrepôt existe déjà dans la base
                    if not frappe.db.exists("Warehouse", new_warehouse_name):
                        warehouse_doc = frappe.get_doc({
                            "doctype": "Warehouse",
                            "warehouse_name": warehouse_name,
                            "name": new_warehouse_name,
                            "is_group": 0,
                            "company": company,
                            "creation": now_datetime(),
                            "modified": now_datetime(),
                            "owner": frappe.session.user
                        })
                        warehouses_temp.append(warehouse_doc)
                        frappe.log_error(f"Nouvel entrepôt ajouté à warehouses_temp : {new_warehouse_name} pour la compagnie {company}", "Debug Warehouse")
                    else:
                        frappe.log_error(f"Entrepôt existant utilisé : {new_warehouse_name} pour la compagnie {company}", "Debug Warehouse")
                warehouse = new_warehouse_name

        items.append({
            "item_code": item.item_code,
            "qty": item.qty,
            "warehouse": warehouse,
            "uom": uom,
            "conversion_factor": conversion_factor
        })
    frappe.log_error(f"Items for Material Request {material_request_name}: {items}", "Debug Items")
    return items