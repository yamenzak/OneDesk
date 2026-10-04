// The kit every OneDesk island is built from (docs/ISLANDS.md). A part is
// here only when frappe-ui and @framework/ui have none: each is frappe-ui's
// components laid out with its tokens, so every screen in every app reads the
// same.
export * from "./desk";
export { screen } from "./mount";
export { default as Facts } from "./Facts.vue";
export { default as Figures } from "./Figures.vue";
export { default as Loading } from "./Loading.vue";
export { default as Page } from "./Page.vue";
export { default as Rows } from "./Rows.vue";
export { default as Section } from "./Section.vue";
export { default as Title } from "./Title.vue";
