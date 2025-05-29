import frappe
import csv
import io
from frappe.utils import now_datetime, getdate
from datetime import datetime

def check_date(date_str, field_name, line_num):
    """Valide une date au format DD/MM/YYYY."""
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except ValueError:
        frappe.throw(f"Ligne {line_num}: {field_name} '{date_str}' n'est pas une date valide (format attendu : DD/MM/YYYY).")

def check_quantity(quantity_str, line_num):
    """Valide que la quantité est un nombre positif."""
    try:
        qty = float(quantity_str)
        if qty <= 0:
            frappe.throw(f"Ligne {line_num}: La quantité '{quantity_str}' doit être positive.")
        return qty
    except ValueError:
        frappe.throw(f"Ligne {line_num}: La quantité '{quantity_str}' n'est pas un nombre valide.")

def check_purpose(purpose, line_num):
    """Valide que le purpose est une valeur valide pour material_request_type."""
    valid_purposes = ["Purchase", "Material Transfer", "Material Issue", "Customer Provided", "Manufacture"]
    if purpose not in valid_purposes:
        frappe.throw(f"Ligne {line_num}: Purpose '{purpose}' invalide. Valeurs valides : {', '.join(valid_purposes)}.")
    return purpose

def check_item(item_name, item_group, line_num, items_temp, item_groups_temp):
    """Vérifie si l'article existe, sinon le crée."""
    if not item_name:
        frappe.throw(f"Ligne {line_num}: item_name est vide.")
    
    if frappe.db.exists("Item", {"item_code": item_name}):
        item = frappe.get_doc("Item", item_name)
        if item.item_group != item_group:
            frappe.msgprint(f"Ligne {line_num}: L'article '{item_name}' appartient au groupe '{item.item_group}', mais '{item_group}' est spécifié. Utilisation de '{item.item_group}'.")
        return item_name
    
    item_group_name = check_item_group(item_group, line_num, item_groups_temp)
    
    item_doc = frappe.get_doc({
        "doctype": "Item",
        "item_code": item_name,
        "item_name": item_name,
        "item_group": item_group_name,
        "is_stock_item": 1,
        "stock_uom": "Nos" if item_name != "ciment" else "Kg",
        "creation": now_datetime(),
        "modified": now_datetime(),
        "owner": frappe.session.user
    })
    items_temp.append(item_doc)
    return item_name

def check_item_group(item_group, line_num, item_groups_temp):
    """Vérifie si le groupe d'articles existe, sinon le crée."""
    if not item_group:
        frappe.throw(f"Ligne {line_num}: item_groupe est vide.")
    
    if frappe.db.exists("Item Group", {"item_group_name": item_group}):
        return item_group
    
    parent_item_group = "All Item Groups"
    parent_group = frappe.db.get_value("Item Group", {"item_group_name": parent_item_group}, "name")
    if not parent_group:
        parent_doc = frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name": parent_item_group,
            "name": parent_item_group,
            "parent_item_group": "",
            "is_group": 1,
            "creation": now_datetime(),
            "modified": now_datetime(),
            "owner": frappe.session.user
        })
        if not any(doc.item_group_name == parent_item_group for doc in item_groups_temp):
            item_groups_temp.append(parent_doc)
            print(f"Groupe parent '{parent_item_group}' ajouté à item_groups_temp.")
    
    item_group_doc = frappe.get_doc({
        "doctype": "Item Group",
        "item_group_name": item_group,
        "parent_item_group": parent_group or parent_item_group,
        "is_group": 0,
        "creation": now_datetime(),
        "modified": now_datetime(),
        "owner": frappe.session.user
    })
    item_groups_temp.append(item_group_doc)
    print(f"Groupe d'articles '{item_group}' ajouté avec parent '{parent_item_group}'.")
    return item_group

def check_warehouse(warehouse_name, line_num, warehouses_temp):
    """Vérifie si l'entrepôt existe pour la compagnie Test (Demo), sinon le crée."""
    if not warehouse_name:
        frappe.throw(f"Ligne {line_num}: target_warehouse est vide.")
    
    company = "Test (Demo)"  # Forcer la compagnie à Test (Demo)
    if not frappe.db.exists("Company", company):
        frappe.throw(f"Ligne {line_num}: La compagnie 'Test (Demo)' n'existe pas dans ERPNext.")

    print(f'Vérification entrepôt "{warehouse_name}" pour la compagnie "{company}"')
    frappe.log_error(f'Vérification entrepôt "{warehouse_name}" pour la compagnie "{company}"', "Debug Warehouse")

    possible_names = [warehouse_name]
    if warehouse_name == "All Warehouse":
        possible_names.append("All Warehouses")
    elif warehouse_name == "All Warehouses":
        possible_names.append("All Warehouse")

    # Vérifier si l'entrepôt existe et appartient à la compagnie
    existing_warehouse = frappe.db.get_value(
        "Warehouse",
        {"warehouse_name": ["in", possible_names], "company": company},
        ["name", "company"],
        as_dict=True
    )
    if existing_warehouse:
        print(f"Entrepôt trouvé : {existing_warehouse.name} (Compagnie : {existing_warehouse.company})")
        frappe.log_error(f"Entrepôt trouvé : {existing_warehouse.name} (Compagnie : {existing_warehouse.company})", "Debug Warehouse")
        return existing_warehouse.name
    
    # Vérifier si l'entrepôt existe mais avec une compagnie différente
    mismatched_warehouse = frappe.db.get_value(
        "Warehouse",
        {"warehouse_name": ["in", possible_names], "company": ["!=", company]},
        ["name", "company"],
        as_dict=True
    )
    if mismatched_warehouse:
        frappe.log_error(f"Entrepôt '{mismatched_warehouse.name}' appartient à la compagnie '{mismatched_warehouse.company}', création d'un nouvel entrepôt pour '{company}'.", "Debug Warehouse")

    # Obtenir l'abréviation de la compagnie pour construire le name
    company_abbr = frappe.db.get_value("Company", company, "abbr")
    if not company_abbr:
        frappe.throw(f"Ligne {line_num}: Aucune abréviation définie pour la compagnie '{company}'.")

    warehouse_doc_name = f"{warehouse_name} - {company_abbr}"

    # Vérifier si un document avec ce name est déjà dans warehouses_temp
    if any(doc.name == warehouse_doc_name for doc in warehouses_temp):
        print(f"Entrepôt '{warehouse_doc_name}' déjà dans warehouses_temp, ignoré.")
        frappe.log_error(f"Entrepôt '{warehouse_doc_name}' déjà dans warehouses_temp, ignoré.", "Debug Warehouse")
        return warehouse_doc_name

    warehouse_doc = frappe.get_doc({
        "doctype": "Warehouse",
        "warehouse_name": warehouse_name,
        "name": warehouse_doc_name,  # Définir explicitement le name
        "is_group": 0,
        "company": company,
        "creation": now_datetime(),
        "modified": now_datetime(),
        "owner": frappe.session.user
    })
    warehouses_temp.append(warehouse_doc)
    print(f"Entrepôt '{warehouse_doc_name}' ajouté à warehouses_temp pour la compagnie '{company}'.")
    frappe.log_error(f"Entrepôt '{warehouse_doc_name}' ajouté à warehouses_temp pour la compagnie '{company}'.", "Debug Warehouse")
    return warehouse_doc_name

@frappe.whitelist()
def import_materials(file_url):
    try:
        required_doctypes = ["Material Request", "Item", "Item Group", "Warehouse"]
        for doctype in required_doctypes:
            if not frappe.has_permission(doctype, "create"):
                frappe.throw(f"Vous n'avez pas la permission de créer des {doctype}.", frappe.PermissionError)

        file_doc = frappe.get_doc("File", {"file_url": file_url})
        if not file_doc:
            frappe.throw(f"Fichier non trouvé pour l'URL : {file_url}")

        file_path = frappe.get_site_path("public", file_doc.file_url.lstrip("/"))

        with open(file_path, mode="r", encoding="utf-8") as f:
            csv_reader = csv.DictReader(f, delimiter=',')

            expected_headers = ["date", "item_name", "item_groupe", "required_by", "quantity", "purpose", "target_warehouse", "ref"]
            if not all(header in csv_reader.fieldnames for header in expected_headers):
                frappe.throw(f"Le fichier CSV doit contenir les colonnes : {', '.join(expected_headers)}")

            items_temp = []
            item_groups_temp = []
            warehouses_temp = []
            material_requests_temp = []
            errors = []

            requests_by_ref = {}
            for row in csv_reader:
                ref = row.get("ref", "").strip()
                if not ref:
                    errors.append(f"Ligne {csv_reader.line_num}: ref est vide.")
                    raise frappe.ValidationError(errors[-1])
                
                if ref in requests_by_ref:
                    requests_by_ref[ref].append(row)
                else:
                    requests_by_ref[ref] = [row]

            for ref, rows in requests_by_ref.items():
                date = check_date(rows[0].get("date", "").strip(), "date", csv_reader.line_num)
                required_by = check_date(rows[0].get("required_by", "").strip(), "required_by", csv_reader.line_num)
                purpose = check_purpose(rows[0].get("purpose", "").strip(), csv_reader.line_num)

                if frappe.db.exists("Material Request", {"ref": ref}):
                    errors.append(f"Material Request '{ref}' existe déjà.")
                    raise frappe.ValidationError(errors[-1])

                request_items = []
                for row in rows:
                    item_name = row.get("item_name", "").strip()
                    item_group = row.get("item_groupe", "").strip()
                    quantity = check_quantity(row.get("quantity", "").strip(), csv_reader.line_num)
                    warehouse = row.get("target_warehouse", "").strip()

                    item_code = check_item(item_name, item_group, csv_reader.line_num, items_temp, item_groups_temp)

                    warehouse_name = check_warehouse(warehouse, csv_reader.line_num, warehouses_temp)

                    request_items.append({
                        "item_code": item_code,
                        "qty": quantity,
                        "warehouse": warehouse_name,
                        "item_group": item_group
                    })

                material_request = frappe.get_doc({
                    "doctype": "Material Request",
                    "ref": ref,
                    "transaction_date": date,
                    "schedule_date": required_by,
                    "material_request_type": purpose,
                    "items": request_items,
                    "company": "Test (Demo)",  # Forcer la compagnie à Test (Demo)
                    "creation": now_datetime(),
                    "modified": now_datetime(),
                    "owner": frappe.session.user
                })
                material_requests_temp.append(material_request)
                frappe.log_error(f"Material Request préparé : {ref}, Items: {request_items}, Company: {material_request.company}", "Debug Material Request")

            try:
                frappe.db.savepoint("import_material_requests")

                for item_group_doc in item_groups_temp:
                    try:
                        item_group_doc.insert(ignore_permissions=False)
                        print(f"Groupe d'articles inséré : {item_group_doc.item_group_name}")
                    except frappe.DuplicateEntryError:
                        print(f"Groupe d'articles '{item_group_doc.item_group_name}' existe déjà, ignoré.")
                        continue

                for item_doc in items_temp:
                    try:
                        item_doc.insert(ignore_permissions=False)
                        print(f"Article inséré : {item_doc.item_code}")
                    except frappe.DuplicateEntryError:
                        print(f"Article '{item_doc.item_code}' existe déjà, ignoré.")
                        continue

                for warehouse_doc in warehouses_temp:
                    try:
                        warehouse_doc.insert(ignore_permissions=False)
                        print(f"Entrepôt inséré : {warehouse_doc.name}")
                        frappe.log_error(f"Entrepôt inséré : {warehouse_doc.name} pour la compagnie {warehouse_doc.company}", "Debug Warehouse")
                    except frappe.DuplicateEntryError:
                        print(f"Entrepôt '{warehouse_doc.name}' existe déjà, ignoré.")
                        continue

                for material_request in material_requests_temp:
                    frappe.log_error(f"Inserting Material Request: {material_request.ref}, Company: {material_request.company}", "Debug Material Request")
                    material_request.insert(ignore_permissions=False)
                    print(f"Material Request inséré : {material_request.ref}")

                frappe.db.commit()
                message = f"Importation terminée : {len(material_requests_temp)} demandes de matériel importées, {len(items_temp)} articles créés, {len(item_groups_temp)} groupes d'articles créés, {len(warehouses_temp)} entrepôts créés."
                frappe.msgprint(message, title="Succès de l'importation")
                return {
                    "status": "success",
                    "message": message,
                    "imported_requests": len(material_requests_temp),
                    "created_items": len(items_temp),
                    "created_item_groups": len(item_groups_temp),
                    "created_warehouses": len(warehouses_temp),
                    "skipped": 0
                }

            except Exception as e:
                frappe.db.rollback(save_point="import_material_requests")
                message = f"Importation annulée en raison d'une erreur : {str(e)}"
                frappe.log_error(title="Material Request CSV Import Error", message=message)
                frappe.msgprint(message, title="Échec de l'importation")
                return {
                    "status": "error",
                    "message": message,
                    "imported_requests": 0,
                    "created_items": 0,
                    "created_item_groups": 0,
                    "created_warehouses": 0,
                    "skipped": len(material_requests_temp)
                }

    except frappe.PermissionError:
        frappe.log_error("Permission Error in import_materials", frappe.get_traceback())
        frappe.throw("Vous n'avez pas les permissions nécessaires pour importer des demandes de matériel, articles, groupes ou entrepôts.", frappe.PermissionError)
    except Exception as e:
        frappe.log_error(f"Error in import_materials: {str(e)}", frappe.get_traceback())
        frappe.throw(f"Erreur lors de l'importation des demandes de matériel : {str(e)}")