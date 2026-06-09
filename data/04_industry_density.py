"""
업종 점유율 순위, 대표 업종, 과밀/부족 업종 분석
입력: 행정동별_업종점유율_2020_2026.csv, 행정동별_HHI_폐업률_결합.csv
출력: 행정동별_최종분석.csv  — HHI, 폐업률, 대표업종, 점유율 순위 통합 테이블
"""

import pandas as pd

# --- 데이터 로드 ---
share_df = pd.read_csv("행정동별_업종점유율_2020_2026.csv", encoding='utf-8-sig')
hhi_close_df = pd.read_csv("행정동별_HHI_폐업률_결합.csv", encoding='utf-8-sig')

# 분석 기준 연도 (가장 최근)
TARGET_YEAR = share_df['년도'].max()
print(f"분석 기준 연도: {TARGET_YEAR}")

share_yr = share_df[share_df['년도'] == TARGET_YEAR].copy()

# --- 업종별 점유율 순위 (행정동 내) ---
share_yr['점유율순위'] = (
    share_yr
    .groupby(['행정동코드'])['점유율']
    .rank(ascending=False, method='min')
    .astype(int)
)

# --- 대표 업종 (점유율 1위) ---
top1 = (
    share_yr[share_yr['점유율순위'] == 1]
    [['행정동코드', '행정동명', '상권업종중분류명', '점유율']]
    .rename(columns={
        '상권업종중분류명': '대표업종',
        '점유율': '대표업종_점유율',
    })
)

# 동점 1위가 여럿이면 업체수 기준으로 하나만 선택
top1 = top1.merge(
    share_yr[['행정동코드', '상권업종중분류명', '업체수']].rename(
        columns={'상권업종중분류명': '대표업종'}
    ),
    on=['행정동코드', '대표업종'],
    how='left'
)
top1 = (
    top1.sort_values('업체수', ascending=False)
    .drop_duplicates(subset='행정동코드')
    .drop(columns='업체수')
)

# --- 전국(서울) 평균 점유율 (기준값) ---
seoul_avg = (
    share_yr
    .groupby('상권업종중분류명')['점유율']
    .mean()
    .rename('서울평균점유율')
)

# --- 행정동별 업종 점유율 피벗 ---
pivot = share_yr.pivot_table(
    index=['행정동코드', '행정동명'],
    columns='상권업종중분류명',
    values='점유율',
    aggfunc='sum',
    fill_value=0,
)
pivot.columns.name = None
pivot = pivot.reset_index()

# --- 과밀 업종 (서울 평균의 1.5배 초과) ---
industry_cols = [c for c in pivot.columns if c not in ('행정동코드', '행정동명')]
OVERCONC_THRESHOLD = 1.5

def get_overconc_industries(row):
    overcrowded = [
        ind for ind in industry_cols
        if ind in seoul_avg.index and row[ind] > seoul_avg[ind] * OVERCONC_THRESHOLD
    ]
    return ', '.join(overcrowded) if overcrowded else None

def get_scarce_industries(row):
    # 서울 평균의 50% 미만이면서 서울 평균 자체가 5% 이상인 업종
    scarce = [
        ind for ind in industry_cols
        if ind in seoul_avg.index
        and seoul_avg[ind] >= 0.05
        and row[ind] < seoul_avg[ind] * 0.5
    ]
    return ', '.join(scarce) if scarce else None

pivot['과밀업종'] = pivot.apply(get_overconc_industries, axis=1)
pivot['부족업종'] = pivot.apply(get_scarce_industries, axis=1)

# --- 행정동 개편 매핑: 소상공인 데이터에 구 코드가 남아있는 경우 신코드로 통일 ---
# 2023년 개편: 신설동(11230515) + 용두동(11230533) → 용신동(11230536)
DONG_RECODE = {
    11230515: 11230536,  # 신설동 → 용신동
    11230533: 11230536,  # 용두동 → 용신동
}
top1['행정동코드']  = top1['행정동코드'].replace(DONG_RECODE)
pivot['행정동코드'] = pivot['행정동코드'].replace(DONG_RECODE)

# 코드 변경으로 중복이 생긴 경우 (신설동·용두동이 모두 용신동으로 바뀐 경우) 첫 번째만 유지
top1  = top1.drop_duplicates(subset='행정동코드', keep='first')
pivot = pivot.drop_duplicates(subset='행정동코드', keep='first')

# --- 최종 테이블 결합 (2024~2025 평균) ---
hhi_yr = (
    hhi_close_df[hhi_close_df['년도'].isin([2024, 2025])]
    .groupby('행정동코드')[['HHI', '평균폐업률']]
    .mean()
    .reset_index()
)

final_df = (
    top1
    .merge(pivot[['행정동코드', '과밀업종', '부족업종']], on='행정동코드', how='left')
    .merge(hhi_yr[['행정동코드', 'HHI', '평균폐업률']], on='행정동코드', how='left')
)[['행정동코드', '행정동명', 'HHI', '평균폐업률', '대표업종', '대표업종_점유율', '과밀업종', '부족업종']]

final_df = final_df.sort_values('HHI', ascending=False).reset_index(drop=True)

final_df.to_csv("행정동별_최종분석.csv", index=False, encoding='utf-8-sig')

# --- 결과 출력 ---
print(f"\n총 행정동 수: {len(final_df)}")
print("\n=== HHI 상위 10개 행정동 ===")
print(final_df.head(10)[['행정동명', 'HHI', '평균폐업률', '대표업종', '대표업종_점유율', '과밀업종']].to_string(index=False))

print("\n=== 업종별 과밀 행정동 수 (Top 10) ===")
all_overcrowded = (
    final_df['과밀업종']
    .dropna()
    .str.split(', ')
    .explode()
    .value_counts()
    .head(10)
)
print(all_overcrowded)

print("\n=== 업종별 부족 행정동 수 (Top 10) ===")
all_scarce = (
    final_df['부족업종']
    .dropna()
    .str.split(', ')
    .explode()
    .value_counts()
    .head(10)
)
print(all_scarce)
