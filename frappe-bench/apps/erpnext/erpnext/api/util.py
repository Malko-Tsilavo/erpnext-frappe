import frappe

@frappe.whitelist()
def submit_doctype(doctype, name):
    """
    Soumet un document donné en mettant à jour son docstatus à 1.

    Args:
        doctype (str): Type de document (par exemple, 'Supplier Quotation')
        name (str): Nom du document (par exemple, 'SQ-00001')

    Returns:
        dict: Message de succès avec les détails du document soumis

    Raises:
        frappe.exceptions.DoesNotExistError: Si le document n'existe pas
        frappe.exceptions.PermissionError: Si l'utilisateur n'a pas la permission de soumettre
        frappe.exceptions.ValidationError: Si le document ne peut pas être soumis
    """
    try:
        # Charger le document
        doc = frappe.get_doc(doctype, name)

        # Vérifier que le document est en état Draft (docstatus=0)
        if doc.docstatus != 0:
            frappe.throw(_("Le document {0} {1} n'est pas en état Draft (docstatus=0).").format(doctype, name))

        # Soumettre le document
        doc.submit()

        # Retourner un message de succès avec les détails du document
        return {
            "message": "Document soumis avec succès",
            "doctype": doctype,
            "name": name,
            "docstatus": doc.docstatus
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Échec de la soumission du document {0} {1}").format(doctype, name))
        frappe.throw(_("Échec de la soumission : {0}").format(str(e)))