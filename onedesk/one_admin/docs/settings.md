# Settings

The cog at the foot of the rail holds what OneAdmin runs on, a tab each.

| Tab | What it holds |
| --- | --- |
| **Operators** | Who may run OneAdmin. The last one can't be removed. |
| **Cloudflare** | The account, the domains, and **Set Up Cloudflare**. |
| **AWS and GitHub** | The keys that order servers and read the code. |
| **Storage** | The buckets workspaces keep their files in. |
| **Stripe** | The keys that take payments. |
| **AI Gateway** | The gateway OneAI goes through, with **Test Gateway** in its menu. |
| **Weather** | The key behind the forecast on Home. |
| **Grace Periods** | How long a workspace stays overdue, suspended and archived. |

## Keys

A key you type is moved to the site's config when you save, and shows as dots
from then on. Keys are never read back.

Saving tells the other operators what changed and who changed it. A key shows
only as changed.

## Setting Up Cloudflare

**Set Up Cloudflare** finds or makes everything a workspace needs from
Cloudflare, and says each step as it ends. It runs in the background, so
leaving the page stops nothing. Pressing it again checks everything and mends
what is missing.

> The master token can make any token on the account. You can delete it in Cloudflare once setup is done.

## Connecting GitHub

Servers read One's code from GitHub through a GitHub App. **Connect GitHub**,
on the **AWS and GitHub** tab, takes you to GitHub to create the app; press
**Create GitHub App** there. GitHub then asks where to install it: choose the
repository the tile names and press **Install**. You come back here and the
tile shows **Connected**.

Each server is then given a token that reads that one repository for an hour,
when it needs the code. Until the app is installed, servers use the
**GitHub Token** under **Personal Token**. Once it is connected, clear that
field.

You never add a secret to the repository on GitHub. Once the app is
installed, production's OneAdmin writes the secrets the release and OneOS
image workflows use, and **Set Up Again** on the **Cloudflare** tab writes
them again. The tile lists what was written. When OneOS's desktop hasn't been
built for the current code, **Set Up Again** starts building it, and the next
**Set Up Again** deploys it. An app made before this asks for **Secrets: Read
and write** and **Actions: Read and write**: give it those on GitHub, accept
the change on the installation, then press **Set Up Again**.
