// How every OneDesk island mounts: frappe's mount contract, with desk's `__`
// in every template and desk's socket for @framework/ui's live parts.
// frappe-ui's resources call frappe's API through frappeRequest, as a Frappe
// UI app sets it up at start; without it a part that doesn't pass its own
// fetcher (@framework/ui's timeline) calls a path relative to the page.
import { frappeRequest, setConfig } from "frappe-ui";
import { mountVueIsland } from "@framework/ui/island";

import { __, deskSession, timeZone } from "./desk";

setConfig("resourceFetcher", frappeRequest);
// Frappe stores times in the site's timezone; frappe-ui shows them in the
// reader's, as a Frappe UI app does from its boot. Without it a time an hour
// ago reads "in 3 hours" wherever the two differ.
const zone = timeZone();
if (zone.system) setConfig("systemTimezone", zone.system);
if (zone.user) setConfig("localTimezone", zone.user);

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
