// What OneCloud's parts share (one_storage/api.py): what a kind of file is
// called and drawn as, where a node is, and what may be dropped where.
import { __, date, fileSize } from "../kit";

export const API = "onedesk.one_storage.api.";
export const UPLOAD = "onedesk.one_storage.upload.";
export const contentUrl = (node) => `/api/method/${API}content?node=${encodeURIComponent(node)}`;

// A folder's colour (one_storage/api.py color), its ink written out whole so
// the stylesheet is built with it.
export const COLORS = [
	{ value: "red", label: () => __("Red"), ink: "text-ink-red-7" },
	{ value: "amber", label: () => __("Amber"), ink: "text-ink-amber-7" },
	{ value: "green", label: () => __("Green"), ink: "text-ink-green-7" },
	{ value: "cyan", label: () => __("Cyan"), ink: "text-ink-cyan-7" },
	{ value: "blue", label: () => __("Blue"), ink: "text-ink-blue-7" },
	{ value: "violet", label: () => __("Violet"), ink: "text-ink-violet-7" },
	{ value: "pink", label: () => __("Pink"), ink: "text-ink-pink-7" },
];

export const inkOf = (item) => COLORS.find((one) => one.value === item.color)?.ink || "text-ink-gray-6";

const KINDS = [
	[["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "heic", "avif", "ico"], "lucide-file-image", () => __("Image")],
	[["pdf"], "lucide-file-text", () => __("PDF document")],
	[["doc", "docx", "odt", "rtf"], "lucide-file-text", () => __("Document")],
	[["txt", "md"], "lucide-file-text", () => __("Text document")],
	[["xls", "xlsx", "ods", "csv", "tsv"], "lucide-file-spreadsheet", () => __("Spreadsheet")],
	[["ppt", "pptx", "odp", "key"], "lucide-presentation", () => __("Presentation")],
	[["mp4", "mov", "webm", "mkv", "avi", "m4v"], "lucide-file-play", () => __("Video")],
	[["mp3", "wav", "ogg", "m4a", "flac", "aac"], "lucide-file-music", () => __("Audio")],
	[["zip", "rar", "7z", "tar", "gz", "tgz"], "lucide-file-archive", () => __("Compressed folder")],
	[["js", "ts", "py", "json", "html", "css", "xml", "sh", "yml", "yaml", "sql"], "lucide-file-code", () => __("Code")],
];

export const SHEETS = ["xlsx", "xlsm", "xls", "csv"];
export const PDF_PARTS = ["pdf", "png", "jpg", "jpeg", "webp", "gif", "bmp", "tif", "tiff"];
export const PREVIEW = {
	image: ["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "avif", "ico"],
	frame: ["pdf", "txt", "md", "csv", "tsv", "json", "xml", "html", "css", "js", "py", "yml", "yaml", "sql", "sh"],
	video: ["mp4", "webm", "mov", "m4v", "mkv", "ogv"],
	audio: ["mp3", "wav", "ogg", "oga", "opus", "m4a", "flac", "aac", "weba"],
};

// What the viewer shows a file as (CloudViewer), by its extension.
const READS = {
	pdf: ["pdf"],
	markdown: ["md", "markdown"],
	text: ["txt", "log", "csv", "tsv", "json", "xml", "html", "htm", "css", "js", "ts", "py", "yml", "yaml", "sql", "sh", "ini", "toml", "conf", "env", "vue", "rb", "go", "java", "c", "h", "cpp", "rs", "php"],
};

export function viewedAs(item) {
	if (!item || item.folder || !item.url) return null;
	const ext = extension(item);
	if (PREVIEW.image.includes(ext)) return "image";
	if (PREVIEW.video.includes(ext)) return "video";
	if (PREVIEW.audio.includes(ext)) return "audio";
	return Object.keys(READS).find((kind) => READS[kind].includes(ext)) || null;
}

// The icons a node names for itself (one_storage/namespace.py), written out
// whole so the build keeps each one.
const NAMED = {
	"folder-heart": "lucide-folder-heart",
	"clock": "lucide-clock",
	"star": "lucide-star",
	"users": "lucide-users",
	"library-big": "lucide-library-big",
	"building-2": "lucide-building-2",
	"database": "lucide-database",
	"mail": "lucide-mail",
	"network": "lucide-network",
	"inbox": "lucide-inbox",
	"trash-2": "lucide-trash-2",
	"image": "lucide-image",
	"folder-kanban": "lucide-folder-kanban",
	"list-checks": "lucide-list-checks",
	"square-check": "lucide-square-check",
	"server": "lucide-server",
	"folder-open": "lucide-folder-open",
};

export function extension(item) {
	const name = item.name || "";
	const dot = name.lastIndexOf(".");
	return dot > 0 ? name.slice(dot + 1).toLowerCase() : "";
}

export function iconOf(item) {
	if (item.icon && NAMED[item.icon]) return NAMED[item.icon];
	if (item.workbook) return "lucide-file-spreadsheet";
	if (item.document) return "lucide-file-text";
	if (item.folder) return item.record ? "lucide-folder-open" : "lucide-folder";
	const found = KINDS.find(([exts]) => exts.includes(extension(item)));
	return found ? found[1] : "lucide-file";
}

export function typeOf(item) {
	if (item.virtual && item.doctype) return __("Record type");
	if (item.record && item.folder) return __("Record");
	if (String(item.id).startsWith("@request/")) return __("File request");
	if (item.folder) return __("Folder");
	if (item.workbook) return __("Workbook");
	if (item.document) return __("Document");
	if (item.presentation) return __("Presentation");
	const ext = extension(item);
	const found = KINDS.find(([exts]) => exts.includes(ext));
	if (found) return found[2]();
	return ext ? __("{0} file", [ext.toUpperCase()]) : __("File");
}

export const sizeText = (bytes) => fileSize(bytes);

export function dateText(value) {
	if (!value) return "";
	const [day, time] = String(value).split(" ");
	return `${date(day)} ${(time || "").slice(0, 5)}`.trim();
}

export const count = (n, one, many) => (n === 1 ? one : many.replace("{0}", n));

// What kind of place a node is: a folder, or one of the places that only
// list (the bin, what is shared, records, libraries, servers, requests).
export function kindOf(node = "") {
	if (node === "@bin") return "bin";
	if (node === "@shared") return "shared";
	if (node === "@root") return "root";
	if (node.startsWith("@records")) return node.split("/").length === 3 ? "record" : "records";
	if (node === "@libraries") return "libraries";
	if (node === "@recent") return "recent";
	if (node === "@starred") return "starred";
	if (node === "@mounts") return "network";
	if (node === "@requests") return "requests";
	if (node.startsWith("@request/")) return "request";
	if (node.startsWith("@mount/")) return "mount";
	return "folder";
}

export function emptyText(kind, searching) {
	if (searching) return __("No results");
	const text = {
		bin: __("No deleted items"),
		shared: __("Nothing shared with you"),
		records: __("No records with files"),
		recent: __("No recent files"),
		network: __("No server connections"),
		requests: __("No file requests"),
		request: __("No files yet"),
		starred: __("No starred items"),
		libraries: __("No libraries"),
		root: "",
	}[kind];
	return text !== undefined ? text : __("This folder is empty");
}

// Where things may be dropped: a folder, never a place that only lists.
export function takes(id) {
	if (["@root", "@shared", "@bin", "@records", "@libraries", "@mounts", "@requests"].includes(id)) return false;
	if (id.startsWith("@request/")) return false;
	if (id.startsWith("@records/") && id.split("/").length !== 3) return false;
	return true;
}

// A server is its own place: moving across servers, or onto a record,
// copies.
export function across(from, to) {
	const server = (id) => (id.startsWith("@mount/") ? id.split("/")[1] : null);
	return server(to) !== server(from);
}

export const stored = (item) => !!item && !item.virtual;
export const filed = (item) => stored(item) && !item.remote;
