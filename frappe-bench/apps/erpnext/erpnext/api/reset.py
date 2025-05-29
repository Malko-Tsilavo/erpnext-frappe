import frappe

@frappe.whitelist()
def reset_imported_data():
    # 🛑 Tables à NE PAS supprimer (à conserver)
    excluded_tables = [
        "__Auth","__UserSettings", "__global_search", "bisect_nodes_id_seq", "crm_note_id_seq",
        "ledger_health_id_seq", "prospect_opportunity_id_seq",
        "tabAccount", "tabActivity Type", "tabAddress Template", "tabComment",
        "tabCompany", "tabContact", "tabCost Center", "tabCountry", "tabCurrency",
        "tabCurrency Exchange Settings Details", "tabCurrency Exchange Settings Result",
        "tabCustom Field", "tabCustomer Group", "tabDashboard", "tabDashboard Chart",
        "tabDashboard Chart Field", "tabDashboard Chart Link", "tabDefaultValue",
        "tabDeleted Document", "tabDepartment", "tabDesignation", "tabDocField",
        "tabDocPerm", "tabDocType", "tabDocType Action", "tabDocType Link", "tabDocType State",
        "tabDomain", "tabEmail Account", "tabEmail Unsubscribe", "tabError Log", "tabFile",
        "tabGender", "tabGlobal Search DocType", "tabHas Role", "tabIncoterm",
        "tabIndustry Type", "tabIssue Priority", "tabItem Attribute", "tabItem Attribute Value",
        "tabItem Group", "tabLanguage", "tabLogs To Clear", "tabMarket Segment",
        "tabMode of Payment", "tabModule Def", "tabNavbar Item", "tabNotification Recipient",
        "tabNotification Settings", "tabNumber Card", "tabNumber Card Link",
        "tabOpportunity Type", "tabPage", "tabParty Type", "tabPatch Log",
        "tabPortal Menu Item", "tabPrice List", "tabPrint Format", "tabPrint Heading",
        "tabPrint Style", "tabProject Type", "tabProperty Setter", "tabReport",
        "tabRole", "tabRole Profile", "tabRoute History", "tabSales Partner Type",
        "tabSales Person", "tabSales Stage", "tabSalutation", "tabScheduled Job Log",
        "tabScheduled Job Type", "tabSessions", "tabShare Type", "tabSingles",
        "tabStock Entry Type", "tabSuccess Action", "tabSupplier Group",
        "tabSupplier Scorecard Standing", "tabSupplier Scorecard Variable",
        "tabTerritory", "tabUOM", "tabUOM Category", "tabUOM Conversion Factor",
        "tabUTM Source", "tabUser", "tabUser Type", "tabVariant Field", "tabVersion",
        "tabWarehouse", "tabWeb Form", "tabWeb Form Field", "tabWeb Template",
        "tabWeb Template Field", "tabWorkflow Action Master", "tabWorkflow State",
        "tabWorkspace", "tabWorkspace Chart", "tabWorkspace Link",
        "tabWorkspace Number Card", "tabWorkspace Shortcut", "web_form_list_column_id_seq","tabFiscal Year"
    ]

    # 🔄 Récupérer toutes les tables
    all_tables = [row[0] for row in frappe.db.sql("SHOW TABLES")]

    # 🔁 Supprimer les données sauf pour les tables exclues
    for table in all_tables:
        if table not in excluded_tables:
            try:
                frappe.db.sql(f"DELETE FROM `{table}`")
            except Exception as e:
                frappe.log_error(f"Erreur lors de la suppression des données dans {table}: {e}")

    frappe.db.commit()

    return {"status": "success", "message": "Toutes les données sauf celles exclues ont été supprimées avec succès."}
