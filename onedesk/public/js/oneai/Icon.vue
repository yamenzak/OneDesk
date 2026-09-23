<!-- An icon from the desk's own sprite: Lucide, plus every Custom Icon.

     `frappe.utils.icon` draws a `<use>` into the sprite the desk already
     loaded, so an icon is a name and nothing else. One the sprite lacks is a
     Custom Icon fixture in fixtures/custom_icon.json, never a path typed here;
     tests/test_borrowing.py refuses both an inline svg element and a name that
     resolves to nothing. -->
<template>
	<span class="one-ai-glyph" aria-hidden="true" v-html="drawn"></span>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	name: { type: String, required: true },
	// frappe's own sizes: xs 12, sm 16, md 20.
	size: { type: String, default: "sm" },
});

const drawn = computed(() => frappe.utils.icon(props.name, props.size, "", "", "", true));
</script>
