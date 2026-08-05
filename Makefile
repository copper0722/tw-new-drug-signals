.PHONY: help test measurements check-live codes clean

PYTHON ?= python3

help:
	@echo "make test          # offline test suite (no network)"
	@echo "make measurements  # offline: re-run every figure computable from the shipped fixtures"
	@echo "make check-live    # ONE request against the known-positive control"
	@echo "make codes         # refetch both TFDA code tables (2 requests, 30s apart, ~30s total)"

# Offline. Recomputes the fixture-backed and repo-internal entries of
# measurements.json and diffs them against the recorded values. The remaining
# entries need data this repository deliberately does not ship; the tool prints
# what each of them requires instead of pretending it can run them.
measurements:
	@$(PYTHON) reference/measure_fixtures.py

# Fully offline. Never add a network test to this target.
# The pytest check is not politeness: without it a reader who has not installed
# it gets `No module named pytest` and no idea that one line fixes it.
test:
	@$(PYTHON) -c 'import pytest' 2>/dev/null || { \
	  echo "pytest is not installed for $(PYTHON)."; \
	  echo "  $(PYTHON) -m pip install -r requirements-dev.txt"; \
	  echo "(only the tests need it; reference/ is standard library only)"; \
	  exit 1; }
	$(PYTHON) -m pytest reference/tests -q

# One request against a government host, so it uses the same `curl -sS --fail`
# guard as `codes` below. Without `--fail` curl exits 0 on an HTTP error and
# pipes the error body into the checker, which then prints `None` — i.e. it
# reports "the marker is gone" (forbidden by docs/00 §C) AND "the canary failed"
# (forbidden by docs/07 §5) for what is only our IP being rate-limited.
#
# Exit codes are distinct on purpose: 1 = the canary really failed (200 OK, no
# `07`), 3 = we could not ask (HTTP error / timeout), which is not a canary
# result at all. NOTE: `make` collapses any recipe failure to its own exit 2, so
# those codes are only visible if you lift the two commands out of here — through
# `make`, read the message, not the status. Verified by running both branches.
#
# Deliberately NOT wired into any automation: it touches a government host.
# To exercise either failure branch without touching that host, override the URL:
#   make check-live LIC_URL='file:///tmp/nomarker.json'
CANARY_ID = 60001328
check-live:
	@echo "# known positive: $(CANARY_ID) (IBALIZUMAB) must carry 07 新藥監視"
	@body=$$($(CURL_ONCE) \
	    -H 'Content-Type: application/json' \
	    -d '{"data":{"licBaseId":"$(CANARY_ID)"}}' \
	    '$(LIC_URL)') || { \
	  echo "# 查詢失敗（HTTP 錯誤或逾時）。HTTP 422 = 我方 IP 被限流（docs/00 §C）；" >&2; \
	  echo "# 那不是 canary 失敗，也不代表標記消失。稍後再跑。" >&2; \
	  exit 3; }; \
	printf '%s' "$$body" | $(PYTHON) -c 'import json,sys; d=json.load(sys.stdin).get("data") or {}; d=d[0] if isinstance(d,list) and d else d; c=d.get("restraintItemsCode"); print(c); sys.exit(0 if c and any(str(x).split()[:1]==["07"] for x in c) else 1)'

# Two requests against a government host, so this target obeys the rule this
# repository teaches everywhere else (docs/00 §C, tfda_lic_query.py): one at a
# time, 30 seconds apart, with a timeout. It therefore takes ~30 seconds.
#
# `--fail` is the point of these targets being Makefile rules instead of lines
# you paste. Without it curl exits 0 on an HTTP error and writes the error body
# to stdout, so a 422 (our IP is rate-limited) is captured as if it were a code
# table — the exact "record the 422 as data" failure docs/00 §C warns about.
# `-S` keeps the reason visible now that `-s` is on.
CODES_URL = https://lmspiq.fda.gov.tw/api/public/codes/search/full/codeKind
LIC_URL = https://lmspiq.fda.gov.tw/api/public/sh/piq/1000/licSearch
CURL_ONCE = curl -sS --fail --max-time 45

codes:
	@echo "# 1/2 Lic.Type（字別）" >&2
	@$(CURL_ONCE) '$(CODES_URL)/Lic.Type' || { \
	  echo "# 抓取失敗。HTTP 422 = 我方 IP 被限流（docs/00 §C），不是碼表消失。" >&2; \
	  exit 1; }
	@echo
	@echo "# 等 30 秒再送第二次（善待政府主機）" >&2
	@sleep 30
	@echo "# 2/2 Restraint.Dr（限制項目）" >&2
	@$(CURL_ONCE) '$(CODES_URL)/Restraint.Dr' || { \
	  echo "# 抓取失敗。HTTP 422 = 我方 IP 被限流（docs/00 §C），不是碼表消失。" >&2; \
	  exit 1; }
	@echo

clean:
	rm -rf .pytest_cache reference/__pycache__ reference/tests/__pycache__
