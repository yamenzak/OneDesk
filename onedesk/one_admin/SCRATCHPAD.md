# OneAdmin scratchpad

What is known to be wrong and what is planned, kept short.

- **Not ready.** It is registered so its foot and the module checks apply, and
  stays off `ready: True` until every point is met.
- **Roles.** `test_ready.py` asks for an `abilities.py`. One Operator is given
  on the admin site by `site.py`, not by AccessCenter, and the abilities hook
  runs on every site. Whether operators get abilities is undecided.
- **Help.** Overview, Workspaces and Settings are the pages so far. The rest of
  the operators' half of `AGENTS.md` becomes pages one by one, each with its
  pictures.
- **The rail's tour** uses the window's own marks; Home draws none yet.
- **Keeping a form.** Home's waiting rows still open the record's own form;
  they move to ControlCenter's tabs when Home is reworked.
- **A connected server as a development machine.** Later: Connect Server
  could also offer "Development", running `deploy/local/setup.sh` and the
  rescue kit beside the copies' container, then New Test Workspace and
  `link.sh` for its site, so a new dev bench is one command like a copies
  server. Kept apart as today: the bench under its own user, copies under
  `one-copies`.
- **Reaching production.** Port 22 on the admin box is open to the dev
  server's address, with the servers' key on the dev server, by the owner's
  choice for now (12 Nov 2026). Later: SSH through Cloudflare Access with the
  owner's sign-in, granted when needed, and no open port.
