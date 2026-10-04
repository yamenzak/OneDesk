// How every OneDesk island mounts: frappe's mount contract, with desk's `__`
// available in every template.
import { mountVueIsland } from "@framework/ui/island";

import { __ } from "./desk";

export const screen = (component) => (el, context) =>
	mountVueIsland(el, {
		...context,
		component,
		configure: (app) => {
			app.config.globalProperties.__ = __;
		},
	});
