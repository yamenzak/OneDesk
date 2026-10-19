"""The old Rua app, read and never written.

Two places it can be read from: the live site, by URL and an API key that
can only read (`rua_source` in site_config: url, key, secret), or a copy of
it on disk (`rua_source_dir`), which `dump` writes and which is how the
import is tried again and again without asking the live site each time.
Only GET is ever sent.
"""

import json
import os
import urllib.parse

import frappe
import requests

# The records the import reads, in the order it reads them. The rest of the
# old app (chat, issues, todos, payslips, its company settings) is left.
DOCTYPES = (
	"RUA Party",
	"RUA Project",
	"RUA Employee",
	"RUA Quotation",
	"RUA RFQ",
	"RUA LPO",
	"RUA Purchase Receipt",
	"RUA Invoice",
	"RUA Payment",
	"RUA Leave",
	"RUA Attendance",
	"RUA Document",
	"RUA Letter",
)
TABLES = {"RUA Quotation", "RUA RFQ", "RUA LPO", "RUA Purchase Receipt"}
PAGE = 500


class Source:
	def __init__(self, url=None, key=None, secret=None, folder=None):
		self.url = (url or "").rstrip("/")
		self.folder = folder
		self.session = requests.Session()
		if key and secret:
			self.session.headers["Authorization"] = f"token {key}:{secret}"
		self.session.headers["Accept"] = "application/json"
		self.read = {}

	@classmethod
	def configured(cls):
		"""The source this site's config names, or None when it names none."""
		folder = frappe.conf.get("rua_source_dir")
		if folder:
			return cls(folder=folder)
		said = frappe.conf.get("rua_source") or {}
		if said.get("url") and said.get("key") and said.get("secret"):
			return cls(said["url"], said["key"], said["secret"])
		return None

	def _get(self, path, params=None):
		response = self.session.get(self.url + path, params=params, timeout=120)
		response.raise_for_status()
		return response

	def docs(self, doctype):
		"""Every record of `doctype`, with its tables, oldest first."""
		if doctype in self.read:
			return self.read[doctype]
		if self.folder:
			path = os.path.join(self.folder, doctype + ".json")
			rows = json.load(open(path)) if os.path.exists(path) else []
		else:
			rows = self._list(doctype)
			if doctype in TABLES:
				rows = [self._doc(doctype, row["name"]) for row in rows]
		self.read[doctype] = rows
		return rows

	def _list(self, doctype):
		rows, start = [], 0
		while True:
			page = self._get(
				"/api/resource/" + urllib.parse.quote(doctype),
				{
					"fields": json.dumps(["*"]),
					"limit_page_length": PAGE,
					"limit_start": start,
					"order_by": "creation asc",
				},
			).json()["data"]
			rows += page
			if len(page) < PAGE:
				return rows
			start += PAGE

	def _doc(self, doctype, name):
		path = f"/api/resource/{urllib.parse.quote(doctype)}/{urllib.parse.quote(name)}"
		return self._get(path).json()["data"]

	def files(self):
		"""The old site's File rows, so a file keeps its privacy and its name."""
		if "File" in self.read:
			return self.read["File"]
		if self.folder:
			path = os.path.join(self.folder, "File.json")
			rows = json.load(open(path)) if os.path.exists(path) else []
		else:
			rows = self._list("File")
		self.read["File"] = rows
		return rows

	def content(self, file_url):
		"""The bytes of one old file, or None when it can't be had."""
		if not file_url or not file_url.startswith(("/files/", "/private/files/")):
			return None
		if self.folder:
			path = os.path.join(self.folder, file_url.lstrip("/"))
			return open(path, "rb").read() if os.path.exists(path) else None
		try:
			return self._get(urllib.parse.quote(file_url)).content
		except requests.RequestException:
			return None

	def dump(self, folder, with_files=False):
		"""Copy the records (and, when asked, the files) to `folder`."""
		os.makedirs(folder, mode=0o700, exist_ok=True)
		for doctype in (*DOCTYPES, "File"):
			rows = self.files() if doctype == "File" else self.docs(doctype)
			with open(os.path.join(folder, doctype + ".json"), "w") as out:
				json.dump(rows, out, default=str)
		if not with_files:
			return
		for row in self.files():
			url = row.get("file_url")
			if row.get("is_folder") or not url:
				continue
			path = os.path.join(folder, url.lstrip("/"))
			if os.path.exists(path):
				continue
			data = self.content(url)
			if data is None:
				continue
			os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
			with open(path, "wb") as out:
				out.write(data)
