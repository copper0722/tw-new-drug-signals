"""restraintItemsCode 判定。每個工具要兩個控制，這裡的負控才是重點。"""

from __future__ import annotations

import pytest

from tw_restraint import (
    MONITORING_FAMILY,
    NEW_DRUG_MONITORING_CODE,
    RestraintError,
    new_drug_monitoring,
    restraint_token,
)


def test_monitoring_family_matches_authority_snapshot(restraint_codes):
    """模組裡的 8 個監視碼必須和碼表快照一致——負控清單不能自己編。"""
    snapshot = {c["code"]: c["name"] for c in restraint_codes["codes"]
                if "監視" in c["name"]}
    assert snapshot == MONITORING_FAMILY
    assert len(restraint_codes["codes"]) == 91


def test_positive_control(controls):
    case = controls["restraint_07"]["positive"]
    result = new_drug_monitoring(case["restraintItemsCode"])
    assert result.designated is True
    assert result.matched_code == NEW_DRUG_MONITORING_CODE


def test_negative_control_generic_drug(controls):
    """最容易被誤判為正的那一族：一張只帶「01 國 產」的學名藥證。"""
    case = controls["restraint_07"]["negative"]
    result = new_drug_monitoring(case["restraintItemsCode"])
    assert result.designated is False
    assert result.matched_code is None
    assert result.monitoring_family_present == ()


def test_substring_match_would_have_passed_the_positive_control(controls):
    """這是本檔最重要的一個測試。

    子字串「監視」的比對器，在正控上會完美通過——所以正控**無法**偵測它抓太多。
    只有負控看得見。這裡把兩件事一起斷言：正確的 token 比對判 false，
    而錯誤的子字串比對會判 true。
    """
    trap = controls["restraint_07"]["negative_substring_trap"]
    entries = trap["restraintItemsCode"]

    assert new_drug_monitoring(entries).designated is False          # 正確作法
    assert any("監視" in e for e in entries)                          # 錯誤作法會中

    positive = controls["restraint_07"]["positive"]["restraintItemsCode"]
    assert any("監視" in e for e in positive)                         # 正控兩種作法都過


@pytest.mark.parametrize("code", sorted(set(MONITORING_FAMILY) - {"07"}))
def test_every_other_monitoring_code_is_negative(code):
    result = new_drug_monitoring([f"{code} {MONITORING_FAMILY[code]}"])
    assert result.designated is False
    assert result.monitoring_family_present == (code,)


def test_token_extraction_handles_ideographic_space():
    """'02 輸 入' 的空白是全形 U+3000。"""
    assert restraint_token("02　輸　入") == "02"
    assert restraint_token("07 新藥監視") == "07"


def test_result_cannot_be_used_as_a_bool(controls):
    """`if result:` 應該當場爆炸，而不是永遠為真。"""
    result = new_drug_monitoring(controls["restraint_07"]["negative"]["restraintItemsCode"])
    with pytest.raises(RestraintError):
        bool(result)


def test_meaning_is_attributed_not_asserted(controls):
    """語意字串會被引用到別的文件裡，所以它必須自帶「這是解讀」的標記。"""
    result = new_drug_monitoring(controls["restraint_07"]["positive"]["restraintItemsCode"])
    assert result.interpretation.startswith("本 repo 解讀：")
    assert "第 45 條" in result.interpretation
    assert "未公開定義此碼" in result.interpretation
    # 絕不可以出現的字：把 07 直接等同於新成分新藥。
    # 早期版本寫成 `.replace("不是官方定義", "")` 再檢查，那個 replace 是空操作
    # ——被拿掉的字串裡沒有「新成分新藥」——但它讀起來像一條有意義的豁免。
    # 一個什麼都沒擋的豁免比沒有豁免更糟：它讓下一個讀者以為這裡放行過什麼。
    assert "新成分新藥" not in result.interpretation


def test_interpretation_claims_no_set_relation(controls):
    """這個字串會旅行到別的文件裡，所以已撤回的主張要釘死在外面。

    「07 是新成分的超集」需要兩樣本 repo 沒有的東西：食藥署未公開的 07 收錄
    準則，以及母體普查。「永久戳記」需要對同一張證做縱向取樣，也沒做過。
    兩句話都撤回了，這個測試防止它們被寫回來。
    """
    text = new_drug_monitoring(
        controls["restraint_07"]["positive"]["restraintItemsCode"]
    ).interpretation
    for retracted in ("超集", "superset", "子集", "永久", "戳記"):
        assert retracted not in text, f"已撤回的主張又出現了：{retracted}"


def test_passing_a_string_instead_of_a_list_raises():
    """把整包 JSON 當字串傳進來，會讓比對悄悄退化成子字串比對。"""
    with pytest.raises(RestraintError):
        new_drug_monitoring("['02 輸 入', '07 新藥監視']")
