# Office containers

A Cloudflare Container running [Gotenberg](https://gotenberg.dev) 8
(`docker.io/gotenberg/gotenberg:8`, MIT): LibreOffice, Chromium and PDF tools
behind one HTTP API. One uses it for files a browser can't open: a Word,
Excel, PowerPoint or OpenDocument file is turned into a PDF to read in
OneCloud's viewer, or saved beside it.

## How it is reached

Only OneAdmin calls it (`one_admin/office.py`), with the secret Set Up
Cloudflare made (`x-one-secret`). A workspace asks OneAdmin
(`proxy.office_convert`), which bills it and passes the file on. The Worker
answers only `/forms/libreoffice/convert`, `/forms/pdfengines/merge` and
`/health`, which go to the container, and OneMail's two checks below;
anything else is 404, and a call without the secret 403.

## OneMail's checks

Both run in the Worker, outside every workspace, and keep nothing
(`look.js`; `node --test look.test.mjs`). OneMail asks through OneAdmin
(`proxy.guard_link`, `proxy.guard_file`, `one_admin/office.py`).

- `POST /guard/link` with `{url}`: a browser from Cloudflare's Browser
  Rendering (the `BROWSER` binding), launched for this one link and closed
  after it, opens the address with no cookies and nothing of the workspace.
  It answers `{final_url, redirects, status, title, asks_password, picture,
  failed}`: `picture` a JPEG of 1280×800, base64; `failed` `download`,
  `slow` (15 s to load, 30 s in all) or `unreachable`. Only http and https
  addresses with no user or password in them are opened.
- `POST /guard/file` with the file as the body, its name in `x-one-name`
  (URI-encoded) and the endings that are programs in `x-one-programs`: what
  the bytes are (`kind`, by their first bytes, never the name), whether the
  name says otherwise (`mismatch`), a program found (`program`, by its bytes
  or its ending, inside an archive too), `macros`, a PDF's `scripts`, and an
  archive's files (`inside`, the first 100). Zip, gzip and tar are unpacked
  three deep, 1000 files, 32 MB a file and 64 MB in all; past a limit, or a
  zip with a password, RAR, 7z or CAB, `unchecked` says why. `office` says
  a clean copy can be made, which OneMail asks of the container as a PDF
  through `office_convert`. At most 30 MB, and 30 s of CPU a request.

## Deploying

Set Up Cloudflare (`one_admin/setup.py`, `Setup.office`) mints a token for
the account that may write Workers and Containers, runs `npm install` and
`wrangler deploy` here with a `wrangler.jsonc` it writes (the name carries the
environment: `one-office-dev` on dev), puts the secret, and keeps the
address and secret in One Admin Settings. The image is pulled from Docker
Hub by Cloudflare, so the machine running it needs Node, not Docker.

A first request after a deploy waits a few minutes while Cloudflare places
the container and answers 503; OneAdmin says so rather than billing.

## What it costs

An instance is `standard-1`: half a vCPU, 4 GiB, 8 GB of disk. Cloudflare
bills memory and disk for every second an instance runs and CPU while it
works: about $0.074 an hour busy and $0.038 idle. An instance sleeps five
minutes after its last request, so one conversion costs its seconds of work
and at most five idle minutes, under half a cent. OneAdmin bills that at the
workspace's rate (`credits_per_dollar` × `default_markup`), at least 1 credit,
rounded up. At most two instances run at once.

A link's preview is billed by the seconds its browser was open, at Browser
Rendering's $0.09 an hour, marked up as `guard`, at least 1 credit. Checking
an attachment runs no container and is not billed.
