import frappe
import requests

@frappe.whitelist()
def export_purchase_order_to_v15(po_name):
	try:
		doc = frappe.get_doc("Purchase Order", po_name)
		config = frappe.get_single("PISPL Configuration")
		v15_url = config.url
		headers = {
			"Authorization": f"token {config.api_key}:{config.api_secret}",
			"Content-Type": "application/json"
		}

		customer = "Advanced Crushing Engineers Private Limited"

		items = []
		for item in doc.items:
			v15_item_code = frappe.db.get_value(
				"Item Supplier",
				{"parent": item.item_code},
				"supplier_part_no"
			)
			if not v15_item_code:
				frappe.log_error(f"Item {item.item_code} has no supplier_part_no", "PO Export Error")
				continue

			items.append({
				"item_code": v15_item_code,
				"qty": item.qty,
				"rate": item.rate
			})

		if not items:
			frappe.log_error(f"PO {po_name} has no valid items to export", "PO Export Error")
			return

		payload = {
			"customer": customer,
			"items": items
		}
		response = requests.post(f"{v15_url}/api/resource/Sales Order", json=payload, headers=headers)

		if response.status_code == 200:
			frappe.msgprint(f"Sales Order created in PISPL v15 for PO {po_name}")
		else:
			frappe.log_error(f"Failed to export PO {po_name}: {response.text}", "PO Export Error")

	except Exception as e:
		frappe.log_error(f"Error exporting PO {po_name}: {str(e)}", "PO Export Error")

def validate_supplier_part_number(doc, method):

	"""Ensure all items have a Supplier Part Number when supplier is 'Proman Infrastructure Services Private Limited'"""
	
	supplier_name = "Proman Infrastructure Services Private Limited"
	
	if doc.supplier != supplier_name:
		return
	
	missing_items = []

	for item in doc.items:
		supplier_part_no = frappe.db.get_value(
			"Item Supplier",
			{"parent": item.item_code, "supplier": doc.supplier},
			"supplier_part_no"
		)

		if not supplier_part_no:
			missing_items.append(item.item_code)
	
	if missing_items:
		missing_items_str = ", ".join(missing_items)

		error_message = f"Missing Supplier Part Numbers in: {missing_items_str}"
		log = frappe.log_error(error_message, "Supplier Part Number missing")

		log_name = log.name if log else ""

		error_log_link = (
			f'<a href="/app/error-log/{log_name}" target="_blank">View Error Log</a>'
			if log_name
			else "Check Error Log for details."
		)

		error_message = f"Missing Supplier Part Numbers in: <br> {missing_items_str}"
		frappe.throw(f"{error_message}<br>{error_log_link}")
