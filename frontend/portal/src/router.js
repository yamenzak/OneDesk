import { createRouter, createWebHistory } from "vue-router";

const routes = [
	{ path: "/", name: "Home", component: () => import("./pages/Home.vue") },
	{ path: "/menu", name: "Menu", component: () => import("./pages/Menu.vue") },
	{ path: "/profile", name: "Profile", component: () => import("./pages/Profile.vue") },
	{ path: "/password", name: "Password", component: () => import("./pages/Password.vue") },
	{ path: "/your-data", name: "YourData", component: () => import("./pages/YourData.vue") },
	{ path: "/apps", name: "Apps", component: () => import("./pages/Apps.vue") },
	{ path: "/addresses/:name", name: "Address", component: () => import("./pages/Address.vue"), props: true },
	{ path: "/rfq/:name", name: "Rfq", component: () => import("./pages/Rfq.vue"), props: true },
	{ path: "/projects/:name", name: "Project", component: () => import("./pages/Project.vue"), props: true },
	{ path: "/start", name: "Start", component: () => import("./pages/Start.vue"), meta: { bare: true } },
	{ path: "/l/:token", name: "Link", component: () => import("./pages/Link.vue"), props: true, meta: { bare: true } },
	{ path: "/:kind", name: "List", component: () => import("./pages/List.vue"), props: true },
	{ path: "/:kind/:name", name: "Record", component: () => import("./pages/Record.vue"), props: true },
];

export default createRouter({ history: createWebHistory("/portal"), routes });
