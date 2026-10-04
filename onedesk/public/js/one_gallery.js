// The photos and videos on a customer's project page (www/projects.html),
// the cover first, then each in turn: a photo for a few seconds, a video
// muted to its end. The arrows and the small photos turn it by hand, and
// holding the pointer over it pauses it. Someone who asked their system for
// less motion turns the photos themselves.
(() => {
	const PHOTO = 6000;
	const still = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

	document.querySelectorAll("[data-one-gallery]").forEach((root) => {
		const slides = [...root.querySelectorAll(".one-gallery__slide")];
		const thumbs = [...root.querySelectorAll(".one-gallery__thumb")];
		const bars = [...root.querySelectorAll(".one-gallery__bars > span > span")];
		const count = root.querySelector(".one-gallery__count");
		const video = (i) => slides[i].querySelector("video");
		let at = 0;
		let shown = 0;
		let held = false;
		let last = null;

		const paint = () =>
			bars.forEach((bar, k) => {
				bar.style.width = `${k < at ? 100 : k === at ? Math.round(shown * 100) : 0}%`;
			});

		function go(i) {
			at = (i + slides.length) % slides.length;
			shown = 0;
			slides.forEach((one, k) => one.classList.toggle("is-on", k === at));
			thumbs.forEach((one, k) => {
				one.classList.toggle("is-on", k === at);
				one.setAttribute("aria-current", k === at ? "true" : "false");
			});
			if (count) count.textContent = `${at + 1} / ${slides.length}`;
			slides.forEach((one, k) => {
				const clip = video(k);
				if (!clip) return;
				if (k === at) {
					clip.currentTime = 0;
					clip.play().catch(() => {});
				} else clip.pause();
			});
			paint();
		}

		slides.forEach((one, k) => {
			const clip = video(k);
			if (!clip) return;
			clip.addEventListener("timeupdate", () => {
				if (k !== at || !clip.duration) return;
				shown = clip.currentTime / clip.duration;
				paint();
			});
			clip.addEventListener("ended", () => k === at && slides.length > 1 && go(at + 1));
		});
		root.querySelector("[data-back]")?.addEventListener("click", () => go(at - 1));
		root.querySelector("[data-on]")?.addEventListener("click", () => go(at + 1));
		thumbs.forEach((one, k) => one.addEventListener("click", () => go(k)));
		root.addEventListener("mouseenter", () => {
			held = true;
			if (slides.length > 1) video(at)?.pause();
		});
		root.addEventListener("mouseleave", () => {
			held = false;
			video(at)?.play().catch(() => {});
		});

		function tick(now) {
			if (last !== null && !held && !still && slides.length > 1 && !video(at)) {
				shown += (now - last) / PHOTO;
				if (shown >= 1) go(at + 1);
				else paint();
			}
			last = now;
			requestAnimationFrame(tick);
		}
		go(0);
		requestAnimationFrame(tick);
	});
})();
