<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/controls/PropertyRow.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<div class="flex h-7 w-full items-center justify-between">
		<span :class="labelClasses">{{ label }}</span>
		<slot />
	</div>
</template>

<script setup>
import { labelClasses } from '@/apps/slides/utils/constants'

defineProps({ label: String })
</script>
