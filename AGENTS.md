# tw-new-drug-signals — agent card

Public, method-only repository about how Taiwan's TFDA marks a drug permit as
"new". M2M English; the deliverable prose in `README.md` and `docs/` is zh-TW
because its audience is Taiwanese clinicians, pharmacists and policy researchers.

Bootstrapped 2026-08-05. Not yet published: no GitHub remote, no push.

## What this repo is

Semantics, failure modes, crosswalk, and a verification protocol for three
non-equivalent "new drug" signals:

1. `restraintItemsCode` code `07 新藥監視` on the per-permit detail record.
2. TFDA 新成分新藥核准審查報告摘要 (the only per-case list TFDA itself names
   新成分新藥).
3. Self-computed moiety first-appearance over all permits including revoked.

## What this repo is NOT

| Not this | Owner |
|---|---|
| Acquisition / scrapers / scheduling | a separate **private** acquisition repo — do not name or link it anywhere in this tree; this file ships publicly too |
| NHI reimbursement rules, drug pricing | `nhi-rule-history` (public) |
| Any data mirror (permit table, ledger, the 273-permit report table) | nobody — regenerate from source |
| Clinical judgement, drug ranking, efficacy claims | out of scope, permanently |
| Bulk loaders, batch queries against government hosts | out of scope, permanently |

Boundary rule, one sentence: **removing it stops you getting the bytes → does not
belong here; removing it makes you believe something false about the bytes →
belongs here.** Phrased without naming the private repo, because the public
README has to state the same boundary and cannot point at a 404.

## Deliberate deviations from the private acquisition repo's house rules

That repo's rules are for standalone executable scrapers. This one ships a
reference library plus an offline test suite, so two rules are deliberately
inverted. Document, don't silently drift.

| Their rule | Here | Why |
|---|---|---|
| One file = one scraper, no sibling imports | `tw_nme_titles.py` imports `tw_permit_id.py` | It needs the 61-entry closed 字別 set. The other three modules ARE standalone, and `test_standalone_modules_really_stand_alone` proves it. README states the copy-set explicitly. |
| Read-only HTTP, never POST | `tfda_lic_query.py` POSTs | The per-permit detail endpoint is POST-only. Mitigated: single permit per invocation, no loop, no `--input-file`, 30s default interval. **Any bulk loader over this endpoint is out of scope for every public repo here** — changing that requires an explicit owner decision, not a drive-by. |

## Layout

| path | purpose |
|---|---|
| `README.md` | zh-TW, decision table first; `## English` section at the end (single file — two READMEs drift) |
| `docs/00`–`08` | one concern each; every page opens with what it answers and closes with a positive AND negative control |
| `measurements.json` | the figure register: one entry per number, plus a `deleted` section recording every figure withdrawn and why |
| `reference/*.py` | stdlib-only reference implementations, each runnable as a CLI |
| `reference/measure_fixtures.py` | recomputes the offline-reproducible entries of `measurements.json`; `make measurements` |
| `reference/tests/` | offline pytest; MUST NOT make network calls |
| `fixtures/` | code-table snapshots + labelled samples; every file carries a retrieval date and "not a mirror". Two of five carry an executable refetch command; the other three say what they would need, because this repo ships no bulk fetcher — do not write a pointer that reads like a recipe |
| `Makefile` | `test` (offline), `measurements` (offline), `check-live` (one manual request), `codes` (two requests, 30s apart). Both network targets use `curl -sS --fail`; a target that pipes an unchecked body into a parser reports a rate-limit as a data change |

## Hard rules

1. **No bare numbers — every figure is registered in `measurements.json`.**
   One entry per figure: `measured_at`, `population`, `method`, `volatility`,
   `source`, `reproduce`, `cited_in`, plus any `caveat` that must travel with
   it. Prose cites the `M-NN` id instead of restating provenance. Cannot supply
   those fields → rewrite as qualitative prose or **delete**, and record the
   deletion with its reason in the `deleted` section. Deleting is a valid and
   frequently correct outcome; thirteen figures were deleted or replaced on
   2026-08-05.
   - `reproduce.kind` is one of `fixture` / `repo-internal` (recomputed offline
     by `make measurements`, and asserted by `test_measurements.py`),
     `public-source`, or `private-data`. The last two must state what they need.
   - **A re-run recipe that does not run is worse than none.** It reads as
     verified. Three shipped recipes were unrunnable (an undefined `titles`
     variable, two `<你的清單表>` placeholders assuming columns this repo never
     builds); all three are now either executable or explicit about the data
     they require.
   - **A figure whose denominator is still moving may not be published as a
     ratio.** Report a floor (`≥ N`) and pin the timestamp to the minute.
     `volatility: moving` entries are required to carry a minute-level
     `measured_at`, and a test enforces it.
   - **Query the composite, not the ingredients.** A difference, ratio or index
     assembled from two true numbers is not observed until you look it up
     directly. The "unconfirmed flags" figure subtracted the announced-permit
     count from the flag count, but 7 of those announced permits were never
     flagged, so the subtrahend was wrong; both ingredients were real and
     nothing errored. Measured directly: 1,218 (`M-38`).
   - Internal contradictions are resolved by **counting**, never by picking a
     side: 11-vs-10 live probes → `M-44` = 11; 12-vs-14 checklist items →
     `M-51` = 14, now pinned by a test.
   - **A `method` must be able to produce its own `value`.** `M-44`'s method
     named `validDate` as a detail-API fact; `validDate` is in the bulk listing
     and `docs/06` cites it for two permits outside the list, so the method
     yielded 13 against a recorded 11. Re-derive the value from the written
     method before shipping either.
   - **`cited_in` is checked in both directions.** Forward: every declared file
     really cites the id. Reverse: every reader-facing doc that cites the id is
     declared. The reverse check is scoped to `docs/*.md` + `README.md` +
     `fixtures/README.md` — `AGENTS.md`, tests and `measure_fixtures.py` mention
     ids while implementing or logging them, and forcing those into the register
     would make it churn until nobody maintained it.
2. **Every doc page ends with a control section containing BOTH a positive and a
   negative control.** A positive control cannot detect over-breadth. The
   negative control must be drawn from the population most easily confused with
   a positive.
3. **No network tests.** `make test` is offline. `check-live` is manual and is
   never wired into automation.
4. **Verbatim frames contain only source text.** Counts, characterisations and
   readings go in surrounding prose attributed to the author. Applies to statute
   quotes in `docs/01` and to the `interpretation` string in `tw_restraint.py`,
   which is prefixed 「本 repo 解讀：」 precisely because that string travels into
   downstream reports.
5. **Never assert a set relation for `07`.** Not `07 = 新成分新藥`, and equally
   not "`07` is a superset/subset of 新成分" — that was written, and retracted
   2026-08-05. TFDA publishes no inclusion criteria for the code and no
   population census exists, so only the *observed scope* may be stated: seen on
   officially announced 新成分新藥 permits AND on permits whose ingredient is not
   a first appearance here. `test_interpretation_claims_no_set_relation` pins the
   retracted wording out of the string that travels downstream.
6. **Statutory status is conferred by review, not read off a field.** 藥事法 §7
   requires 經中央衛生主管機關審查認定. Never write that a strength change, a
   dosage-form change, or a two-ingredient combination "is therefore a new drug";
   §2 of the 施行細則 requires the change to produce 新醫療效能 (first limb) or to
   be 優於各該單一成分藥品之醫療效能 (second limb), and §7 review on top.
7. **Never assign a 施行細則 §2 subclause to a specific permit** unless its own
   review report says so. Two permits were mislabelled this way (`docs/05`).
8. **No data mirrors.** Fixtures are test samples sized for tests.
9. **Never dress this repo's computation as an official determination, and never
   flatten the three signals into one kind of thing.** They differ in standing,
   and the error runs in both directions:
   - The TFDA announcement list **is authority for the positives it lists** —
     saying "all three are just candidate generators" demotes it. Only its
     *silence* is unusable, and silence has at least three causes (not yet
     announced / outside that list's scope / genuinely not one), so it may never
     be written as "always means not yet announced".
   - `07` answers exactly one question: whether the detail record carries `07`.
     Never "it tells you whether this is a statutory new drug", and never which
     §2 subclause.
   - Moiety first appearance is the only pure candidate generator. It is a
     statement about **this repo's normalized moiety string**, never about "the
     molecule in Taiwan" — salt stripping discards a distinction the regulator
     treated as material (`docs/05`, 康紓維 / leuprolide mesylate). Always keep
     the qualifier when abbreviating.
10. **Documented commands must run from a clean clone, from the repo root.**
    Doc paths are `reference/<file>.py`, not bare `<file>.py`; snippets define
    every variable they use. Verify by executing them out of the markdown, not
    by reading them.

## Public-safety gate (run before any push)

Author is a named practising physician; a confident wrong regulatory claim is the
expensive failure mode, not an incomplete one.

- No internal hostnames, tailnet/LAN IPs, DSNs, absolute `/Users/...` paths,
  private repo names, secret-store paths, internal panel URLs or ports.
- **The leak is usually in DEFAULT VALUES, not secret literals.** Audit the
  second argument of every `os.environ.get`, every argparse `default=`, every
  module constant. As of 2026-08-05 this repo reads no environment variables at
  all and every constant is either a public FDA URL or a measured invariant.
- Fixtures are reviewed by hand: they originate near a private pipeline and are
  the likeliest carrier of an internal uid, path or column name.
- Full-tree scan before the first push; record the result in the commit message.

## Publication state

Local only. Creating the GitHub repo and registering it in the fleet repo roster
are owner actions. Publication follows an external review of the prose, not this
card.

## Status

Passes are listed oldest first. **No per-row test counts** — they expire the way
the README's test count did (deleted 2026-08-05 for exactly that reason). Run
`make test` for the current number.

| # | pass | what it did |
|---|---|---|
| 1 | Bootstrap | Repo written, offline test suite green. All figures measured the same day against 66,440 permits / 206 announcements. Live probe of 11 permits at 30s spacing, no 422. 藥事法 §7/§45 and 藥品安全監視管理辦法 §1/§2/§8 verified verbatim against law.moj.gov.tw. |
| 2 | Legal / factual correction, after an external review failed the repo | Retracted: the `07`-is-a-superset claim; "§7 sets up no review track"; "a dose change is itself a statutory new drug"; "two approved ingredients combined is a new drug"; "食藥署實務比條文更寬"; "only `07` carries 新藥 in its name"; `監視 ⊅ 新藥` (wrong direction, now `⊄`); the 24/25 reading; "permanent stamp" / "present at issue"; and the docs/06 inference that most `issueDate`s are original. Corrected: both worked examples in `docs/05` (001082 is itself an announced 新成分新藥 whose `oriIssueDate` is 2018-05-10, so it was mis-ranked by the date field; 028546 is a new salt, leuprolide mesylate, whose distinction the moiety normalisation strips), the 康紓維 character, and the impossible-date section (seven permits, six with evidence-backed corrected values held read-side, one left unresolved). Verified verbatim: 藥事法 §40-2 IV, 藥品安全監視管理辦法 §3, 藥品查驗登記審查準則 §4 (`L0030057`). |
| 3 | Numbers | Every figure moved into `measurements.json`; prose cites `M-NN`. Added `reference/measure_fixtures.py` + `make measurements`, with a negative control proving the comparator can fail. Deleted or replaced thirteen figures — an unsourced "30–50 new molecules a year" (also circular against `M-34`), an unreproducible "15–34 per month" and the "most weeks" claim it supported (`M-46`: 41% of weeks), an unmeasured "3–5×" (`M-47`: 3.6×), the 1,639-day gap computed off a re-issue date, a stale flag total and a difference that subtracted the wrong quantity (`M-37`/`M-38`), an unreconstructable 4,037/66,267 (`M-43`), a ratio whose denominator was a running backfill (`M-48`, now a floor), the four-molecule ATC anecdote (`M-33`, now 87.9% vs 1.8%), an approximate 98%, and the README's test count. Fixed three unrunnable re-run recipes. Resolved both internal contradictions by counting: `M-44` = 11, `M-51` = 14. New: `M-25`, `M-52`. |
| 4 | Runnability + deletion | Fixed every command a stranger would paste: `docs/02` and `docs/06` invoked modules at the repo root where they do not exist (now `reference/…`), and the `docs/03` 字別 snippet raised `NameError` on an undefined `titles`. Hardened `make codes` (30s gap, timeout, `curl -sS --fail`). Attribution fixes in `docs/03` (silence has three causes) and `docs/08` (the three signals differ in standing). Deleted `docs/07`'s incident log, `docs/06`'s database-operations note, `docs/04`'s self-correction, `docs/08`'s DDL, and `docs/00`'s duplicate decision table. |
| 5 | **Close-out, after a stranger run + an adversarial read** | Details below. |

### Pass 5 (close-out)

Two independent reviews: one stranger executing every documented command from a
clean clone, one adversarial read of the prose against PG and statute. Applied:

- **Fabricated mechanism, newly introduced by pass 4** — `docs/05` row 3 claimed
  the 2023 flu permit's moieties were "identical after normalisation" to the 2013
  one. **The shipped normaliser refutes it**: 3 of 4 shared, one differs. The real
  mechanism is that the *ingredient field is mutable* — the 2013 permit's
  ingredient column now holds 2022/2023 strains. Both permits' ingredient strings
  are now in the fixture, the refutation is executable (`M-53`), and the mutable
  ingredient field is documented as a **fifth noise class** (`docs/04`, `docs/00`
  §C) with its own figure (`M-54`). It produces false *negatives*, which the four
  existing noise classes do not.
- **Public safety**: `.gitignore` carried an internal directive number, a retired
  internal library name and a home-directory path. Rewritten to five lines. The
  identifier scan does not catch this — it lives in boilerplate nobody re-reads.
- **`make check-live` was the failure it warns about**: bare `curl -s`, so a 422
  printed `None` and exited 1 — simultaneously "the marker is gone" (forbidden by
  `docs/00` §C) and "the canary failed" (forbidden by `docs/07` §5). Now
  `curl -sS --fail` with exit 3 for "could not ask".
- **`cited_in` was one-directional**, the same blind spot `M-44`'s caveat
  describes. Added the reverse assertion over the reader-facing prose surface,
  plus two controls (fires on drift; does not fire on a code-file superset), and
  reconciled 15 entries.
- **`M-44`'s method could not produce `M-44`'s value**: it counted `validDate` as
  a detail-API fact, but `validDate` is in the bulk listing and `docs/06` cites it
  for two permits outside the list — by that method the answer was 13. Criterion
  narrowed to `restraintItemsCode` + `oriIssueDate`; value unchanged at 11.
- **Retracted-abbreviation leak**: "在台灣…首見" survived in six places including
  the `interpretation` string that travels downstream, and README applied the
  statutory term 新成分 to a self-computed result.
- **New statute**: 藥事法 §47 I verified verbatim. Permit validity is §47, not
  監視辦法 §8 — the repo had attributed the five years to the wrong provision, and
  §47's renewal cap is what explains the 15-year case in `docs/02`. 藥品查驗登記
  審查準則 §4's opening "本章用詞定義如下" is now inside the quote, because the
  definition is chapter-scoped.
- Smaller: `docs/06` said "four independent signals" over a six-row table (now
  five corroborations, four mechanisms); a bare "12 年" that is 11 years 9 months
  and rounds the wrong way; the 7-character claim that described the *serial*, not
  the licId (9 characters); a no-op `.replace` that read as a real carve-out; a
  usage hint that printed the literal word `CLI:`; module docstring CLI lines that
  did not run from the repo root; `fixtures/README`'s refetch column, which
  claimed recipes two files do not have; the undocumented `//` header that makes
  the `.jsonl` files invalid JSON Lines; and the code-table snapshots' renamed
  fields (`value`/`text` → `code`/`name`), which would `KeyError` anyone following
  `docs/00` §B.

## Open questions

- `issueDate` vs `oriIssueDate` disagreement rate rests on the 11 permits whose
  detail this repo cites (`M-44`), 1 of them disagreeing (`M-21`). That cannot
  support a population estimate. Measuring it costs one API call per permit at
  30s spacing. `docs/06` says so rather than quoting a rate. The two proxies once
  used to argue "most are original" (`M-43`: serial inversion 6.1%, sub-5-year
  expiry 2.7%) do NOT estimate a re-issue rate — a re-issue preserves the serial
  and can carry any expiry interval — and that inference is retracted.
- **`oriIssueDate` has not yet entered the first-appearance computation** (30s-paced
  backfill). Until it has, `M-36` (249/256 = 97.3%) stands as measured on
  2026-08-05 keyed on `issueDate`, **not as a current value**, and must not be
  compared against any post-backfill number: two methods, two figures. Everything
  downstream of the DUPIXENT date carries the same restriction — `M-15`'s −2,232
  lower bound and the deleted 1,639-day gap in `docs/05` are both artifacts of it.
- Several registered figures are `volatility: moving` (`M-35` … `M-39`, `M-45`
  … `M-48`, `M-52`): a paced detail backfill and periodic listing rebuilds change
  them under you. They carry minute-level timestamps and a test enforces that.
  **Re-measure before quoting one; do not carry it forward from this card.**
- The false-positive direction is still unmeasured. `M-38`'s 1,218 flagged
  permits have no external confirmation, and at least two false-positive classes
  are known (coating agents, same-salt spellings).
- `M-44`'s check is one-directional: it proves the 11 listed permits appear in
  `docs/`, but a 12th detail citation added without updating the list would not
  turn the test red. (`cited_in` had the identical blind spot and it was closed
  in pass 5; this one is still open because the reverse direction needs a
  permit-number regex over prose, which would also match permits cited from the
  bulk listing.)
- **The ingredient field's mutability is documented but not measured.** `M-54`
  proves the mechanism exists on one drug family (influenza vaccines, found by
  a strain string). The population-scale question — how many current permits
  have an ingredient field newer than their issue date — needs the listing's
  change-date column compared against `issue_date` across the whole table, and
  that has not been run. Until it is, `docs/04` states the mechanism and gives
  no rate.
- The distribution of `1L 監視中新藥` / `26 監視期滿新藥` was never measured, so
  `docs/02` stops at "these codes exist" and gives no conclusion about current
  monitoring status.
- Co-occurrence of `24` / `25` with other restraint codes was never measured
  across the population, so those codes are documented as a strong
  counter-indication to first appearance (grounded in 藥品查驗登記審查準則 §4's
  definition of 學名藥), not as proven mutual exclusion.
- The 1,218 moiety-flagged permits TFDA has never confirmed (`M-38`) are
  unmeasured in the false-positive direction. `docs/05` states the 97.3% figure
  (`M-36`) as one-way recall for exactly this reason.
