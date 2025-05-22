import frappe
from frappe.utils.pdf import get_pdf
import csv
from frappe.utils import now_datetime

@frappe.whitelist()
def reset_customer_data():
    frappe.db.delete("Customer", {})
    frappe.db.commit()
    return {"status": "success", "message": "All Customer data deleted successfully."}

def import_data():
    import frappe

@frappe.whitelist()
def importer_csv_sql_complet(file_url):
    file_doc = frappe.get_doc("File", {"file_url": file_url})
    file_path = frappe.get_site_path("public", file_doc.file_url.lstrip("/"))

    now = now_datetime()
    current_user = frappe.session.user

    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=';')

        for row in reader:
            produit = row["produit"]
            prix = row["prix"]
            tache = row["tache"]
            titre = row["titre"]
            employeur = row["employeur"]
            email = row["email"]

            frappe.db.sql("""
                INSERT IGNORE INTO tabProduit (name, prix, creation, modified, modified_by, owner, docstatus, idx)
                VALUES (%s, %s, %s, %s, %s, %s, 0, 0)
            """, (produit, prix, now, now, current_user, current_user))

            frappe.db.sql("""
                INSERT IGNORE INTO tabTache (name, titre, creation, modified, modified_by, owner, docstatus, idx)
                VALUES (%s, %s, %s, %s, %s, %s, 0, 0)
            """, (tache, titre, now, now, current_user, current_user))

            frappe.db.sql("""
                INSERT IGNORE INTO tabEmployeur (name, email, creation, modified, modified_by, owner, docstatus, idx)
                VALUES (%s, %s, %s, %s, %s, %s, 0, 0)
            """, (employeur, email, now, now, current_user, current_user))

        frappe.db.commit()

    return {"status":"success","message":"Importation SQL avec métadonnées réussie"}

def importer_csv_personnalise(file_url):
    file_doc = frappe.get_doc("File", {"file_url": file_url})
    file_path = frappe.get_site_path("public", file_doc.file_url.lstrip("/"))

    produits_temp = []
    taches_temp = []
    employeurs_temp = []

    with open(file_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=';')
        lignes = list(reader)  # On lit tout pour pouvoir tout valider

    # Étape 1 : validation + création des documents en mémoire
    for i, row in enumerate(lignes, start=1):
        produit = row.get("produit")
        prix = row.get("prix")
        tache = row.get("tache")
        titre = row.get("titre")
        employeur = row.get("employeur")
        email = row.get("email")

        if not produit or not prix:
            frappe.throw(_("Ligne {} : Le produit et le prix sont obligatoires.").format(i))

        if not tache or not titre:
            frappe.throw(_("Ligne {} : La tâche et le titre sont obligatoires.").format(i))

        if not employeur or not email:
            frappe.throw(_("Ligne {} : L'employeur et l'email sont obligatoires.").format(i))

        # Création des docs mais SANS insertion
        if not frappe.db.exists("Produit", produit):
            doc_produit = frappe.get_doc({
                "doctype": "Produit",
                "name": produit,
                "prix": prix
            })
            produits_temp.append(doc_produit)

        if not frappe.db.exists("Tache", tache):
            doc_tache = frappe.get_doc({
                "doctype": "Tache",
                "name": tache,
                "titre": titre
            })
            taches_temp.append(doc_tache)

        if not frappe.db.exists("Employeur", employeur):
            doc_employeur = frappe.get_doc({
                "doctype": "Employeur",
                "name": employeur,
                "email": email
            })
            employeurs_temp.append(doc_employeur)

    # Étape 2 : si tout est validé, on insère en base
    try:
        frappe.db.savepoint("import_perso")  # point de rollback

        for doc in produits_temp:
            doc.insert(ignore_permissions=True)

        for doc in taches_temp:
            doc.insert(ignore_permissions=True)

        for doc in employeurs_temp:
            doc.insert(ignore_permissions=True)

        frappe.db.commit()
        return _("Importation terminée avec succès.")

    except Exception as e:
        frappe.db.rollback(save_point="import_perso")
        frappe.throw(_("Échec de l'importation : {0}").format(str(e)))
        
def generer_pdf_depuis_html():
    # Ton HTML personnalisé
    html = """
    <h1>Mon super document</h1>
    <p>Ceci est un fichier PDF généré depuis Frappe !</p>
    """

    # Générer le PDF
    pdf_content = get_pdf(html)

    # Retourner une réponse fichier
    frappe.local.response.filename = "mon_fichier.pdf"
    frappe.local.response.filecontent = pdf_content
    frappe.local.response.type = "download"