#!/usr/bin/env python3
"""成分字串 -> moiety 集合，以及「這個**正規化 moiety 字串**是不是首見」。

這個模組獨立，不 import 任何兄弟檔。

回傳值是關於**字串**的敘述，不是關於分子、也不是關於法規身分的敘述。它沒有
任何官方地位：它是候選產生器，不是裁決者。尤其**不要把它縮寫成「這個分子在
台灣首見」**——正規化會剝掉鹽別，而主管機關可能把鹽別視為有意義的差異
（實例：leuprolide mesylate 對 acetate，見 docs/05）。

## 為什麼要寫成程式

因為許可證的成分欄是自由文字，而它的四種噪音都會讓「字串首見」把老藥算成
新藥。四種都取自真實資料（2026-08-05）：

| 噪音 | 真實字串 | 天真作法的結果 |
|---|---|---|
| 鹽／水合物後綴 | `DASATINIB MONOHYDRATE`（2026） | 判為新，實際 2008 就有 `DASATINIB` |
| 賦形劑混進成分欄 | `CEVIMELINE HYDROCHLORIDE;;CAPSULE SHELL` | 字串唯一，判為新 |
| 複方 | `NETARSUDIL MESYLATE;;LATANOPROST` | 整串唯一，判為新 |
| 同產品多劑量 | 一個產品的 20/50/70 mg 各一張證 | 同一分子算三次 |

## 這個方法的結構性極限（不是 bug，是定義）

`SALT_SUFFIXES` 和 `EXCIPIENT_PREFIXES` 都是**封閉清單**。清單沒收錄的鹽別
寫法或賦形劑名稱，會安靜地變成一個「新 moiety」。這不是可以靠寫得更仔細
解決的：真實資料裡量測到兩個例子——

- `OPADRY PINK;;RIVAROXABAN`（衛部藥製字第062360號）：包衣劑被當成活性成分。
- `Nintedanib esylate`（2026）與 `Nintedanib ethanesulfonate`（2015）：
  同一個鹽的兩種寫法，各自成為一個 moiety。

兩者本模組都收了，但**下一個沒收錄的寫法還是會漏**。所以這個訊號的正確用法
是「候選清單 + 逐筆核對」，不是「直接發表的新藥數字」。見 docs/04、docs/07。

## 基線是定義的一部分

`first_appearance()` 的 `baseline` 是**必填**參數，故意不給預設值：基線必須
涵蓋**全部**許可證，包含已註銷的。漏掉已註銷證，會把「早就上市、證已註銷」
的分子算成新藥。真實案例：REMDESIVIR 的 2020 年許可證已註銷，只看現行證會
把 2023 年那張判成首見。

CLI:
    python3 reference/tw_moiety.py 'CEVIMELINE HYDROCHLORIDE;;CAPSULE SHELL'
    python3 reference/tw_moiety.py --json 'OPADRY PINK;;RIVAROXABAN'
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from typing import Iterable, Mapping

__all__ = [
    "COMPONENT_SEP",
    "SALT_SUFFIXES",
    "FORM_WORDS",
    "EXCIPIENT_PREFIXES",
    "COUNTER_IONS",
    "MoietySet",
    "normalize_component",
    "moieties",
    "first_appearance",
    "is_first_appearance",
]

COMPONENT_SEP = ";;"

#: 鹽／酯／水合物後綴。只在**字尾**剝除，且剝到剩下反離子時不剝
#: （否則 `SODIUM CHLORIDE` 會變成 `SODIUM`）。
SALT_SUFFIXES: frozenset[str] = frozenset("""
HCL HYDROCHLORIDE DIHYDROCHLORIDE 2HCL HYDROBROMIDE HYDROIODIDE
SULFATE SULPHATE BISULFATE HEMISULFATE SULFATES
PHOSPHATE DIPHOSPHATE HEMIPHOSPHATE NITRATE
MALEATE DIMALEATE FUMARATE TARTRATE BITARTRATE CITRATE OXALATE
ACETATE SUCCINATE LACTATE GLUCONATE PAMOATE EMBONATE
MESYLATE MESILATE ESYLATE ESILATE ETHANESULFONATE ETHANESULPHONATE
BESYLATE BESILATE BENZENESULFONATE TOSYLATE TOSILATE NAPADISYLATE
XINAFOATE HYCLATE TRIFLUTATE
PROPIONATE DIPROPIONATE VALERATE FUROATE PIVALATE PALMITATE STEARATE
SODIUM DISODIUM MONOSODIUM POTASSIUM CALCIUM MAGNESIUM LITHIUM ZINC
TROMETHAMINE TROMETAMOL MEGLUMINE ARGININE LYSINE
MONOHYDRATE DIHYDRATE TRIHYDRATE HEMIHYDRATE PENTAHYDRATE ANHYDROUS
""".split())

#: 劑型字，同樣只在字尾剝除。
FORM_WORDS: frozenset[str] = frozenset("""
SOLUTION SOLUTIONS INJECTION POWDER SUSPENSION SYRUP CREAM OINTMENT
GEL TABLET TABLETS CAPSULE CAPSULES CONCENTRATE
""".split())

#: 賦形劑：整個成分分量直接丟棄。前綴比對（OPADRY 有數十種商品名變體）。
EXCIPIENT_PREFIXES: tuple[str, ...] = (
    "CAPSULE SHELL", "OPADRY", "WATER PURIFIED", "PURIFIED WATER",
    "WATER FOR INJECTION", "EMPTY CAPSULE", "EMPTY HARD CAPSULE",
    "GELATIN CAPSULE SHELL", "PRINTING INK",
)

#: 剝完剩下這些就代表剝過頭了，保留原字串。
COUNTER_IONS: frozenset[str] = frozenset(
    "SODIUM POTASSIUM CALCIUM MAGNESIUM LITHIUM ZINC IRON AMMONIUM".split()
)

_PAREN_RE = re.compile(r"\([^()]*\)")
_PERCENT_RE = re.compile(r"^\s*\d+(?:\.\d+)?\s*%\s*")
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class MoietySet:
    """一張證的 moiety 判定結果。"""

    moieties: frozenset[str]
    raw: str
    dropped_excipients: tuple[str, ...] = ()

    @property
    def missing(self) -> bool:
        """成分資料缺漏：欄位為空，或正規化後不剩任何 moiety。

        這種列**必須現形**成「成分資料缺漏」，不能靜默消失——消失的列和
        不存在的列長得一模一樣。
        """
        return not self.moieties

    @property
    def is_combination(self) -> bool:
        return len(self.moieties) > 1

    def as_dict(self) -> dict:
        return {
            "raw": self.raw,
            "moieties": sorted(self.moieties),
            "dropped_excipients": list(self.dropped_excipients),
            "missing": self.missing,
            "is_combination": self.is_combination,
        }


def _is_excipient(text: str) -> bool:
    upper = text.upper()
    return any(upper.startswith(p) for p in EXCIPIENT_PREFIXES)


def normalize_component(component: str) -> str | None:
    """單一成分分量 -> moiety，賦形劑或空值回傳 None。

    >>> normalize_component('DASATINIB MONOHYDRATE')
    'DASATINIB'
    >>> normalize_component('ACETAMINOPHEN (EQ TO PARACETAMOL)')
    'ACETAMINOPHEN'
    >>> normalize_component('CAPSULE SHELL') is None
    True
    >>> normalize_component('SODIUM CHLORIDE')
    'SODIUM CHLORIDE'
    """
    if not component:
        return None
    text = component.strip()
    if _is_excipient(text):
        return None
    # 括號內容是換算說明（(eq to …) / (AS SULFATE)），不是成分。
    prev = None
    while prev != text:
        prev = text
        text = _PAREN_RE.sub(" ", text)
    text = _PERCENT_RE.sub("", text)
    text = _WS_RE.sub(" ", text).strip().upper()
    text = text.strip(" ,.;:-")
    if not text:
        return None
    if _is_excipient(text):
        return None

    tokens = text.split()
    while len(tokens) > 1 and tokens[-1] in (SALT_SUFFIXES | FORM_WORDS):
        candidate = tokens[:-1]
        if len(candidate) == 1 and candidate[0] in COUNTER_IONS:
            break  # SODIUM CHLORIDE / POTASSIUM PHOSPHATE：剝過頭了
        tokens = candidate
    out = " ".join(tokens).strip()
    return out or None


def moieties(active_ingredient: str | None) -> MoietySet:
    """許可證成分欄 -> MoietySet。"""
    raw = active_ingredient or ""
    found: set[str] = set()
    dropped: list[str] = []
    for part in raw.split(COMPONENT_SEP):
        part = part.strip()
        if not part:
            continue
        norm = normalize_component(part)
        if norm is None:
            dropped.append(part)
        else:
            found.add(norm)
    return MoietySet(frozenset(found), raw, tuple(dropped))


def first_appearance(moiety: str, baseline: Mapping[str, object]):
    """回傳這個 moiety 在 baseline 中最早出現的日期，沒有則 None。

    `baseline` 是必填的 moiety -> 最早日期 對照表，而且**必須以全部許可證
    （含已註銷）建立**。把基線限縮成現行證，會讓已註銷證上的老分子被判成新。
    """
    if baseline is None:
        raise TypeError(
            "baseline 為必填：moiety 首見必須有一個明確的基線，"
            "而且基線要包含已註銷的許可證。"
        )
    return baseline.get(moiety)


def is_first_appearance(
    moiety_set: Iterable[str], permit_date, baseline: Mapping[str, object]
) -> bool:
    """這張證是不是它任一**正規化 moiety 字串**在給定基線上的首見？

    命名刻意不叫 `is_new_drug()`：首見是關於**分子字串**的敘述，
    不是關於法規上「新藥」或「新成分新藥」的敘述。見 docs/01。
    """
    for m in moiety_set:
        earliest = first_appearance(m, baseline)
        if earliest is None or earliest >= permit_date:
            return True
    return False


def _main(argv: list[str]) -> int:
    as_json = "--json" in argv
    args = [a for a in argv if a != "--json"]
    if not args:
        print("usage: reference/tw_moiety.py [--json] '<成分字串>' [...]", file=sys.stderr)
        return 2
    for raw in args:
        result = moieties(raw)
        if as_json:
            print(json.dumps(result.as_dict(), ensure_ascii=False))
        else:
            print(f"{raw}\n  -> {sorted(result.moieties) or '(成分資料缺漏)'}"
                  + (f"   [丟棄賦形劑: {', '.join(result.dropped_excipients)}]"
                     if result.dropped_excipients else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
