// What Suite's session store gave the slides editor, read from the desk's own session.
import { person } from "../../kit/desk";

export * from "../../doc/shim/session.js";

export const session = {
	get user() {
		return { sessionUser: person().name };
	},
};
