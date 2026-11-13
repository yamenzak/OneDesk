"""The loop while working: OneLint's changed mode, and `--all` for the gate
(scripts/lint.py, where it is described)."""

import sys

import lint

if __name__ == "__main__":
	sys.exit(lint.main(sys.argv[1:]))
