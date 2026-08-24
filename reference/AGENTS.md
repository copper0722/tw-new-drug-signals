# reference/ — executable reference methods

- Standard-library reference modules are bounded CLIs; no hidden private dependency.
- Bulk government-host loaders are out of scope. Manual live probes are one-item,
  throttled, and never part of `make test`.
- Offline tests make no network call and include positive/negative controls for every
  broadening rule.
- Fixtures carry retrieval date, exact public provenance, and “not a mirror” scope.
- Any sibling import is explicit and tested; standalone modules must actually run alone.
- Network commands use bounded timeout/throttle and fail on HTTP errors before parsing.
- `measure_fixtures.py` must independently reproduce every offline-reproducible
  measurement entry.
