// The lucide icons a block, a starter or a step names, written out whole so
// frappe-ui's icon classes are built for them; a name not here draws a square.
const ICONS = {
	bell: "lucide-bell",
	bot: "lucide-bot",
	file: "lucide-file",
	"file-plus": "lucide-file-plus",
	"file-user": "lucide-file-user",
	"folder-input": "lucide-folder-input",
	forward: "lucide-forward",
	inbox: "lucide-inbox",
	"life-buoy": "lucide-life-buoy",
	link: "lucide-link",
	"list-checks": "lucide-list-checks",
	"mail-check": "lucide-mail-check",
	"mail-open": "lucide-mail-open",
	moon: "lucide-moon",
	newspaper: "lucide-newspaper",
	octagon: "lucide-octagon",
	oneai: "lucide-sparkles",
	paperclip: "lucide-paperclip",
	"pen-line": "lucide-pen-line",
	receipt: "lucide-receipt",
	reply: "lucide-reply",
	"shield-alert": "lucide-shield-alert",
	siren: "lucide-siren",
	split: "lucide-split",
	star: "lucide-star",
	"user-check": "lucide-user-check",
	"user-plus": "lucide-user-plus",
	users: "lucide-users",
};

export const lucide = (name) => ICONS[name] || "lucide-square";
