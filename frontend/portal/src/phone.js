import { ref } from "vue";

const narrow = matchMedia("(max-width: 767px)");
export const phone = ref(narrow.matches);
narrow.addEventListener("change", () => (phone.value = narrow.matches));
