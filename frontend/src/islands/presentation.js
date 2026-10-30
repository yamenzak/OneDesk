import { screen } from "../kit";
import PresentationPage from "../slide/PresentationPage.vue";
import { routes } from "../slide/shim/routes.js";

export const mount = screen(PresentationPage, routes);
