"""公告標題 -> 許可證號。全部 fixture 逐筆對到期望集合。"""

from __future__ import annotations

import subprocess
import sys
import shutil
from pathlib import Path

import pytest

from tw_nme_titles import extract_permits, parse_title

REFERENCE = Path(__file__).resolve().parents[1]


def test_every_fixture_title_matches_expected(title_rows):
    """46 筆全部逐筆比對。抽樣通過不算數：陷阱就藏在剩下那幾筆。"""
    failures = []
    for row in title_rows:
        parsed = parse_title(row["title"])
        got = sorted(parsed.permits)
        want = sorted(row["expected"])
        if got != want:
            failures.append(f"{row['title']!r}\n    got={got}\n    want={want}")
        if row.get("expect_unresolved") and not parsed.unresolved:
            failures.append(f"{row['title']!r}\n    應回報無法解析，但沒有")
        if not row.get("expect_unresolved") and parsed.unresolved:
            failures.append(f"{row['title']!r}\n    不該有未解析註記：{parsed.unresolved}")
    assert not failures, "\n".join(failures)


def test_fixture_covers_every_measured_anomaly(title_rows):
    """對照組本身也要驗：樣本必須真的涵蓋每一種量測到的形態。"""
    reasons = " ".join(r["why"] for r in title_rows)
    for needed in ("短尾範圍", "波浪號", "短尾列舉", "斜線", "沒有「號」",
                   "字母開頭", "公司名", "兩個不同字別", "錯字"):
        assert needed in reasons, f"樣本缺少 {needed} 的案例"
    assert sum(1 for r in title_rows if r["origin"] == "real") >= 40


def test_multi_permit_titles_are_the_majority_of_the_loss(title_rows):
    """只取第一張證會漏掉多少——在樣本上重現母體的結論。"""
    real = [r for r in title_rows if r["origin"] == "real"]
    total = sum(len(r["expected"]) for r in real)
    first_only = sum(1 for r in real if r["expected"])
    assert total > first_only, "樣本必須含多證公告，否則這個測試沒有意義"


def test_greedy_cjk_would_swallow_the_company_name():
    """負控：貪婪的中文字元類會吃掉公司名，最長匹配不會。"""
    import re
    title = "台灣武田藥品工業股份有限公司衛部藥輸字第027623號「福星定膜衣錠20毫克」"
    greedy = re.search(r"([一-鿿]+)字第", title).group(1)
    assert greedy == "台灣武田藥品工業股份有限公司衛部藥輸"   # 錯誤作法抓到的東西
    assert extract_permits(title) == ["衛部藥輸字第027623號"]  # 正確作法


def test_product_name_digits_are_not_eaten_as_serials():
    """「可申達10、20毫克膜衣錠」的 10 和 20 不能被當成序號。"""
    title = "台灣拜耳股份有限公司 衛部藥輸字第028325、26號 「可申達10、20毫克膜衣錠」"
    assert extract_permits(title) == ["衛部藥輸字第028325號", "衛部藥輸字第028326號"]


def test_slash_inside_product_name_is_not_a_separator():
    title = "台灣默克股份有限公司 衛部菌疫輸字第001085號「百穩益注射劑20毫克/毫升 」"
    assert extract_permits(title) == ["衛部菌疫輸字第001085號"]


def test_serial_followed_by_ascii_is_still_extracted():
    """預防性守衛，不是觀察到的形態。

    「序號後面接英文品名」這個形態在 2026-08-05 的 206 則真實標題裡出現
    **0 次**（`M-29`：`第\\s*[0-9]{6}\\s*[A-Za-z]` 匹配 0/206）。0 是「沒觀察
    到」，不是「不可能」。之所以仍然守，是因為酬載規則若允許內部空白，產品名
    會被整段吃成序號；這個測試釘住那條規則。
    """
    title = "某某股份有限公司 衛部藥輸字第 027864 Testdrug 100mg 「測試錠」"
    assert extract_permits(title) == ["衛部藥輸字第027864號"]


def test_unresolvable_lic_type_is_reported_not_guessed():
    """來源錯字必須現形。猜成衛部藥輸剛好會對，但那是運氣不是方法。"""
    parsed = parse_title("台灣武田藥品工業股份有限公司 衛部藥字第027731號「癌能畢 膜衣錠90毫克」")
    assert parsed.permits == ()
    assert parsed.unresolved
    assert "不要猜" in parsed.unresolved[0]


@pytest.mark.parametrize("title", [
    "某某股份有限公司 衛部藥輸字第R00100-R00104號「測試針劑」",
    "某某股份有限公司 衛部藥輸字第027640-027900號「測試錠」",
    "某某股份有限公司 衛部藥輸字第0271234號「測試錠」",
])
def test_refuses_rather_than_guesses(title):
    parsed = parse_title(title)
    assert parsed.permits == ()
    assert parsed.unresolved


def test_expansion_is_a_hypothesis_not_a_conclusion():
    """本模組不連網也不查表，所以它的輸出是候選集合。

    這個測試釘住那個契約：一個語法完全合法、但完全虛構的許可證號，
    照樣會被展開出來。真正的檢定是「它存在於許可證表裡嗎」。
    """
    assert extract_permits("測試公司 衛部藥輸字第999998-999999號「不存在的藥」") == [
        "衛部藥輸字第999998號", "衛部藥輸字第999999號"]


def test_documented_copy_set_actually_runs(tmp_path):
    """README 說「要複製就複製這兩個檔」。這裡真的複製兩個檔並跑 CLI。

    只複製 tw_nme_titles.py 一個檔會 ModuleNotFoundError——那正是文件必須
    講清楚的事，所以順便把它也釘住。
    """
    for name in ("tw_nme_titles.py", "tw_permit_id.py"):
        shutil.copy(REFERENCE / name, tmp_path / name)
    title = "台灣禮來股份有限公司  衛部藥輸字第027640-027643號「捷癌寧膜衣錠」"
    proc = subprocess.run([sys.executable, "tw_nme_titles.py", title],
                          cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "衛部藥輸字第027643號" in proc.stdout

    (tmp_path / "tw_permit_id.py").unlink()
    lonely = subprocess.run([sys.executable, "tw_nme_titles.py", title],
                            cwd=tmp_path, capture_output=True, text=True)
    assert lonely.returncode != 0
    assert "tw_permit_id" in lonely.stderr


@pytest.mark.parametrize("module", ["tw_permit_id.py", "tw_restraint.py", "tw_moiety.py"])
def test_standalone_modules_really_stand_alone(tmp_path, module):
    """另外三個模組必須單獨複製就能跑。文件這樣寫，就要這樣測。"""
    shutil.copy(REFERENCE / module, tmp_path / module)
    sample = {
        "tw_permit_id.py": ["衛部藥輸字第R00108號"],
        "tw_restraint.py": ["02 輸 入", "07 新藥監視"],
        "tw_moiety.py": ["DASATINIB MONOHYDRATE"],
    }[module]
    proc = subprocess.run([sys.executable, module, *sample],
                          cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
