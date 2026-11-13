// Suite's editor asks Suite's server by Suite's names. Every request a vendored
// file makes comes through here and is answered by one_deck/api.py, so the
// vendored files keep Suite's names and a refresh is a copy. VENDORED.md.
import { toValue } from "vue";
import {
	FileUploadHandler as Handler,
	call as asked,
	createResource as resourced,
	frappeRequest as requested,
	useKeyboardShortcut as shortcut,
} from "frappe-ui";

import { slideRoot } from "./root.js";

export * from "frappe-ui";

const API = "onedesk.one_deck.api.";
const SUITE = ["suite.slides.doctype.presentation.presentation.", "suite.slides.api.slides.", "suite.slides.api.presentation."];

export function moved(url, params) {
	if (typeof url !== "string") return url;
	if (url === "frappe.client.get" && params?.doctype === "Presentation") return API + "get";
	if (url === "suite.drive.api.files.track_visit") return API + "visited";
	const from = SUITE.find((prefix) => url.startsWith(prefix));
	return from ? API + url.slice(from.length) : url;
}

export const call = (method, args, options) => asked(moved(method, args), args, options);
export const frappeRequest = (options) => requested({ ...options, url: moved(options.url, options.params) });
export const createResource = (options) => resourced({ ...options, url: moved(options.url, options.params) });

export class FileUploadHandler extends Handler {
	upload(file, options = {}) {
		return super.upload(file, { ...options, upload_endpoint: `/api/method/${API}upload` });
	}
}

// frappe-ui decides whether a key was typed into a field from the event's
// target, which a listener on the document sees as the island's host. So
// typing an "l" in a slide's text started the line tool. The focused element
// inside the island is asked instead, before frappe-ui's own check.
const focused = () => slideRoot().activeElement;
const typing = () => {
	const at = focused();
	return Boolean(at && (at.isContentEditable || at.tagName === "INPUT" || at.tagName === "TEXTAREA"));
};
const inDialog = () => Boolean(focused()?.closest?.('[role="dialog"]'));

export function useKeyboardShortcut(shortcuts) {
	const listed = Array.isArray(shortcuts) ? shortcuts : [shortcuts];
	return shortcut(
		listed.map((config) => ({
			...config,
			enabled: () =>
				toValue(config.enabled ?? true) && (config.allowInInput || !typing()) && (config.allowInDialog || !inDialog()),
		}))
	);
}
