<!-- Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/pages/Slideshow.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
	<div
		class="absolute left-0 top-0 h-full w-full overflow-clip bg-black"
		:class="{ 'slideshow-hide-cursor': cursorHidden }"
	>
		<!-- One: the audience's window fills its screen when asked (shim/presenter.js, VENDORED.md) -->
		<Button
			v-if="audience && !filling"
			variant="solid"
			class="absolute end-4 top-4 z-10"
			:label="__('Fill the Screen')"
			@click.stop="fillScreen"
		/>
		<div
			class="flex h-screen w-full items-center justify-center"
			:style="slideContainerStyles"
		>
			<div
				v-if="showSlideshowEndScreen"
				class="flex h-full w-full items-center justify-center bg-black"
				@click="endSlideShow()"
			>
				<SlideshowEndScreen @restartSlideShow="changeSlideInSlideshow(0)" />
			</div>

			<div
				v-else-if="isMagicMoveApplied"
				:style="slideStyles"
				@click="changeSlideInSlideshow(slideIndex + 1)"
			>
				<FadeElementTransition
					:duration="parseFloat(prevSlide?.transitionDuration)"
					:skip="!prevSlide?.fadeUnmatchedElements"
				>
					<SlideElement
						v-for="element in shownElements"
						:key="`slideshow-${getElementKey(element)}`"
						mode="slideshow"
						:element="element"
						:data-index="element.id"
						:transitionStyles="transitionStyles"
						:style="getElementTransitionStyles(element)"
						class="forward-transition"
					/>
				</FadeElementTransition>
			</div>

			<div v-else>
				<Transition
					@before-enter="beforeSlideEnter"
					@enter="slideEnter"
					@before-leave="beforeSlideLeave"
					@leave="slideLeave"
				>
					<div
						:key="slideIndex"
						:style="slideStyles"
						@click="changeSlideInSlideshow(slideIndex + 1)"
					>
						<SlideElement
							v-for="element in shownElements"
							:key="`slideshow-${getElementKey(element)}`"
							mode="slideshow"
							:element="element"
							:data-index="element.id"
						/>
					</div>
				</Transition>
			</div>
		</div>
	</div>
</template>

<script setup>
import { audience, link, say, unlink } from '@/apps/slides/shim/presenter.js' // One: the presenter view, VENDORED.md
import { frame, frameSize } from '@/apps/slides/shim/frame.js' // One: the frame is one setting, a screen's may stand on its side (VENDORED.md)
import { __ } from '@/apps/slides/shim/words.js' // One: Suite's words through the desk's translations, VENDORED.md
import { computed, onActivated, onDeactivated, ref, watch, provide } from 'vue'
import { Button, toast, useKeyboardShortcut, usePageMeta } from 'frappe-ui'
import { appPageMeta } from '@/utils/documentTitle'

import SlideElement from '@/apps/slides/components/SlideElement.vue'
import SlideshowEndScreen from '@/apps/slides/components/SlideshowEndScreen.vue'
import FadeElementTransition from '@/apps/slides/components/FadeElementTransition.vue'
import { useBrowserZoomGuard } from '@/apps/slides/composables/useBrowserZoomGuard'

import {
	inSlideShowMode,
	showSlideshowEndScreen,
	requestFullscreen,
	exitFullscreen,
	requestWakeLock,
	releaseWakeLock,
	releaseVideoWarmers,
	resetSlideShowState,
	endSlideShow,
	prefetchNextSlide,
	changeSlideInSlideshow,
	performNextStep,
	performPreviousStep,
	scheduleAdvance,
	cancelAdvance,
	prevSlide,
	isMagicMoveApplied,
} from '@/apps/slides/stores/slideshow'

import {
	applyReverseTransition,
	initPresentationDoc,
	inReadonlyMode,
	pageTitle,
} from '@/apps/slides/stores/presentation'
import { currentSlide, setSlideIndex, slideIndex, slides } from '@/apps/slides/stores/slide'
import { underneath } from '@/apps/slides/shim/master.js' // One: the master, VENDORED.md
import { resetFocus } from '@/apps/slides/stores/element'
import { getTransitionKey } from '@/apps/slides/stores/transition'

// One: the master underneath the slide's own (shim/master.js, VENDORED.md)
const shownElements = computed(() => [...underneath(currentSlide.value, slideIndex.value), ...(currentSlide.value?.elements || [])])

const props = defineProps({
	presentationId: {
		type: String,
		required: true,
	},
	activeSlideId: {
		type: Number,
		required: true,
	},
})

const transition = ref('none')
const transform = ref('')
const opacity = ref(1)
const windowWidth = ref(window.innerWidth)
const windowHeight = ref(window.innerHeight)

const clipPath = computed(() => {
	if (!inSlideShowMode.value) return 'none'
	// One: a slide of any size fits both ways, so it may leave room at the sides too (VENDORED.md)
	const scale = fitScale()
	const across = Math.max(0, (windowWidth.value - frame.w * scale) / 2)
	const down = Math.max(0, (windowHeight.value - frame.h * scale) / 2)
	return `inset(${down}px ${across}px ${down}px ${across}px)`
})

const fitScale = () => Math.min(windowWidth.value / frame.w, windowHeight.value / frame.h)

const getElementKey = (element) => getTransitionKey(element)

const cursorHidden = ref(true)

const slideStyles = computed(() => {
	// One: as large as fits the screen both ways, at the presentation's own shape (VENDORED.md)
	const widthScale = fitScale()

	const baseStyles = {
		...frameSize(),
		overflow: 'hidden',
		background: currentSlide.value?.background || '#ffffff', // One: a fade is a background too, VENDORED.md
	}

	if (prevSlide.value?.transition == 'Magic Move') {
		return {
			...baseStyles,
			transform: `scale(${widthScale})`,
			opacity: 1,
			...transitionStyles.value,
		}
	}

	return {
		...baseStyles,
		transform: `${transform.value} scale(${widthScale})`,
		opacity: opacity.value,
		transition: transition.value,
	}
})

const getElementTransitionStyles = (element) => {
	const styles = transitionStyles.value

	// limit transition property in element container to dimensions and position only
	const transitionProperty = styles.transitionProperty == 'all' ? 'left, top, width, height' : ''

	return {
		...styles,
		transitionProperty: transitionProperty,
		'--transition-duration': styles.transitionDuration,
	}
}

const transitionStyles = computed(() => {
	if (applyReverseTransition.value) return {}

	const transitionProperty = prevSlide.value?.transition == 'Magic Move' ? 'all' : ''
	const transitionDuration = prevSlide.value?.transitionDuration

	return {
		transitionProperty: transitionProperty,
		transitionDuration: transitionDuration ? `${transitionDuration}s` : '0s',
		transitionTimingFunction: 'ease-in-out',
	}
})

const transitionMap = computed(() => {
	if (!currentSlide.value) return {}
	return {
		'Slide In': {
			beforeEnter: {
				transform: ['translateX(100%)', 'translateX(-100%)'],
				transition: 'none',
			},
			enter: {
				transform: 'translateX(0)',
				transition: `transform ${currentSlide.value.transitionDuration}s ease-out`,
			},
			beforeLeave: {
				transition: 'none',
			},
			leave: {
				transform: ['translateX(100%)', 'translateX(-100%)'],
				transition: `transform ${currentSlide.value.transitionDuration}s ease-out`,
			},
		},
		Fade: {
			beforeEnter: {
				opacity: 0,
			},
			enter: {
				transition: `opacity ${currentSlide.value.transitionDuration}s`,
			},
			beforeLeave: {},
			leave: {
				transition: `opacity ${currentSlide.value.transitionDuration}s`,
				opacity: 0,
			},
		},
	}
})

const applyTransitionStyles = (hook) => {
	const styles = transitionMap.value?.[currentSlide.value.transition]?.[hook]
	if (!styles) return

	let transformVal = styles.transform
	if (transformVal && Array.isArray(transformVal)) {
		transformVal = applyReverseTransition.value ? transformVal[1] : transformVal[0]
	}

	transform.value = transformVal || transform.value
	transition.value = styles.transition || transition.value
	opacity.value = styles.opacity
}

const beforeSlideEnter = (el) => {
	if (!currentSlide.value.transition) return
	applyTransitionStyles('beforeEnter')
}

const slideEnter = (el, done) => {
	if (!currentSlide.value.transition) return done()
	el.offsetWidth
	applyTransitionStyles('enter')
	done()
}

const beforeSlideLeave = (el) => {
	if (!currentSlide.value.transition) return
	applyTransitionStyles('beforeLeave')
}

const slideLeave = (el, done) => {
	if (!currentSlide.value.transition) return done()
	applyTransitionStyles('leave')
	done()
}

const CURSOR_IDLE_DELAY = 3000
let cursorTimer = null

const resetCursorVisibility = () => {
	cursorHidden.value = false
	clearTimeout(cursorTimer)
	cursorTimer = setTimeout(() => {
		cursorHidden.value = true
	}, CURSOR_IDLE_DELAY)
}

const stopCursorTracking = () => {
	clearTimeout(cursorTimer)
	document.removeEventListener('mousemove', resetCursorVisibility)
	cursorHidden.value = true
}

const handleFullScreenChange = () => {
	filling.value = Boolean(document.fullscreenElement)
	if (document.fullscreenElement) {
		inSlideShowMode.value = true
		requestWakeLock()
	} else {
		stopCursorTracking()
		// One: the audience's window plays on whether it fills the screen or not (shim/presenter.js, VENDORED.md)
		if (inSlideShowMode.value && !audience.value) endSlideShow()
	}
}

// One: whether the audience's window fills its screen, and the button that makes it
const filling = ref(false)
const fillScreen = () => requestFullscreen()

// the lock is dropped when the tab is hidden
const handleVisibilityChange = () => {
	if (document.visibilityState === 'visible' && inSlideShowMode.value) requestWakeLock()
}

const slideContainerStyles = computed(() => {
	return {
		clipPath: clipPath.value,
		background: currentSlide.value?.background || '#ffffff', // One: a fade is a background too, VENDORED.md
	}
})

let active = false

const initFullscreenMode = async () => {
	// One: the audience's window opens without a click to fill the screen with, so it starts in the window (shim/presenter.js, VENDORED.md)
	if (audience.value) {
		inSlideShowMode.value = true
		requestWakeLock()
		return
	}
	// fullscreen is requested on the click that starts the slideshow, so the
	// change event fires before this component is around to hear it
	const inFullscreen = Boolean(document.fullscreenElement) || (await requestFullscreen())
	if (!active) return exitFullscreen()
	if (!inFullscreen) {
		toast.error(__('Could not enter fullscreen mode'))
		endSlideShow()
		return
	}

	handleFullScreenChange()
}

const loadPresentation = async () => {
	if (slides.value.length) return
	// the slide asked for was picked before there were any to pick from
	if (await initPresentationDoc(props.presentationId)) setSlideIndex(props.activeSlideId)
}

const updateWindowSize = () => {
	windowWidth.value = window.innerWidth
	windowHeight.value = window.innerHeight
}

usePageMeta(() => appPageMeta(pageTitle(), 'Slides'))
useBrowserZoomGuard()

// One: the audience's window tells the presenter view where it is, and goes where it is told (shim/presenter.js, VENDORED.md)
const tellPresenter = () => say({ at: slideIndex.value, of: slides.value.length })
watch(slideIndex, () => audience.value && tellPresenter())

onActivated(() => {
	if (audience.value) {
		link(props.presentationId, (heard) => {
			if (heard.go != null) changeSlideInSlideshow(heard.go)
			if (heard.hello) tellPresenter()
			if (heard.end) endSlideShow()
		})
		tellPresenter()
	}
	active = true
	document.title = pageTitle()
	resetFocus()
	loadPresentation()
	initFullscreenMode()
	document.addEventListener('fullscreenchange', handleFullScreenChange)
	document.addEventListener('visibilitychange', handleVisibilityChange)
	document.addEventListener('mousemove', resetCursorVisibility)
	window.addEventListener('resize', updateWindowSize)

	// Initial prefetch of next slide
	setTimeout(() => {
		prefetchNextSlide()
	}, 500)
})

onDeactivated(() => {
	unlink() // One
	active = false
	document.removeEventListener('fullscreenchange', handleFullScreenChange)
	document.removeEventListener('visibilitychange', handleVisibilityChange)
	window.removeEventListener('resize', updateWindowSize)
	cancelAdvance()
	stopCursorTracking()
	releaseWakeLock()
	releaseVideoWarmers()

	// leaving by any route other than endSlideShow would strand the editor in fullscreen
	resetSlideShowState()
	exitFullscreen()
})

watch(
	() => props.activeSlideId,
	(index) => {
		setSlideIndex(index)
		// Prefetch next slide when current slide changes
		setTimeout(() => {
			prefetchNextSlide()
		}, 200)
	},
	{ immediate: true },
)

// any change of slide, by hand, by the timer, or by the load, restarts the wait
// the slide the show opens on, or loads into, waits only its delay
watch([currentSlide, inSlideShowMode], ([, presenting], [previous, wasPresenting]) => {
	if (presenting) scheduleAdvance(wasPresenting && Boolean(previous))
	else cancelAdvance()
})

provide('inReadonlyMode', inReadonlyMode)
provide('inSlideShowMode', inSlideShowMode)

useKeyboardShortcut([
	{ combo: 'ArrowRight', description: __('Next step'), group: __('Slideshow'), handler: performNextStep },
	{ combo: 'ArrowDown', description: __('Next step'), group: __('Slideshow'), handler: performNextStep },
	{ combo: 'Space', description: __('Next step'), group: __('Slideshow'), handler: performNextStep },
	{ combo: 'PageDown', description: __('Next step'), group: __('Slideshow'), handler: performNextStep },
	{ combo: 'ArrowLeft', description: __('Previous step'), group: __('Slideshow'), handler: performPreviousStep },
	{ combo: 'ArrowUp', description: __('Previous step'), group: __('Slideshow'), handler: performPreviousStep },
	{ combo: 'PageUp', description: __('Previous step'), group: __('Slideshow'), handler: performPreviousStep },
	{ combo: 'F5', description: __('Restart'), group: __('Slideshow'), handler: () => changeSlideInSlideshow(0) },
])
</script>

<style>
/* has to beat the cursor elements set on themselves */
.slideshow-hide-cursor,
.slideshow-hide-cursor * {
	cursor: none !important;
}

.forward-transition .textElement span,
.forward-transition .textElement li {
	transition-property: all;
	transition-duration: var(--transition-duration);
	transition-timing-function: ease-in-out;
}

/* the marker inherits the rest from its item, only its fade is its own */
.forward-transition .textElement li > p:first-child::before {
	transition-property: opacity;
	transition-duration: var(--transition-duration);
	transition-timing-function: ease-in-out;
}
</style>
