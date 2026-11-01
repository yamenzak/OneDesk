# One on your own machine

A bench in WSL2 on Windows, with two sites: `one.localhost` (a workspace) and
`admin.localhost` (OneAdmin). Frappe Cloud stays where One runs for real; this
is where it is built, because a change shows up in seconds instead of after a
deploy.

## Windows, once

In PowerShell, as administrator:

    wsl --install -d Ubuntu

Restart when it asks, open **Ubuntu** from the Start menu, and choose a user
name and password. Install **VS Code** on Windows with its **WSL** extension.

## Ubuntu

Copy `setup.sh` into Ubuntu and run it as your own user:

    bash setup.sh

It stops once to have WSL restarted (`wsl --shutdown` in PowerShell, then open
Ubuntu again and run it again), and once for the GitHub sign-in. The rest takes
twenty minutes or so. Run it again at any time; it only does what is missing.

Keep the bench in Ubuntu's own home (`~/one-bench`), never under `/mnt/c`:
files on the Windows side are many times slower to read from Linux.

## Every day

    cd ~/one-bench && bench start

and open `http://one.localhost:8000` or `http://admin.localhost:8000` in the
Windows browser. Passwords are in `~/.one-local`. Push to `main` as before;
Frappe Cloud deploys from there.

frappe, erpnext and hrms are pinned to the commits in `upstream.json`, which
is what the tests were last checked against. When Frappe Cloud's bench moves
ahead, record the new commits there and run `setup.sh` again.
