"""OneLegal: the agreements a workspace runs under, assembled from the modules.

Each module declares the clauses that follow from what it does, in its own
`legal.py` beside the code the clause is about, and this module assembles them
into the documents a person is shown and asked to agree to. See README.md.

Deliberately imports nothing: `registry`, `documents`, `legal` and `assemble`
are pure, so the tests can assemble every document and check its hash without
a site.
"""
