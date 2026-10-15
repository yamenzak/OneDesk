// Whether the portal is on a phone: frappe-ui's two shells are two
// navigation models, and the app picks one by the window's width.
import { ref } from "vue";

const narrow = matchMedia("(max-width: 767px)");
export const phone = ref(narrow.matches);
narrow.addEventListener("change", () => (phone.value = narrow.matches));
