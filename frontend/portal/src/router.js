// The portal's places. A tab's path is its Portal Settings route
// (one/portal.py PATHS), so /portal/orders is what /orders was.
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
	{ path: "/:kind", name: "List", component: () => import("./pages/List.vue"), props: true },
	{ path: "/:kind/:name", name: "Record", component: () => import("./pages/Record.vue"), props: true },
];

export default createRouter({ history: createWebHistory("/portal"), routes });
