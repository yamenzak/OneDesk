<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/components/LockBadge.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<Tooltip text="Unlock" :hover-delay="700">
		<div
			:style="[styles.handle, { pointerEvents: 'auto' }]"
			class="flex cursor-pointer items-center justify-center"
			:aria-label="__('Unlock')"
			@mousedown.stop
			@click="toggleLock()"
		>
			<div :style="styles.stem"></div>
			<LucideLockOpen
				class="stroke-[1.5]"
				:style="[styles.icon, { transform: `rotate(${-rotation}deg)` }]"
			/>
		</div>
	</Tooltip>
</template>
<script setup>
import { computed } from 'vue'
import { Tooltip } from 'frappe-ui'

import { slideBounds } from '@/apps/slides/stores/slide'
import { toggleLock } from '@/apps/slides/stores/element'
import { lockColor, getStemHandleStyles } from '@/apps/slides/utils/constants'

defineProps({
	rotation: {
		type: Number,
		default: 0,
	},
})

const styles = computed(() => getStemHandleStyles(slideBounds.scale, lockColor))
</script>
