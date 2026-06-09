"""
프랜차이즈 비율 + 최종분석 v2 결합 및 경쟁구조 유형 분류
입력: crawling/annual_franchise_ratio.csv, 행정동별_최종분석_v2.csv
출력: 행정동별_최종분석_v3.csv
"""

import pandas as pd

# ── 1. 데이터 로드 ─────────────────────────────────────────────────────────────
franchise_df = pd.read_csv("crawling/annual_franchise_ratio.csv", encoding="utf-8-sig")
v2_df        = pd.read_csv("행정동별_최종분석_v2.csv",            encoding="utf-8-sig")

# ── 3. 2024·2025 프랜차이즈 비율 평균 계산 ────────────────────────────────────
ratio_cols = [c for c in franchise_df.columns if c.endswith("년_프랜차이즈비율(%)")]
target_cols = [c for c in ratio_cols if c.startswith("2024") or c.startswith("2025")]

if not target_cols:
    raise ValueError(f"2024·2025 비율 컬럼 없음. 현재 컬럼: {ratio_cols}")

franchise_df["프랜차이즈비율_평균"] = franchise_df[target_cols].mean(axis=1).round(2)

# ── 4. 행정동·프랜차이즈비율_평균만 추출 ──────────────────────────────────────
franchise_slim = franchise_df[["행정동", "프랜차이즈비율_평균"]].copy()

# ── 5. v2와 행정동 기준 병합 ───────────────────────────────────────────────────
# 이름 정규화: 마침표(.) → 가운뎃점(·) 로 통일
def normalize_dong(name):
    if pd.isna(name):
        return name
    return str(name).replace(".", "·")

# v2 행정동명 정규화 키 컬럼 생성
v2_df["_행정동_key"] = v2_df["행정동명"].apply(normalize_dong)

# franchise 행정동 정규화 + 행정동 통합 수동 매핑
#   상일1동·상일2동 → 상일동 (크롤링 데이터에서 통합 표기)
DONG_ALIAS = {
    "상일1동": "상일동",
    "상일2동": "상일동",
    # 2023년 행정동 개편: 신설동+용두동 → 용신동
    # (04에서 코드 통합 후 행정동명도 용신동으로 바뀌므로 여기선 불필요하나 안전망으로 유지)
    "신설동": "용신동",
    "용두동": "용신동",
}
v2_df["_행정동_key"] = v2_df["행정동명"].apply(
    lambda x: normalize_dong(DONG_ALIAS.get(x, x))
)
franchise_slim["_행정동_key"] = franchise_slim["행정동"].apply(normalize_dong)

v3_df = v2_df.merge(
    franchise_slim[["_행정동_key", "프랜차이즈비율_평균"]],
    on="_행정동_key",
    how="left"
).drop(columns=["_행정동_key"])

print(f"병합 결과: {len(v3_df)}개 행정동")
missing = v3_df["프랜차이즈비율_평균"].isna().sum()
if missing:
    print(f"⚠ 프랜차이즈 비율 미매칭 행정동 (franchise 데이터 없음): {missing}개")
    print(v3_df[v3_df["프랜차이즈비율_평균"].isna()]["행정동명"].tolist())

# ── 6. 프랜차이즈 비율 분위수 (25% / 75%) ─────────────────────────────────────
q25 = v3_df["프랜차이즈비율_평균"].quantile(0.25)
q75 = v3_df["프랜차이즈비율_평균"].quantile(0.75)
print(f"\n프랜차이즈 비율 분위수 — Q25: {q25:.2f}%  Q75: {q75:.2f}%")

# ── 7. 프랜차이즈등급 생성 ─────────────────────────────────────────────────────
def franchise_grade(val):
    if pd.isna(val):
        return None
    if val >= q75:
        return "높음"
    elif val <= q25:
        return "낮음"
    else:
        return "보통"

v3_df["프랜차이즈등급"] = v3_df["프랜차이즈비율_평균"].apply(franchise_grade)

# ── HHI 분위수 (경쟁구조 판단용, 중앙값 기준 높/낮 이분) ─────────────────────
hhi_median = v3_df["HHI"].median()
print(f"HHI 중앙값: {hhi_median:.1f}")

def hhi_level(val):
    if pd.isna(val):
        return None
    return "높음" if val >= hhi_median else "낮음"

v3_df["HHI_수준"] = v3_df["HHI"].apply(hhi_level)

# ── 8·9. HHI_수준 × 프랜차이즈등급 → 경쟁구조유형 ────────────────────────────
#
# 프랜차이즈  │  높음              보통              낮음
# ─────────────┼──────────────────────────────────────────────
# HHI 높음    │  브랜드 경쟁형     브랜드 집중형     로컬 독점형
# HHI 낮음    │  브랜드 혼합형     분산 혼합형       분산 경쟁형
#
COMPETITION_MAP = {
    ("높음", "높음"): "브랜드 경쟁형",   # 특정 프랜차이즈 업종 집중 + 브랜드 밀도 高
    ("높음", "보통"): "브랜드 집중형",   # 업종 집중은 있으나 프랜차이즈 비율 중간
    ("높음", "낮음"): "로컬 독점형",     # 특정 업종 집중이나 독립 점포 위주
    ("낮음", "높음"): "브랜드 혼합형",   # 업종 분산 + 프랜차이즈 비율 高
    ("낮음", "보통"): "분산 혼합형",     # 업종 분산 + 프랜차이즈 비율 중간
    ("낮음", "낮음"): "분산 경쟁형",     # 업종 분산 + 독립 점포 위주
}

def competition_type(row):
    hhi_lv    = row["HHI_수준"]
    fr_grade  = row["프랜차이즈등급"]
    if pd.isna(hhi_lv) or pd.isna(fr_grade):
        return None
    return COMPETITION_MAP.get((hhi_lv, fr_grade))

v3_df["경쟁구조유형"] = v3_df.apply(competition_type, axis=1)

# ── 10. 최종 결과 저장 ─────────────────────────────────────────────────────────
col_order = [
    "행정동코드", "행정동명",
    "HHI", "평균폐업률",
    "대표업종", "대표업종_점유율", "과밀업종", "부족업종",
    "총_직장_인구_수", "총_상주인구_수", "직장상주비율", "상권타입", "HHI위험도",
    "프랜차이즈비율_평균", "프랜차이즈등급",
    "HHI_수준", "경쟁구조유형",
]
# 혹시 v2에 없는 컬럼 있을 경우 안전하게 필터
col_order = [c for c in col_order if c in v3_df.columns]
# HHI가 없는 행정동(신설동·용두동 등 데이터 공백)은 제거
before = len(v3_df)
v3_df = v3_df[v3_df["HHI"].notna()].copy()
dropped = before - len(v3_df)
if dropped:
    print(f"ℹ HHI 없는 행정동 {dropped}개 제거")

v3_df = v3_df[col_order].sort_values("HHI", ascending=False).reset_index(drop=True)

v3_df.to_csv("행정동별_최종분석_v3.csv", index=False, encoding="utf-8-sig")

# ── 요약 출력 ──────────────────────────────────────────────────────────────────
print("\n=== 프랜차이즈등급 분포 ===")
print(v3_df["프랜차이즈등급"].value_counts().to_string())

print("\n=== 경쟁구조유형 분포 ===")
print(v3_df["경쟁구조유형"].value_counts().to_string())

print("\n=== 상권타입 × 경쟁구조유형 ===")
if "상권타입" in v3_df.columns:
    print(v3_df.groupby(["상권타입", "경쟁구조유형"]).size().unstack(fill_value=0).to_string())

print("\n✔ 행정동별_최종분석_v3.csv 저장 완료")
