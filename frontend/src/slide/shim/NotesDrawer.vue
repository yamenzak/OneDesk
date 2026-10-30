<!-- A slide's speaker notes, under the slide: what the presenter says over it.
     Shown in the presenter view and on a PDF with notes, never to the audience. -->
<template>
	<div
		class="absolute bottom-0 start-56 end-72 z-10 flex flex-col border-t border-outline-gray-1 bg-surface-elevation-1 max-md:hidden"
		:style="{ height: `${notesOpen ? NOTES_HEIGHT : NOTES_BAR}px` }"
		@click.stop
		@mousedown.stop
	>
		<button
			type="button"
			class="flex h-9 shrink-0 items-center gap-1.5 px-4 text-start text-sm text-ink-gray-6 hover:text-ink-gray-8"
			:aria-expanded="notesOpen"
			@click="notesOpen = !notesOpen"
		>
			<span class="lucide-chevron-up size-3.5 transition-transform" :class="notesOpen ? 'rotate-180' : ''" aria-hidden="true" />
			<span>{{ __("Speaker Notes") }}</span>
			<span v-if="!notesOpen && currentSlide?.notes" class="truncate text-ink-gray-5">· {{ currentSlide.notes }}</span>
		</button>
		<textarea
			v-if="notesOpen"
			:value="currentSlide?.notes || ''"
			:readonly="inReadonlyMode"
			:placeholder="__('What you will say over this slide')"
			dir="auto"
			class="min-h-0 flex-1 resize-none border-0 bg-transparent px-4 pb-3 pt-0 text-base text-ink-gray-8 placeholder:text-ink-gray-4 focus:ring-0"
			@focus="() => notes.begin()"
			@input="(e) => notes.set(e.target.value)"
			@blur="() => notes.commit()"
			@keydown.stop
		/>
	</div>
</template>

<script setup>

import { useSlideProperty } from "../composables/editProperty";
import { inReadonlyMode } from "../stores/presentation";
import { currentSlide } from "../stores/slide";
import { NOTES_BAR, NOTES_HEIGHT, notesOpen } from "./notes.js";
import { __ } from "./words.js";

const notes = useSlideProperty("notes");
</script>
