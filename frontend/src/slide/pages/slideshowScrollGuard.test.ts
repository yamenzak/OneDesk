// Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/pages/slideshowScrollGuard.test.ts. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
import { describe, expect, it } from 'vitest'

import source from './Slideshow.vue?raw'

describe('slideshow root overflow', () => {
	// elements past the slide edge would otherwise grow the document and show scrollbars
	it('clips the slideshow root', () => {
		const rootClass = source.match(/<template>[\s\S]*?<div\s+class="([^"]*)"/)?.[1]

		expect(rootClass).toContain('overflow-clip')
	})
})

describe('slideshow browser zoom', () => {
	it('installs the browser zoom guard', () => {
		expect(source).toContain('useBrowserZoomGuard()')
	})
})
