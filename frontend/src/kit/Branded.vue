<template>
  <template v-for="(part, i) in parts" :key="i">
    <span v-if="part.one" class="one-name one-solo inline-flex items-baseline gap-1 whitespace-nowrap"><svg v-if="mark" class="one-mark inline-block size-[1.05em] shrink-0 self-center" :viewBox="mark.viewBox" aria-hidden="true" v-html="mark.html" /><span class="font-light">{{ NAME }}</span></span>
    <span v-else-if="part.named" class="one-name inline-flex items-baseline gap-1 whitespace-nowrap"><svg v-if="part.mark" class="one-mark inline-block size-[1.05em] shrink-0 self-center" :viewBox="part.mark.viewBox" aria-hidden="true" v-html="part.mark.html" /><span><span class="font-light">{{ NAME }}</span>{{ part.named }}</span></span>
    <template v-else>{{ part }}</template>
  </template>
</template>

<script setup>
import { computed } from "vue";
import { onedesk, symbol } from "./desk";

const props = defineProps({ text: { type: [String, Number], default: "" } });
const NAME = "One";
const mark = symbol("one");
// The desk draws a product's name, "OneCloud", with One light and, in a
// sentence, its mark before it, and a lone "One" with One's mark
// (public/js/brand.js); an island, which the desk's observer leaves alone,
// draws both here the same way.
const parts = computed(() => {
  const text = props.text === null || props.text === undefined ? "" : String(props.text);
  const brand = onedesk()?.brand;
  if (!brand?.parts) return [text];
  const out = [];
  let at = 0;
  for (const found of text.matchAll(new RegExp(brand.NAME.source, "g"))) {
    if (found.index > at) out.push(...brand.parts(text.slice(at, found.index)));
    const id = text.trim() !== found[0] && brand.mark_of?.(found[1]);
    out.push({ named: found[1], mark: id ? symbol(id) : null });
    at = found.index + found[0].length;
  }
  if (at < text.length) out.push(...brand.parts(text.slice(at)));
  return out;
});
</script>
