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
`/health`; anything else is 404, and a call without the secret 403.

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
