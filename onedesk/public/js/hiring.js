// Recording an interview. OneAI's own verbs on the hiring walk — screen
// again, rank again, prepare again, transcribe again — are offered in the
// OneAI panel, not here; see one_hr/ai.py SUGGESTIONS.
frappe.provide("onedesk.hiring");

frappe.ui.form.on("Interview", {
	refresh(frm) {
		if (frm.is_new()) return;
		if ((frm.doc.__onload || {}).one_ai_record && frm.doc.docstatus < 2) {
			const busy = onedesk.hiring.recorder.on;
			frm.add_custom_button(busy ? __("Recording…") : __("Record"), () => {
				if (!onedesk.hiring.recorder.on) onedesk.hiring.recorder.ask(frm);
			}).toggleClass("disabled", !!busy);
		}
	},
});

// Recording an interview. The browser's own MediaRecorder, restarted every
// PART seconds so each part is a whole file that plays on its own: uploaded as
// soon as it closes, transcribed as soon as it lands, and a laptop that dies in
// minute forty loses one part rather than the interview. The next part starts
// before the last one stops, so nothing falls between them.
//
// It lives on `onedesk.hiring`, not on the form, so moving to another page
// does not stop it; only closing the tab does, and the tab says so first.
onedesk.hiring.recorder = {
	// hrms/hiring.py PART_SECONDS says the same.
	PART: 300,
	BITS: 24000,
	on: false,

	kind() {
		return ["audio/ogg;codecs=opus", "audio/webm;codecs=opus", "audio/mp4"].find((one) =>
			window.MediaRecorder?.isTypeSupported(one),
		);
	},

	ask(frm) {
		if (!navigator.mediaDevices?.getUserMedia || !this.kind()) {
			frappe.msgprint(__("This browser cannot record sound."));
			return;
		}
		const who = frm.doc.one_applicant || frm.doc.job_applicant;
		const dialog = new frappe.ui.Dialog({
			title: __("Record this interview"),
			fields: [
				{
					fieldname: "agreed",
					fieldtype: "Check",
					label: __("Candidate Consented to Recording"),
					description: __("Confirm that {0} agreed before you start.", [who]),
				},
				{
					fieldname: "call",
					fieldtype: "Check",
					label: __("Include Audio From Another Tab"),
					description: __("For video calls. The browser asks which tab to share."),
				},
			],
			primary_action_label: __("Start recording"),
			primary_action: (values) => {
				if (!values.agreed) {
					frappe.msgprint(__("Confirm the candidate's consent to start recording."));
					return;
				}
				dialog.hide();
				this.start(frm, !!values.call).catch((raised) => {
					this.stop_all();
					frappe.msgprint(__("Recording did not start: {0}", [raised.message || raised]));
				});
			},
		});
		dialog.show();
	},

	async start(frm, call) {
		const mic = await navigator.mediaDevices.getUserMedia({
			audio: { echoCancellation: true, noiseSuppression: true },
		});
		this.sources = [mic];
		let stream = mic;
		if (call) {
			// Chrome only shares a tab's sound alongside its picture; the
			// picture is never recorded.
			const tab = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
			this.sources.push(tab);
			if (tab.getAudioTracks().length) {
				this.mixer = new AudioContext();
				const into = this.mixer.createMediaStreamDestination();
				this.mixer.createMediaStreamSource(mic).connect(into);
				this.mixer.createMediaStreamSource(new MediaStream(tab.getAudioTracks())).connect(into);
				stream = into.stream;
			} else {
				frappe.show_alert({ message: __("That tab shared no sound, so only the microphone is recorded."), indicator: "orange" }, 8);
			}
		}

		this.recording = await frappe.xcall("onedesk.one_hr.hiring.start_recording", {
			interview: frm.doc.name,
			agreed: 1,
		});
		this.stream = stream;
		this.listen(stream);
		this.began = Date.now();
		this.uploads = [];
		this.on = true;
		this.bar();
		this.part();
		this.guard = (event) => {
			event.preventDefault();
			event.returnValue = "";
		};
		window.addEventListener("beforeunload", this.guard);
		frm.refresh();
	},

	// A level meter beside the time: the last couple of seconds of sound as
	// bars, so the interviewer can see the microphone hears the room — and a
	// line saying so when it has heard nothing for a while, which is a muted
	// or wrong microphone rather than a quiet candidate.
	BARS: 18,
	QUIET_SECONDS: 8,

	listen(stream) {
		this.ear = new AudioContext();
		const analyser = this.ear.createAnalyser();
		analyser.fftSize = 1024;
		this.ear.createMediaStreamSource(stream).connect(analyser);
		const samples = new Float32Array(analyser.fftSize);
		this.levels = new Array(this.BARS).fill(0);
		this.heard = Date.now();
		let last = 0;
		const tick = (now) => {
			if (!this.on) return;
			this.drawing = requestAnimationFrame(tick);
			if (now - last < 90) return;
			last = now;
			analyser.getFloatTimeDomainData(samples);
			const rms = Math.sqrt(samples.reduce((sum, one) => sum + one * one, 0) / samples.length);
			// Speech sits around 0.02–0.2 RMS; a square root spreads it over the bar.
			const level = Math.min(1, Math.sqrt(rms * 6));
			this.levels.push(level);
			this.levels.shift();
			if (rms > 0.01) this.heard = Date.now();
			this.quiet(Date.now() - this.heard > this.QUIET_SECONDS * 1000);
			this.draw();
		};
		this.drawing = requestAnimationFrame(tick);
	},

	draw() {
		const canvas = this.$bar?.find(".one-rec__wave")[0];
		if (!canvas) return;
		const ratio = window.devicePixelRatio || 1;
		const width = canvas.clientWidth;
		const height = canvas.clientHeight;
		if (canvas.width !== width * ratio) {
			canvas.width = width * ratio;
			canvas.height = height * ratio;
		}
		const pen = canvas.getContext("2d");
		pen.setTransform(ratio, 0, 0, ratio, 0, 0);
		pen.clearRect(0, 0, width, height);
		// The OneAI spectrum, read off the page's own tokens.
		const token = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
		const ramp = pen.createLinearGradient(0, 0, width, 0);
		ramp.addColorStop(0, token("--one-ai-1"));
		ramp.addColorStop(0.5, token("--one-ai-3"));
		ramp.addColorStop(1, token("--one-ai-6"));
		pen.fillStyle = ramp;
		const step = width / this.BARS;
		const thick = Math.max(2, step * 0.55);
		this.levels.forEach((level, at) => {
			const tall = Math.max(2, level * height);
			const x = at * step + (step - thick) / 2;
			pen.beginPath();
			pen.roundRect(x, (height - tall) / 2, thick, tall, thick / 2);
			pen.fill();
		});
	},

	quiet(silent) {
		if (!this.$bar || silent === this.silent) return;
		this.silent = silent;
		this.$bar.toggleClass("one-rec--quiet", silent);
		this.$bar
			.find(".one-rec__label")
			.text(silent ? __("No sound. Check the microphone.") : __("Recording"));
	},

	seconds() {
		return Math.round((Date.now() - this.began) / 1000);
	},

	part() {
		const kind = this.kind();
		const from = this.seconds();
		const chunks = [];
		const media = new MediaRecorder(this.stream, { mimeType: kind, audioBitsPerSecond: this.BITS });
		media.ondataavailable = (event) => event.data.size && chunks.push(event.data);
		media.onstop = () => {
			const blob = new Blob(chunks, { type: kind.split(";")[0] });
			this.uploads.push(this.upload(blob, from, this.seconds() - from));
		};
		media.start(1000);
		const before = this.media;
		this.media = media;
		if (before && before.state !== "inactive") before.stop();
		this.next = setTimeout(() => this.on && this.part(), this.PART * 1000);
	},

	// Sent through frappe.call rather than the uploader: there is no dialog
	// here and no person choosing a file, and the server files it and adds the
	// part in one step, so a part never exists without its sound.
	async upload(blob, from, seconds) {
		const ext = { "audio/ogg": "ogg", "audio/webm": "webm", "audio/mp4": "m4a" }[blob.type] || "webm";
		const data = await new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = () => resolve(String(reader.result).split(",")[1]);
			reader.onerror = reject;
			reader.readAsDataURL(blob);
		});
		await frappe.xcall("onedesk.one_hr.hiring.recorded_part", {
			recording: this.recording,
			file_name: `${this.recording}-${String(from).padStart(5, "0")}.${ext}`,
			data,
			starts_at: from,
			seconds,
		});
	},

	async stop() {
		if (!this.on) return;
		this.on = false;
		clearTimeout(this.next);
		clearInterval(this.ticking);
		const seconds = this.seconds();
		this.$bar?.find(".one-rec__time").text(__("Saving…"));
		const done = new Promise((resolve) => {
			this.media.addEventListener("stop", () => setTimeout(resolve, 0), { once: true });
		});
		this.media.stop();
		await done;
		const results = await Promise.allSettled(this.uploads);
		await frappe.xcall("onedesk.one_hr.hiring.stop_recording", { recording: this.recording, seconds });
		this.stop_all();
		const lost = results.filter((one) => one.status === "rejected").length;
		frappe.show_alert(
			{
				message: lost
					? __("Recording saved, but {0} part(s) did not upload.", [lost])
					: __("Recording saved. OneAI writes it down and remarks on it on the interview."),
				indicator: lost ? "orange" : "green",
			},
			10,
		);
		cur_frm?.doctype === "Interview" && cur_frm.reload_doc();
	},

	stop_all() {
		this.on = false;
		clearTimeout(this.next);
		clearInterval(this.ticking);
		(this.sources || []).forEach((stream) => stream.getTracks().forEach((track) => track.stop()));
		this.mixer?.close();
		this.mixer = null;
		cancelAnimationFrame(this.drawing);
		this.ear?.close();
		this.ear = null;
		this.silent = false;
		this.$bar?.remove();
		this.$bar = null;
		this.guard && window.removeEventListener("beforeunload", this.guard);
	},

	bar() {
		this.$bar = $(`
			<div class="one-rec" role="status">
				<span class="one-rec__dot"></span>
				<span class="one-rec__label"></span>
				<canvas class="one-rec__wave" aria-hidden="true"></canvas>
				<span class="one-rec__time">00:00</span>
				<button type="button" class="btn btn-xs btn-default one-rec__stop"></button>
			</div>
		`).appendTo(document.body);
		this.$bar.find(".one-rec__label").text(__("Recording"));
		this.$bar
			.find(".one-rec__stop")
			.text(__("Stop"))
			.on("click", () => this.stop());
		const pad = (n) => String(n).padStart(2, "0");
		this.ticking = setInterval(() => {
			const s = this.seconds();
			this.$bar?.find(".one-rec__time").text(`${pad(Math.floor(s / 60))}:${pad(s % 60)}`);
		}, 1000);
	},
};
