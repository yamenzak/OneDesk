import { frappeRequest } from "frappe-ui";

export const call = (method, params = {}) =>
	frappeRequest({ url: `/api/method/${method.includes(".") ? method : `onedesk.one.portal.${method}`}`, params });
