"""
서울시 외식업 프랜차이즈 비율 수집기 (행정동 단위)
- 기간: 2024년 1분기 ~ 2025년 4분기
- 조건: 외식업 / 전체 / 조회분기=동분기
- 단위: 행정동 (자치구 + 버튼 클릭해 펼침)

실행: python seoul_franchise_scraper.py
"""

import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://golmok.seoul.go.kr/stateArea.do"

# 기준년 2025로 검색 → 컬럼: [2023, 2024, 2025]
SEARCH_PLAN = [
    ("2025", "1", ["2023", "2024", "2025"]),
    ("2025", "2", ["2023", "2024", "2025"]),
    ("2025", "3", ["2023", "2024", "2025"]),
    ("2025", "4", ["2023", "2024", "2025"]),
]
TARGET_YEARS = {"2024", "2025"}


def get_driver():
    options = Options()
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )


def wait_click(driver, by, sel, timeout=15):
    el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, sel)))
    driver.execute_script("arguments[0].click();", el)


def wait_select(driver, el_id, value, timeout=15):
    def option_available(d):
        try:
            opts = [o.get_attribute("value")
                    for o in Select(d.find_element(By.ID, el_id)).options]
            return value in opts
        except Exception:
            return False
    WebDriverWait(driver, timeout).until(option_available)
    Select(driver.find_element(By.ID, el_id)).select_by_value(value)


def get_first_cell_text(driver):
    """현재 테이블 첫 번째 자치구 행 td[2] 값 반환 (변경 감지용)"""
    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        space = soup.find(id="tableSpace")
        if not space:
            return ""
        rows = space.find_all("tr", attrs={"data-tt-parent-id": "1"})
        if not rows:
            return ""
        cells = rows[0].find_all("td")
        return cells[2].get_text(strip=True) if len(cells) > 2 else ""
    except Exception:
        return ""


def wait_table_refresh(driver, prev_value, timeout=30):
    def is_refreshed(d):
        try:
            space = d.find_element(By.ID, "tableSpace")
            rows = space.find_elements(By.XPATH, ".//tr[@data-tt-parent-id='1']")
            if not rows:
                return False
            cells = rows[0].find_elements(By.TAG_NAME, "td")
            if len(cells) < 3:
                return False
            current = cells[2].text.strip().replace(",", "")
            prev = prev_value.replace(",", "")
            return current != prev and current != ""
        except Exception:
            return False
    WebDriverWait(driver, timeout).until(is_refreshed)


def wait_table_load(driver, timeout=30):
    def has_rows(d):
        try:
            space = d.find_element(By.ID, "tableSpace")
            return len(space.find_elements(
                By.XPATH, ".//tr[@data-tt-parent-id='1']")) > 0
        except Exception:
            return False
    WebDriverWait(driver, timeout).until(has_rows)


def expand_all_districts(driver, timeout=30):
    """모든 자치구의 + 버튼을 클릭해 행정동 목록 펼치기"""
    expanders = driver.find_elements(
        By.XPATH,
        "//*[@id='tableSpace']//tr[@data-tt-parent-id='1']//span[contains(@class,'expander')]"
    )
    if not expanders:
        # expander 클래스명이 다를 경우 대비
        expanders = driver.find_elements(
            By.XPATH,
            "//*[@id='tableSpace']//tr[@data-tt-parent-id='1']//td[1]//*[self::span or self::a]"
        )
    print(f"    자치구 수: {len(expanders)}")

    for exp in expanders:
        try:
            driver.execute_script("arguments[0].click();", exp)
            time.sleep(0.2)
        except Exception:
            pass

    # 동 행이 나타날 때까지 대기
    WebDriverWait(driver, timeout).until(
        lambda d: len(d.find_elements(
            By.XPATH,
            "//*[@id='tableSpace']//tr[@data-tt-parent-id and @data-tt-parent-id!='1']"
        )) > 0
    )
    time.sleep(0.5)


def parse(driver, quarter, years):
    """
    동분기 컬럼 구조:
      td[0]=지역명, td[1]=업종
      td[2,3,4] = 기준-2년 (전체, 프랜차이즈, 일반)
      td[5,6,7] = 기준-1년
      td[8,9,10]= 기준년
    years = [기준-2년, 기준-1년, 기준년]
    """
    soup = BeautifulSoup(driver.page_source, "html.parser")
    space = soup.find(id="tableSpace")
    if not space:
        print("    ❌ tableSpace 없음")
        return []

    # 자치구 행: data-tt-parent-id="1" → {tt-id: 자치구명} 매핑
    district_rows = space.find_all("tr", attrs={"data-tt-parent-id": "1"})
    id_to_district = {}
    for row in district_rows:
        tt_id = row.get("data-tt-id", "")
        cells = row.find_all("td")
        if not cells:
            continue
        addr = cells[0]
        for tag in addr.find_all(["span", "a"]):
            tag.decompose()
        name = addr.get_text(strip=True)
        if name and "서울시" not in name:
            id_to_district[tt_id] = name

    # 동 행: parent-id가 자치구 tt-id인 것
    all_rows = space.find_all("tr", attrs={"data-tt-parent-id": True})
    dong_rows = [
        r for r in all_rows
        if r.get("data-tt-parent-id") in id_to_district
    ]

    if not dong_rows:
        print("    ❌ 동 행 없음 (펼치기 실패 가능성)")
        return []

    col_map = {
        years[0]: (2, 3),
        years[1]: (5, 6),
        years[2]: (8, 9),
    }

    def to_int(cell):
        t = cell.get_text(strip=True).replace(",", "")
        return int(t) if t.isdigit() else 0

    records = []
    for row in dong_rows:
        parent_id = row.get("data-tt-parent-id", "")
        district = id_to_district.get(parent_id, "")
        cells = row.find_all("td")
        if len(cells) < 11:
            continue
        addr = cells[0]
        for tag in addr.find_all(["span", "a"]):
            tag.decompose()
        dong = addr.get_text(strip=True)
        if not dong:
            continue

        for year, (ci_t, ci_f) in col_map.items():
            if year not in TARGET_YEARS:
                continue
            total     = to_int(cells[ci_t])
            franchise = to_int(cells[ci_f])
            records.append({
                "연도":               year,
                "분기":               f"{quarter}분기",
                "자치구":             district,
                "행정동":             dong,
                "전체_점포수":        total,
                "프랜차이즈_점포수":  franchise,
                "프랜차이즈_비율(%)": round(franchise / total * 100, 2) if total else 0,
            })
    return records


def main():
    driver = get_driver()
    all_records = []
    total_searches = len(SEARCH_PLAN)

    try:
        t0 = time.time()

        driver.get(URL)
        wait_click(driver, By.CSS_SELECTOR, "button.store")
        print(f"✔ 점포수 탭 클릭 ({time.time()-t0:.1f}s)")

        wait_select(driver, "induL", "CS100000")
        wait_select(driver, "induM", "all")
        wait_select(driver, "selectQuCondition", "sameQu")
        print(f"✔ 고정 조건 설정 완료")

        for i, (base_year, quarter, years) in enumerate(SEARCH_PLAN):
            target = [y for y in years if y in TARGET_YEARS]
            print(f"\n  [{i+1}/{total_searches}] 기준 {base_year}년 {quarter}분기 → 수집: {target}")

            prev_val = get_first_cell_text(driver) if i > 0 else "0"

            wait_select(driver, "selectYear", base_year)
            wait_select(driver, "selectQu", quarter)
            wait_click(driver, By.ID, "presentSearch")

            if i == 0:
                wait_table_load(driver)
            else:
                wait_table_refresh(driver, prev_val)

            print(f"    ✔ 테이블 갱신 확인 ({time.time()-t0:.1f}s)")

            expand_all_districts(driver)
            print(f"    ✔ 동 목록 펼침 완료 ({time.time()-t0:.1f}s)")

            records = parse(driver, quarter, years)
            if records:
                all_records.extend(records)
                for year in target:
                    cnt = sum(1 for r in records if r["연도"] == year)
                    print(f"    ✔ {year}년 {quarter}분기: {cnt}개 행정동")
            else:
                print(f"    ❌ 파싱 실패")

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("page_source.html 저장")

    finally:
        driver.quit()

    if not all_records:
        print("\n⚠ 수집된 데이터 없음")
        return

    df = pd.DataFrame(all_records)
    df = df.sort_values(["연도", "분기", "자치구", "행정동"]).reset_index(drop=True)

    print(f"\n✅ 총 {len(df)}개 레코드")
    summary = df.groupby(["연도", "분기"])["행정동"].count().reset_index()
    summary.columns = ["연도", "분기", "행정동수"]
    print(summary.to_string(index=False))

    df.to_csv("seoul_franchise_ratio.csv", index=False, encoding="utf-8-sig")
    print("\n✔ seoul_franchise_ratio.csv 저장 완료")

if __name__ == "__main__":
    main()
