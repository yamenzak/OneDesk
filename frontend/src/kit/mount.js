// How every OneDesk island mounts: frappe's mount contract, with desk's `__`
// in every template and desk's socket for @framework/ui's live parts.
// frappe-ui's resources call frappe's API through frappeRequest, as a Frappe
// UI app sets it up at start; without it a part that doesn't pass its own
// fetcher (@framework/ui's timeline) calls a path relative to the page.
import { frappeRequest, setConfig } from "frappe-ui";
import { mountVueIsland } from "@framework/ui/island";

import { __, deskSession } from "./desk";

setConfig("resourceFetcher", frappeRequest);

export const screen = (component) => (el, context) => {
	const { socket } = deskSession();
	return mountVueIsland(el, {
		...context,
		component,
		configure: (app) => {
			app.config.globalProperties.__ = __;
			if (socket) app.provide("socket", socket);
		},
	});
};
