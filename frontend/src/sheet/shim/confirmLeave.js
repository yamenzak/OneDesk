// Derived from frappe/suite@df7f341 (frontend/src/utils/confirmLeave.ts). Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0.
import { dialog } from "frappe-ui";

import { __ } from "../../kit/desk";

export function confirmLeave({ title = __("Leave this page?"), message = __("Your unsaved changes may be lost."), confirmLabel = __("Leave") } = {}) {
	return new Promise((resolve) => {
		let settled = false;
		const finish = (value) => {
			if (settled) return;
			settled = true;
			resolve(value);
		};
		dialog.confirm({ title, message, confirmLabel, cancelLabel: __("Stay"), theme: "red", onConfirm: () => finish(true), onCancel: () => finish(false) });
	});
}
