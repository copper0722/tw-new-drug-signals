# tw-new-drug-signals

Public method-only repository explaining three non-equivalent Taiwan drug “newness”
signals. M2M contract is English; reader docs are zh-TW.

## Scope

1. Permit detail `restraintItemsCode=07 新藥監視`.
2. TFDA per-case 新成分新藥 review-summary list.
3. Repo-computed normalized-moiety first appearance across permits.

This repo owns semantics, failure modes, reference algorithms, fixtures, controls, and
verification. It owns no acquisition scheduler, bulk mirror, reimbursement data, or
clinical efficacy/ranking judgment.

## Path governance

- `docs/AGENTS.md`: public claim/evidence/control rules.
- `reference/AGENTS.md`: reference implementation, fixtures, tests, live probes.

## Hard semantic rules

- Never flatten the three signals or assert a set relation for code `07`.
- `07` says only that the detail record carries `07`; it does not establish statutory
  status or a regulation subclause.
- Statutory new-drug status requires competent-authority review; do not infer it from a
  formulation/strength/combination field.
- Never assign a specific legal subclause to a permit without its own review report.
- TFDA announcement positives are authoritative for listed cases; silence has multiple
  meanings and is not a negative determination.
- Moiety first appearance is a computation over this repo's normalization, not “the
  molecule's first appearance in Taiwan.” Preserve that qualifier.

## Reproducibility

Every published number is registered in `measurements.json` with time, population,
method, volatility, source, reproduction path, citations, and caveat. The written method
must reproduce the value. Moving denominators are floors/time-stamped, not false ratios.
Composite values are measured directly. Unreproducible numbers are deleted or made
qualitative, with deletion recorded.

## Public safety

No internal host/path/repo/DSN/secret/default value or private schema name. Fixtures are
small reviewed samples, never mirrors. Before push, run the full offline suite,
measurement reproduction, documented-command tests, and a full-tree privacy scan.
Historical audit narratives belong in Git history, not this card.
