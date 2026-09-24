// The portal's file picker (templates/includes/one_drop.html): dropping onto
// the box, the names of what was chosen, and a button that says it is busy.
(function () {
	const size = (bytes) => {
		const units = ["B", "KB", "MB", "GB"];
		let at = 0;
		while (bytes >= 1024 && at < units.length - 1) (bytes /= 1024), at++;
		return `${at ? bytes.toFixed(1) : bytes} ${units[at]}`;
	};

	document.querySelectorAll(".one-drop").forEach((box) => {
		const input = box.querySelector("input[type=file]");
		const chosen = box.querySelector(".one-drop__chosen");
		const empty = box.querySelector(".one-drop__empty");
		const icon = box.querySelector(".one-drop__file-icon");
		const form = box.closest("form");
		const go = form && form.querySelector("[type=submit]");
		const show = () => {
			const files = Array.from(input.files || []);
			box.classList.toggle("is-chosen", files.length > 0);
			empty.hidden = files.length > 0;
			chosen.hidden = !files.length;
			chosen.innerHTML = "";
			files.forEach((one) => {
				const row = document.createElement("span");
				row.className = "one-drop__file";
				row.append(icon.content.cloneNode(true));
				const name = document.createElement("span");
				name.className = "one-drop__name";
				name.textContent = one.name;
				const weight = document.createElement("small");
				weight.textContent = size(one.size);
				row.append(name, weight);
				chosen.append(row);
			});
			if (go) go.disabled = !files.length;
		};
		input.addEventListener("change", show);
		["dragenter", "dragover"].forEach((kind) =>
			box.addEventListener(kind, (e) => {
				e.preventDefault();
				box.classList.add("is-over");
			})
		);
		["dragleave", "drop"].forEach((kind) => box.addEventListener(kind, () => box.classList.remove("is-over")));
		box.addEventListener("drop", (e) => {
			e.preventDefault();
			const dropped = Array.from(e.dataTransfer.files || []);
			if (!dropped.length) return;
			const kept = new DataTransfer();
			(input.multiple ? dropped : dropped.slice(0, 1)).forEach((one) => kept.items.add(one));
			input.files = kept.files;
			show();
		});
		if (form && go) {
			form.addEventListener("submit", () => {
				go.disabled = true;
				if (go.dataset.busy) go.textContent = go.dataset.busy;
			});
		}
		show();
	});
})();
