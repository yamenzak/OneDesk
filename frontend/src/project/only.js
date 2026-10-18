import { computed, inject, provide } from "vue";

const KEY = Symbol("only");

export const provideOnly = (only) => provide(KEY, only);
export const useOnly = () => inject(KEY, computed(() => false));
export const onlyArg = (only) => (only.value ? { only: 1 } : {});
