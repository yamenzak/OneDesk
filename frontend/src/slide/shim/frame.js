// The frame a slide is drawn on, in the editor's own units. A presentation's is
// Suite's 960 by 540; a screen standing on its side is 540 by 960 (stage 7 of
// docs/ONESLIDE.md). Set it before the editor mounts.
import { reactive } from "vue";

export const WIDE = { w: 960, h: 540 };
export const TALL = { w: 540, h: 960 };
export const frame = reactive({ ...WIDE });

export function setFrame(portrait) {
	Object.assign(frame, portrait ? TALL : WIDE);
}

export const frameSize = () => ({ width: `${frame.w}px`, height: `${frame.h}px` });
