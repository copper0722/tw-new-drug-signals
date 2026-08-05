#!/usr/bin/env python3
"""restraintItemsCode -> 「這張證有沒有被列為新藥監視」的結構化判定。

這個模組獨立，不 import 任何兄弟檔。

## 為什麼要寫成程式

因為用子字串「監視」比對會靜默地多抓。食藥署的限制項目碼表（91 筆）裡，
名稱含「監視」的有 **8 個**：

    07 新藥監視    1K 安全監視    1L 監視中新藥    24 監視期滿學名藥
    25 監視中學名藥  26 監視期滿新藥  27 監視中藥品   28 監視期滿藥品

用子字串比對，這 8 個全部會被判成 true，而你的已知正控（帶 07 的真新藥）仍然
會通過——所以正控不會告訴你工具壞了。只有負控會。見 docs/07。

這 8 個碼是「**EXACT-07 比對器**的負控」，意思僅止於此。**它不表示帶那些碼的
藥不是新藥**：同一張碼表裡 `1L 監視中新藥`、`26 監視期滿新藥` 的名稱就含「新藥」。

`24` / `25` 尤其容易讀錯。它們是舊制的「監視藥品之學名藥」分類，回答的是
「申請這張學名藥時，該成分的第一張**新藥**還在不在監視期內」，據以決定要檢附
哪些臨床／BA-BE 資料；**不是**宣告這張學名藥自己落入辦法第 8 條的新藥監視義務。
它們仍然是「這張證不可能是該成分首見」的強反指標，理由是藥品查驗登記審查準則
第 4 條把學名藥定義為與國內已核准藥品同成分、同劑型、同劑量、同療效——但本 repo
沒有在母體規模上量測它們與其他碼的共現，所以是反指標，不是已證明的互斥。

## 語意（誰說的，分清楚）

碼表本身只給兩個欄位：`value` = `07`、`text` = `新藥監視`。食藥署沒有公開
一份「定義 07 這個碼」的文件。以下是**已查證的法源**，不是本 repo 的推論：

- 藥事法第 45 條第 1 項：「經核准製造或輸入之藥物，中央衛生主管機關得指定
  期間，監視其安全性。」——監視制度的授權來源。
- 藥品安全監視管理辦法（修正日期：民國 111 年 04 月 15 日）第 1 條：
  「本辦法依藥事法（以下簡稱本法）第四十五條第二項規定訂定之。」
- 同辦法第 2 條：「中央衛生主管機關依本法第四十五條第一項規定指定之期間，
  以藥品許可證有效期間為準。」
- 同辦法第 8 條：「藥商應自中央衛生主管機關核發**本法第七條新藥**藥品許可證
  之日（以下簡稱發證日）起五年內，向該主管機關繳交藥品安全性定期報告…」

三層關係要一起讀：授權在 §45；辦法依 §45 II 訂定；而辦法 §8 又把 §7 接了回來，
把新藥的定期報告義務明文綁在「本法第七條新藥」的許可證上。所以「新藥監視」是
**上市後安全監視**，不是上市前的審查途徑——但也不能說 §7 與監視無關。

至於藥事法第 7 條本身：它定義三類（新成分／新療效複方／新使用途徑），並要求
**經中央衛生主管機關審查認定**。它不建立 `07` 這個註記，也不產生可查詢的欄位。
反過來，帶 `07` 也不等於經審查認定為第 7 條新藥——那個身分來自審查，不來自碼。

本模組回傳的 `.interpretation` 字串已標明「本 repo 解讀」，因為那句話一旦被
引用到別的文件裡，讀者無法回頭確認哪部分是法條、哪部分是作者的讀法。
它刻意**不主張任何集合關係**（「07 是新成分的超集」之類），因為那需要 07 的
收錄準則（未公開）加上母體普查（未做）。`tests/test_restraint.py` 釘住這件事。

CLI:
    python3 reference/tw_restraint.py '02 輸 入' '07 新藥監視'
    python3 reference/tw_restraint.py --json '25 監視中學名藥'
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field

__all__ = [
    "NEW_DRUG_MONITORING_CODE",
    "MONITORING_FAMILY",
    "RestraintError",
    "NewDrugMonitoring",
    "restraint_token",
    "restraint_tokens",
    "new_drug_monitoring",
]

NEW_DRUG_MONITORING_CODE = "07"

#: 碼表中名稱含「監視」的全部 8 個碼。
#:
#: 除 07 以外的 7 個，是「**EXACT-07 比對器**的負控」——用來證明比對器沒有退化
#: 成子字串「監視」比對。這**不是**在說帶那些碼的藥不是新藥：`1L 監視中新藥`、
#: `26 監視期滿新藥` 的名稱本身就含「新藥」。見模組 docstring。
MONITORING_FAMILY: dict[str, str] = {
    "07": "新藥監視",
    "1K": "安全監視",
    "1L": "監視中新藥",
    "24": "監視期滿學名藥",
    "25": "監視中學名藥",
    "26": "監視期滿新藥",
    "27": "監視中藥品",
    "28": "監視期滿藥品",
}

_INTERPRETATION = (
    "本 repo 解讀：`07 新藥監視` 表示這張許可證被列入藥事法第 45 條的上市後"
    "安全監視；藥品安全監視管理辦法第 8 條把該監視的定期報告義務綁在「本法"
    "第七條新藥」的許可證上。食藥署未公開定義此碼的收錄準則，因此這是讀法，"
    "不是官方定義。已量測到的觀察範圍：一張兩個成分都不是第一次出現在許可證上的複方證"
    "（衛部藥輸字第029062號）帶 07，而一般學名藥不帶。到此為止——沒有收錄準則"
    "也沒有母體普查，就推不出集合關係；帶 07 也不等於經審查認定為第 7 條新藥。"
)


class RestraintError(ValueError):
    """restraintItemsCode 的形狀不是預期的樣子。"""


@dataclass(frozen=True)
class NewDrugMonitoring:
    """一張證的新藥監視判定結果。

    刻意**不回傳裸 bool**：呼叫端不應該拿到一個可以直接寫進報告的「是」。
    要布林值請讀 `.designated`，並且在寫出去的時候把 `.interpretation`
    一起帶著。

    `.designated` 的意思只有一個：**這張證的限制項目裡有 `07` 這個碼**。
    不要把它改寫成「這是新成分新藥」，也不要改寫成「這張證經審查認定為
    第 7 條新藥」——後者的來源是審查認定，不是這個欄位。
    """

    designated: bool
    matched_code: str | None
    all_codes: tuple[str, ...] = field(default=())
    monitoring_family_present: tuple[str, ...] = field(default=())
    interpretation: str = _INTERPRETATION

    def __bool__(self) -> bool:  # pragma: no cover - 故意讓誤用當場爆炸
        raise RestraintError(
            "NewDrugMonitoring 不可直接當布林值使用。請明確讀 .designated，"
            "並注意它的意思是「被列入新藥安全監視」，不是「這是新成分新藥」。"
        )

    def as_dict(self) -> dict:
        return {
            "designated": self.designated,
            "matched_code": self.matched_code,
            "all_codes": list(self.all_codes),
            "monitoring_family_present": list(self.monitoring_family_present),
            "interpretation": self.interpretation,
        }


def restraint_token(entry: str) -> str:
    """`'07 新藥監視'` -> `'07'`。取**碼**，不取名稱。

    entry 內含的空白可能是半形或全形 U+3000（`'02 輸 入'`），Python 的
    `str.split()` 兩者都吃。
    """
    if not isinstance(entry, str):
        raise RestraintError(f"限制項目必須是字串，收到 {type(entry).__name__}")
    parts = entry.split()
    if not parts:
        raise RestraintError("限制項目為空字串")
    return parts[0].strip().upper()


def restraint_tokens(codes) -> tuple[str, ...]:
    """把 API 回傳的 `restraintItemsCode` 陣列轉成純碼的 tuple。"""
    if codes is None:
        return ()
    if isinstance(codes, str):
        raise RestraintError(
            "restraintItemsCode 應是陣列。傳入單一字串通常表示你把整包 JSON "
            "當成字串處理了，那會讓下面的比對變成子字串比對。"
        )
    return tuple(restraint_token(c) for c in codes)


def new_drug_monitoring(codes) -> NewDrugMonitoring:
    """判定一張證是否帶 `07 新藥監視`。

    >>> new_drug_monitoring(['02 輸 入', '07 新藥監視']).designated
    True
    >>> new_drug_monitoring(['25 監視中學名藥']).designated
    False
    """
    tokens = restraint_tokens(codes)
    family = tuple(t for t in tokens if t in MONITORING_FAMILY)
    matched = NEW_DRUG_MONITORING_CODE if NEW_DRUG_MONITORING_CODE in tokens else None
    return NewDrugMonitoring(
        designated=matched is not None,
        matched_code=matched,
        all_codes=tokens,
        monitoring_family_present=family,
    )


def _main(argv: list[str]) -> int:
    as_json = "--json" in argv
    entries = [a for a in argv if a != "--json"]
    if not entries:
        print("usage: reference/tw_restraint.py [--json] '<限制項目>' [...]", file=sys.stderr)
        return 2
    result = new_drug_monitoring(entries)
    if as_json:
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=1))
    else:
        print(f"designated\t{result.designated}")
        print(f"matched_code\t{result.matched_code}")
        print(f"monitoring_family\t{','.join(result.monitoring_family_present) or '-'}")
        print(f"interpretation\t{result.interpretation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
