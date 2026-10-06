// Whether the project page shows only the project's own work, its Main, and
// not what is under it (one_project/tree.py `narrow`). The page provides it;
// each view sends it with what it reads.
import { computed, inject, provide } from "vue";

const KEY = Symbol("only");

export const provideOnly = (only) => provide(KEY, only);
export const useOnly = () => inject(KEY, computed(() => false));
// What a view adds to its call: the server reads it as a check.
export const onlyArg = (only) => (only.value ? { only: 1 } : {});
