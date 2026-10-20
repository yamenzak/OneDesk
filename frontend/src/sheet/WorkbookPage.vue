<!-- A workbook in the desk: Suite's editor, opened on the workbook the route names. Closing goes back to OneCloud. -->
<template>
	<div class="one-workbook">
		<SheetEditor v-if="name" :key="name" :id="name" :export-as="query.export || ''" @close="go('onecloud')" />
		<Dialogs />
	</div>
</template>

<script setup>
import { computed } from "vue";
import { Dialogs } from "frappe-ui";

import { go } from "../kit/desk";
import SheetEditor from "./components/SheetEditor/index.vue";
import "./shim/fit.css";

const props = defineProps({ route: { type: Array, default: () => [] }, query: { type: Object, default: () => ({}) } });
const name = computed(() => props.route[0]);
</script>
