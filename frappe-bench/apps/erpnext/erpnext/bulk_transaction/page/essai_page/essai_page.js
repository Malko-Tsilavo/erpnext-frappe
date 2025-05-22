frappe.pages['essai-page'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'The Page',
		single_column: true
	});
}