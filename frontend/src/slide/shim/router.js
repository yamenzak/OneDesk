// Suite's stores reach the router as a module, not through inject. The island's
// own router (PresentationPage.vue) is put here when it mounts, with what the
// reader may do with the presentation open (Suite's routerState.ts).
let held = null;
let allowed = "none";

export const holdRouter = (router) => (held = router);
export const allow = (said) => (allowed = said || "none");
export const access = () => allowed;

export const router = {
	get currentRoute() {
		return held?.currentRoute || { value: { params: {}, query: {}, name: null } };
	},
	replace: (to) => held?.replace(to),
	push: (to) => held?.push(to),
};

export default router;
