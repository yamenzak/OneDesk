// The editor's own routes inside the island (Suite's routes.ts, cut to the editor
// and the slideshow). The desk's route names the presentation; the page sends the
// island's router there once it knows what the reader may do with it.
import { h } from "vue";

import { access } from "./router.js";

const Blank = { name: "SlideBlank", render: () => h("div") };

const presented = (route) => ({
	presentationId: route.params.presentationId,
	activeSlideId: Number.parseInt(route.query.slide, 10) || 1,
	editorAccess: access(),
});

export const routes = [
	{ path: "/", name: "slides-blank", component: Blank },
	{ path: "/home", name: "slides-home", component: Blank },
	{ path: "/new", name: "slides-editor-new", component: Blank },
	{
		path: "/presentation/:presentationId/:slug?",
		name: "slides-editor",
		component: () => import("../pages/PresentationEditor.vue"),
		props: presented,
	},
	{
		path: "/slideshow/:presentationId/:slug?",
		name: "slides-slideshow",
		component: () => import("../pages/Slideshow.vue"),
		props: presented,
	},
];
