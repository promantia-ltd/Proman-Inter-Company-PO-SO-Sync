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
