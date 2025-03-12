import frappe
import requests
from frappe.utils import formatdate

@frappe.whitelist()
def export_purchase_order_to_v15(po_name):
	try:
		doc = frappe.get_doc("Purchase Order", po_name)
		config = frappe.get_single("PISPL Configuration")
		password = config.get_password('password')
		v15_url = config.url
		headers = {
			"Authorization": f"token {config.api_key}:{password}",
			"Content-Type": "application/json"
		}

		items = []
		for item in doc.items:
			v15_item_code = frappe.db.get_value(
				"Item Supplier",
				{"parent": item.item_code},
				"supplier_part_no"
			)

			items.append({
				"item_code": v15_item_code,
				"qty": item.qty,
				"rate": item.rate,
				"delivery_date": item.schedule_date.strftime("%Y-%m-%d") if item.schedule_date else None
			})

		payload = {
			"items": items,
			"transaction_date": doc.transaction_date.strftime("%Y-%m-%d") if doc.transaction_date else None,
			"delivery_date": doc.schedule_date.strftime("%Y-%m-%d") if doc.schedule_date else None
		}

		frappe.log_error(title="payload", message=payload)

		response = requests.post(f"{v15_url}/api/method/proman.proman.utils.create_sales_order.create_sales_order", json=payload, headers=headers)

		if response.status_code == 200:
			frappe.log_error(f"{response.text}", "PO Export Success")
			return {"status": "success", "message": f"Sales Order created in PISPL v15 for PO {po_name}"}
		else:
			error_msg = f"Failed to export PO {po_name}: {response.text}"
			frappe.log_error(error_msg, "PO Export Error")
			return {"status": "error", "message": error_msg}

	except Exception as e:
		error_msg = f"Error exporting PO {po_name}: {str(e)}"
		frappe.log_error(error_msg, "PO Export Error")
		return {"status": "error", "message": error_msg}

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
