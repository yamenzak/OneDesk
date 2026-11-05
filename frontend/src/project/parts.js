import { computed, inject, provide } from "vue";

const PARTS = Symbol("parts");

export const provideParts = (parts) => provide(PARTS, parts);
export const useParts = () => inject(PARTS, computed(() => null));
