// What Suite's session store gave the editor, read from the desk's own session.
import { computed, ref } from "vue";

import { person } from "../../kit/desk";

export const fullName = ref(person().fullName);
export const imageURL = ref(person().image);

export const getSessionUser = () => person().name;

export function useCurrentUser() {
	const user = person().name;
	return {
		user: computed(() => user),
		isLoggedIn: computed(() => Boolean(user) && user !== "Guest"),
		fullName: computed(() => fullName.value || user),
		imageURL: computed(() => imageURL.value),
		email: computed(() => user),
		systemUser: computed(() => true),
		isSystemManager: computed(() => person().roles.includes("System Manager")),
		jmapUser: computed(() => false),
	};
}

export function useSessionStore() {
	return { isLoggedIn: false, user: person().name, logout: { submit() {} } };
}
