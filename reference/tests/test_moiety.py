"""成分字串 -> moiety。負控在於「不該剝的不剝」與「清單沒收錄的會漏」。"""

from __future__ import annotations

from datetime import date

import pytest

from tw_moiety import first_appearance, is_first_appearance, moieties, normalize_component


def test_every_fixture_ingredient_matches_expected(ingredient_rows):
    failures = []
    for row in ingredient_rows:
        got = sorted(moieties(row["active_ingredient"]).moieties)
        want = sorted(row["expected_moieties"])
        if got != want:
            failures.append(f"{row['active_ingredient']!r}\n    got={got}\n    want={want}")
    assert not failures, "\n".join(failures)


def test_positive_and_negative_control_pair(controls):
    """正控：DASATINIB 2008 首見。負控：同分子 2026 的水合物寫法不是首見。"""
    case = controls["moiety_first_appearance"]
    baseline = {"DASATINIB": date(2008, 3, 3)}

    pos = moieties(case["positive"]["active_ingredient"])
    assert pos.moieties == {"DASATINIB"}
    assert is_first_appearance(pos.moieties, date(2008, 3, 3), baseline) is True

    neg = moieties(case["negative"]["active_ingredient"])
    assert neg.moieties == {"DASATINIB"}, "水合物後綴必須剝掉，否則就變成新字串"
    assert is_first_appearance(neg.moieties, date(2026, 5, 29), baseline) is False


def test_baseline_must_include_revoked_permits(controls):
    """Remdesivir：2020 那張證已註銷。基線只收現行證，就會把 2023 判成首見。"""
    trap = controls["moiety_first_appearance"]["baseline_trap"]
    m = moieties(trap["active_ingredient"]).moieties
    issue = date(2023, 6, 7)

    current_only: dict = {}                                # 錯的基線
    all_permits = {"REMDESIVIR": date(2020, 6, 2)}         # 對的基線（含已註銷）

    assert is_first_appearance(m, issue, current_only) is True    # 誤判
    assert is_first_appearance(m, issue, all_permits) is False    # 正解


def test_baseline_is_a_required_argument():
    """不給基線就沒有首見可言，所以參數必填，且傳 None 要爆炸。"""
    with pytest.raises(TypeError):
        first_appearance("DASATINIB", None)
    with pytest.raises(TypeError):
        moieties("DASATINIB").moieties and first_appearance("DASATINIB", None)


def test_counter_ion_is_not_stripped():
    """負控：SODIUM / POTASSIUM 在字首是分子的一部分，不是鹽別後綴。"""
    assert normalize_component("SODIUM BICARBONATE") == "SODIUM BICARBONATE"
    assert normalize_component("POTASSIUM PHOSPHATE") == "POTASSIUM PHOSPHATE"


def test_salt_synonyms_collapse():
    """esylate 與 ethanesulfonate 是同一個鹽的兩種寫法。"""
    assert moieties("Nintedanib esylate").moieties == {"NINTEDANIB"}
    assert moieties("Nintedanib ethanesulfonate").moieties == {"NINTEDANIB"}


def test_excipient_is_dropped_and_recorded():
    result = moieties("CEVIMELINE HYDROCHLORIDE;;CAPSULE SHELL")
    assert result.moieties == {"CEVIMELINE"}
    assert "CAPSULE SHELL" in result.dropped_excipients


def test_missing_ingredient_surfaces_instead_of_disappearing():
    """成分資料缺漏必須現形。消失的列和不存在的列長得一模一樣。"""
    for raw in ("", None, "CAPSULE SHELL"):
        assert moieties(raw).missing is True


def test_closed_list_is_the_structural_limit(ingredient_rows):
    """本方法的極限：清單沒收錄的寫法會安靜地變成一個新 moiety。

    這不是可以靠寫得更仔細解決的缺陷，所以它必須有一個測試釘住，
    免得下一個人以為 moiety 首見是精確的。
    """
    row = next(r for r in ingredient_rows if r["origin"] == "synthetic")
    got = moieties(row["active_ingredient"]).moieties
    assert got == set(row["expected_moieties"])
    assert len(got) == 1 and "UNDECANOATE-X" in next(iter(got))


def test_combination_reports_every_component():
    result = moieties("NETARSUDIL MESYLATE;;LATANOPROST")
    assert result.moieties == {"NETARSUDIL", "LATANOPROST"}
    assert result.is_combination is True
    # 複方裡只要有一個成分是首見，整張證就會被旗標——這是已知的計數放大來源
    baseline = {"LATANOPROST": date(2002, 1, 1)}
    assert is_first_appearance(result.moieties, date(2026, 6, 8), baseline) is True
