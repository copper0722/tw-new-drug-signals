"""`measurements.json` 的契約測試。

這個檔案守的是 repo 的第一條硬規則：**任何數字都不得裸奔**。守法有三層：

1. **結構**：每一項都要有量測時刻、母體、方法、重跑方式。缺一項就紅。
2. **可重跑的真的重跑**：`kind=fixture` / `repo-internal` 的項目，測試會實際
   算一次，跟登記值比對。登記值改了而資料沒改（或反過來）就紅。
3. **文件與登記處對得起來**：文件裡引用的 id 必須存在；登記處宣稱被引用的
   檔案必須真的引用它。

第 2 層還附一個**負控**：故意把登記值改錯，比對器必須抓到。只有正控的檢查
測不出比對器是不是永遠說 OK。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import measure_fixtures as MF

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = json.loads((ROOT / "measurements.json").read_text(encoding="utf-8"))
ENTRIES = DATA["measurements"]
IDS = {e["id"] for e in ENTRIES}

#: 會被掃描「有沒有引用一個不存在的 M-id」的檔案。範圍要寬——引用一個不存在的
#: id 在哪裡都是錯的。
PROSE = (
    sorted((ROOT / "docs").glob("*.md"))
    + [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "fixtures" / "README.md"]
    + sorted((ROOT / "reference").glob("*.py"))
    + sorted((ROOT / "reference" / "tests").glob("*.py"))
)

#: **反向**檢查的範圍：讀者會讀的 zh-TW 正文。這一組檔案若引用了某個 id，
#: 登記處的 `cited_in` 就必須列出它。
#:
#: 刻意比 PROSE 窄。`AGENTS.md` 的變更紀錄、`measure_fixtures.py` 的實作、
#: 測試檔本身都會提到 id，但它們是**在實作或記錄那個數字**，不是在引用它；
#: 把它們納進來只會讓 `cited_in` 變成一份跟著程式碼抖動的清單，於是沒有人
#: 維護它，於是這個檢查失去意義。窄範圍換來的是這條規則真的被遵守。
#:
#: `cited_in` 仍然**可以**額外列出這個範圍之外的檔案（例如 reference 模組的
#: docstring），正向檢查會驗證那些也成立。
PROSE_SURFACE = sorted(
    (ROOT / "docs").glob("*.md")
) + [ROOT / "README.md", ROOT / "fixtures" / "README.md"]

_ID_RE = re.compile(r"\bM-\d{2}\b")

REQUIRED = ("id", "claim", "value", "measured_at", "population",
            "method", "volatility", "source", "reproduce", "cited_in")
KINDS = {"fixture", "repo-internal", "private-data", "public-source"}
VOLATILITY = {"static-fixture", "moves-with-upstream", "moving", "repo-internal"}


# --------------------------------------------------------------------- 結構

@pytest.mark.parametrize("entry", ENTRIES, ids=[e["id"] for e in ENTRIES])
def test_every_measurement_carries_its_provenance(entry):
    """缺量測時刻／母體／方法／重跑方式的數字，就是裸奔的數字。"""
    missing = [f for f in REQUIRED if f not in entry]
    assert not missing, f"{entry['id']} 缺欄位：{missing}"
    assert entry["reproduce"]["kind"] in KINDS
    assert entry["volatility"] in VOLATILITY
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}[+-]\d{2}:\d{2})?",
                        entry["measured_at"]), entry["measured_at"]


@pytest.mark.parametrize(
    "entry", [e for e in ENTRIES if e["volatility"] == "moving"],
    ids=[e["id"] for e in ENTRIES if e["volatility"] == "moving"])
def test_moving_numbers_are_timestamped_to_the_minute(entry):
    """量測當下就在動的數字，只給日期等於沒給。

    背景回填每分鐘都在改母體。一個只標到「日」的數字，讀者無法判斷它是那天
    早上還是傍晚的值——而那天之內它就變過好幾次。
    """
    assert "T" in entry["measured_at"], (
        f"{entry['id']} 是 moving，measured_at 必須到分鐘：{entry['measured_at']}")


@pytest.mark.parametrize(
    "entry", [e for e in ENTRIES if e["reproduce"]["kind"] in
              ("private-data", "public-source")],
    ids=[e["id"] for e in ENTRIES if e["reproduce"]["kind"] in
         ("private-data", "public-source")])
def test_unrunnable_entries_say_what_they_need(entry):
    """跑不了的項目，必須寫出「你需要什麼才能重現」——sql、command 或 note。"""
    r = entry["reproduce"]
    assert any(k in r for k in ("sql", "command", "note")), (
        f"{entry['id']} 無法在本機重跑，卻沒說需要什麼")


def test_ratios_carry_both_sides():
    """比值有兩邊。只給百分比不給分子分母，就是量了一邊。"""
    for e in ENTRIES:
        if isinstance(e["value"], str) and e["value"].endswith("%"):
            assert "numerator" in e and "denominator" in e, (
                f"{e['id']} 是百分比卻沒有分子分母")


# --------------------------------------------------------- 可重跑的真的重跑

@pytest.mark.parametrize("mid", sorted(MF.RUNNABLE), ids=sorted(MF.RUNNABLE))
def test_runnable_measurement_matches_the_register(mid):
    """正控：算一次，跟 measurements.json 記的值比。"""
    assert MF.RUNNABLE[mid]() == MF.expected(mid)


def test_the_comparator_would_catch_a_wrong_value(monkeypatch):
    """負控：把登記值弄錯，比對器必須抓到。

    只有正控的檢查測不出「比對器永遠回 OK」。這裡把 expected() 換成一個一定
    不對的值，check_all() 必須報 FAIL——否則上面那組全綠不代表任何事。
    """
    monkeypatch.setattr(MF, "expected", lambda mid: "definitely-not-the-value")
    results = MF.check_all()
    assert results, "check_all() 回空的，等於什麼都沒驗"
    assert all(not ok for _, ok, _, _ in results), (
        "把登記值全部換錯，比對器竟然還說相符——比對器壞了")


def test_every_runnable_entry_declares_a_runnable_kind():
    """RUNNABLE 裡的項目，kind 必須是 fixture 或 repo-internal。"""
    for mid in MF.RUNNABLE:
        kind = next(e for e in ENTRIES if e["id"] == mid)["reproduce"]["kind"]
        assert kind in ("fixture", "repo-internal"), f"{mid} kind={kind}"


def test_every_fixture_kind_entry_is_actually_runnable():
    """反過來也要成立：宣稱 fixture / repo-internal 的，必須真的有實作。

    否則一個項目可以宣稱自己可重跑，卻永遠沒有人跑過它。
    """
    claimed = {e["id"] for e in ENTRIES
               if e["reproduce"]["kind"] in ("fixture", "repo-internal")}
    assert claimed == set(MF.RUNNABLE), (
        f"宣稱可跑但沒實作：{sorted(claimed - set(MF.RUNNABLE))}；"
        f"有實作但沒宣稱：{sorted(set(MF.RUNNABLE) - claimed)}")


# ----------------------------------------------------- 文件與登記處對得起來

def test_ids_cited_in_prose_all_exist():
    """文件引用的 M-id 必須存在。引用一個不存在的 id 比不引用更糟。"""
    bad = {}
    for path in PROSE:
        for mid in _ID_RE.findall(path.read_text(encoding="utf-8")):
            if mid not in IDS:
                bad.setdefault(str(path.relative_to(ROOT)), set()).add(mid)
    assert not bad, f"文件引用了不存在的 measurement id：{bad}"


@pytest.mark.parametrize("entry", ENTRIES, ids=[e["id"] for e in ENTRIES])
def test_cited_in_is_not_a_wish(entry):
    """正向：登記處宣稱「這個 id 被 X 引用」，X 就必須真的引用它。

    `cited_in` 如果只是願望清單，它會在文件改寫之後安靜地變成謊話。
    """
    for rel in entry["cited_in"]:
        path = ROOT / rel
        assert path.exists(), f"{entry['id']} 的 cited_in 指向不存在的檔案：{rel}"
        assert entry["id"] in path.read_text(encoding="utf-8"), (
            f"{entry['id']} 宣稱被 {rel} 引用，但該檔沒有這個 id")


def _undeclared_citations(entries, cited: dict[str, set[str]]) -> dict[str, list[str]]:
    """正文引用了、但 `cited_in` 沒列出來的 (id -> 檔案)。"""
    missing = {}
    for entry in entries:
        gap = cited.get(entry["id"], set()) - set(entry["cited_in"])
        if gap:
            missing[entry["id"]] = sorted(gap)
    return missing


def _scan_prose_surface() -> dict[str, set[str]]:
    cited: dict[str, set[str]] = {}
    for path in PROSE_SURFACE:
        rel = str(path.relative_to(ROOT))
        for mid in set(_ID_RE.findall(path.read_text(encoding="utf-8"))):
            cited.setdefault(mid, set()).add(rel)
    return cited


def test_cited_in_is_not_only_half_checked():
    """反向：正文引用了某個 id，登記處就必須列出那份正文。

    只有正向的檢查是**單向**的——它抓得到「宣稱被引用但其實沒有」，抓不到
    「其實被引用但沒宣稱」。M-44 的 caveat 早就寫出這個形狀的盲區，`cited_in`
    自己卻留著同一個盲區：一次外部審查在這裡數到十幾筆漂移。

    這正是「正控抓不到過度狹窄」的另一面：兩個方向要分別測。
    """
    missing = _undeclared_citations(ENTRIES, _scan_prose_surface())
    assert not missing, (
        f"正文引用了這些 id，但登記處的 cited_in 沒列出來：{missing}")


def test_the_reverse_citation_check_fires_on_a_known_positive():
    """負控：反向檢查必須抓得到一筆刻意造出來的漂移。

    一個永遠回傳空 dict 的檢查，和一個真的乾淨的 repo 長得一模一樣。
    """
    fake = [{"id": "M-01", "cited_in": ["docs/00-sources.md"]}]
    cited = {"M-01": {"docs/00-sources.md", "docs/07-controls-and-pitfalls.md"}}
    assert _undeclared_citations(fake, cited) == {
        "M-01": ["docs/07-controls-and-pitfalls.md"]}


def test_the_reverse_citation_check_accepts_a_superset_declaration():
    """負控之二（過度廣泛的方向）：`cited_in` 多列了程式檔不算漂移。

    反向檢查的範圍刻意窄於正向檢查，所以一個列出 `reference/…` 的登記項目
    不可以因此變紅——否則這條規則會逼所有人把實作檔也登記進去。
    """
    fake = [{"id": "M-01",
             "cited_in": ["docs/00-sources.md", "reference/measure_fixtures.py"]}]
    assert _undeclared_citations(fake, {"M-01": {"docs/00-sources.md"}}) == {}


#: 被撤回的數字，以及撤回理由。值是給錯誤訊息用的。
RETRACTED = {
    "每年約 30–50 個新分子": "無來源，且與 M-34 循環論證",
    "每月 15–34 張": "任何分母都重現不出來，見 M-46",
    "3–5 倍": "沒量過的區間，實際是 M-47 的 3.6 倍",
    "1,472": "清單套用日期更正前的舊值，見 M-37",
    "1,216": "減錯了東西（該減 249 不是 256），見 M-38",
    "1,639": "從換發日算出來的間隔，不存在，見 M-39",
    "4,037": "重現不出來的分子，已重新量測，見 M-43",
}

#: 撤回敘述會用到的詞。出現在附近就代表這一次提及是在講「這個數字錯了」。
#: 中英兩組都要有：`docs/` 是 zh-TW，`AGENTS.md` 是 M2M 英文，只列中文的話
#: 這個檢查會在英文檔上誤報——那是判準不完整，不是文件出錯。
_RETRACTION_CUES = (
    "早期版本", "已刪除", "收回", "已改", "取代", "撤回",
    "那個說法是錯的", "不適用", "重現不出來", "減錯",
    "deleted", "Deleted", "retracted", "Retracted", "replaced", "Replaced",
    "withdrawn", "superseded", "unreproducible", "artifact", "stale",
)

#: 檢查命中位置前後各幾行。
_CUE_WINDOW = 6


def _mentions_without_retraction(text: str, phrase: str) -> list[str]:
    """回傳提到 phrase、但附近找不到撤回語的行。"""
    lines = text.splitlines()
    bad = []
    for i, line in enumerate(lines):
        if phrase not in line:
            continue
        lo, hi = max(0, i - _CUE_WINDOW), min(len(lines), i + _CUE_WINDOW + 1)
        window = "\n".join(lines[lo:hi])
        if not any(cue in window for cue in _RETRACTION_CUES):
            bad.append(f"L{i + 1}: {line.strip()[:70]}")
    return bad


def test_retracted_numbers_only_appear_as_retractions():
    """被撤回的數字，只能以「這個數字錯了」的身分出現。

    直接禁掉字串是行不通的：撤回段落本身就必須引用那個數字，否則讀者不知道
    被撤回的是什麼。所以判準不是「有沒有出現」，而是「出現的時候，附近有沒有
    在講它被撤回」。

    這條規則有一個容易忽略的前提：**寫完撤回段落之後，你自己的文字也變成了被
    掃描的語料。** 一個只比對字串的檢查，會把作者的更正當成復發。
    """
    hits = {}
    for path in PROSE:
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        for phrase, why in RETRACTED.items():
            bad = _mentions_without_retraction(text, phrase)
            if bad:
                hits[f"{path.relative_to(ROOT)} :: {phrase}（{why}）"] = bad
    assert not hits, f"被撤回的數字以肯定語氣出現：{hits}"


def test_the_retraction_check_fires_on_a_known_positive():
    """負控之一：判準必須抓得到一段沒有撤回語的復發。

    一個抓不到已知陽性的掃描器，回報「乾淨」和回報「壞了」長得一模一樣。
    """
    relapse = ("## 逐年產出\n"
               "\n"
               "完整年度落在 31–50 之間，與台灣每年約 30–50 個新分子的量級相符。\n"
               "\n"
               "做合理性檢查時要排除部分年度。\n")
    assert _mentions_without_retraction(relapse, "每年約 30–50 個新分子")


def test_the_retraction_check_accepts_a_real_retraction():
    """負控之二：判準不可以把作者自己的更正誤判成復發。

    這是過度廣泛的方向。只有正控（上一個測試）測不出這一面——一個把所有東西
    都判成陽性的比對器，正控會完美通過。
    """
    proper = ("早期版本在這裡寫了一句「與台灣每年約 30–50 個新分子的量級相符」，\n"
              "那句話已刪除：它沒有來源。\n")
    assert not _mentions_without_retraction(proper, "每年約 30–50 個新分子")
