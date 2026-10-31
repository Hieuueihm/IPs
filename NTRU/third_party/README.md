# Reference source

`r8/` is a pristine detached checkout of
https://github.com/fixed-point-fndsa/fixed-point-c.git at
`ad1e5bf7714d53230ad457364db8a46a1b459c94`.

The upstream source and its existing license notices are preserved. No source
patch is applied for vector capture; the external C wrapper is in
`sim/ref/r8_capture.c`. Build output goes to `study/build/r8/<platform>/`.
The validator can clone the checkout again when it is absent; it never resets an
existing checkout with a different commit or local modifications.

See `docs/numeric_contract.md` for the pinned configuration, LP64 requirement,
commands, vector format and limits of the differential checks.
