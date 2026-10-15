// The portal's server (onedesk/one/portal.py), through frappe-ui's request,
// which carries frappe's CSRF token and turns frappe's errors into throws.
import { frappeRequest } from "frappe-ui";

export const call = (method, params = {}) =>
	frappeRequest({ url: `/api/method/${method.includes(".") ? method : `onedesk.one.portal.${method}`}`, params });
