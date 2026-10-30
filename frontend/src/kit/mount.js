import { h } from "vue";
import { FrappeUIProvider, frappeRequest, setConfig } from "frappe-ui";
import { mountVueIsland } from "@framework/ui/island";

import { __, deskSession, timeZone } from "./desk";

setConfig("resourceFetcher", frappeRequest);
const zone = timeZone();
if (zone.system) setConfig("systemTimezone", zone.system);
if (zone.user) setConfig("localTimezone", zone.user);

const provided = (component) => ({
	name: "OneIsland",
	inheritAttrs: false,
	render() {
		return h(FrappeUIProvider, null, { default: () => h(component, this.$attrs) });
	},
});

export const screen = (component, routes) => (el, context) => {
	const { socket } = deskSession();
	return mountVueIsland(el, {
		...context,
		...(routes ? { routes } : {}),
		component: provided(component),
		configure: (app) => {
			app.config.globalProperties.__ = __;
			if (socket) app.provide("socket", socket);
		},
	});
};
