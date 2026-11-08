// A Markdown file as a page of its own, for a frame that runs nothing
// (CloudViewer): frappe's converter's HTML, with nothing fetched but pictures,
// in the ink and paper of the viewer around it, so it follows light and dark.
import { markdown } from "../kit";

export const markdownPage = (text, { ink = "CanvasText", paper = "Canvas", line = "GrayText" } = {}) =>
	`<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data: https: http:; style-src 'unsafe-inline'"><style>body{margin:0 auto;max-width:46rem;padding:2rem 1.5rem;font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:${ink};background:${paper}}a{color:inherit}img{max-width:100%}pre{white-space:pre-wrap}table{border-collapse:collapse}td,th{border:1px solid ${line};padding:4px 8px}</style></head><body>${markdown(text)}</body></html>`;
