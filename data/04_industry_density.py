"""
업종 점유율 순위, 대표 업종, 과밀/부족 업종 분석
입력: 행정동별_업종점유율_2020_2025.csv, 행정동별_HHI_폐업률_결합.csv
출력: 행정동별_최종분석.csv  — HHI, 폐업률, 대표업종, 점유율 순위 통합 테이블
"""

import pandas as pd

# --- 데이터 로드 ---
share_df = pd.read_csv("행정동별_업종점유율_2020_2025.csv", encoding='utf-8-sig')
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
    [['행정동코드', '행정동명', '통합카테고리', '점유율']]
    .rename(columns={
        '통합카테고리': '대표업종',
        '점유율': '대표업종_점유율',
    })
)

# 동점 1위가 여럿이면 업체수가 많은 업종 하나만 선택
top1 = top1.merge(
    share_yr[['행정동코드', '통합카테고리', '업체수']].rename(
        columns={'통합카테고리': '대표업종'}
    ),
    on=['행정동코드', '대표업종'],
    how='left'
)
top1 = (
    top1.sort_values('업체수', ascending=False)
    .drop_duplicates(subset='행정동코드')
    .drop(columns='업체수')
)

# --- 서울 전체 평균 점유율 (과밀/부족 기준값) ---
seoul_avg = (
    share_yr
    .groupby('통합카테고리')['점유율']
    .mean()
    .rename('서울평균점유율')
)

# --- 행정동별 업종 점유율 피벗 ---
pivot = share_yr.pivot_table(
    index=['행정동코드', '행정동명'],
    columns='통합카테고리',
    values='점유율',
    aggfunc='sum',
    fill_value=0,
)
pivot.columns.name = None
pivot = pivot.reset_index()

# --- 과밀/부족 업종 판별 ---
industry_cols = [c for c in pivot.columns if c not in ('행정동코드', '행정동명')]

# 과밀: 해당 동 점유율이 서울 평균의 1.5배 초과 (약 상위 10%)
OVERCONC_THRESHOLD = 1.5

# 부족: 서울 평균의 0.5배 미만, 단 서울 평균이 5% 이상인 주요 업종만 대상
#   (서울 평균 5% 이상 업종: 한식·커피·호프·분식·제과·치킨 6개)
SCARCE_THRESHOLD = 0.5
SCARCE_MIN_AVG = 0.05

def get_overconc_industries(row):
    overcrowded = [
        ind for ind in industry_cols
        if ind in seoul_avg.index and row[ind] > seoul_avg[ind] * OVERCONC_THRESHOLD
    ]
    return ', '.join(overcrowded) if overcrowded else None

def get_scarce_industries(row):
    scarce = [
        ind for ind in industry_cols
        if ind in seoul_avg.index
        and seoul_avg[ind] >= SCARCE_MIN_AVG
        and row[ind] < seoul_avg[ind] * SCARCE_THRESHOLD
    ]
    return ', '.join(scarce) if scarce else None

pivot['과밀업종'] = pivot.apply(get_overconc_industries, axis=1)
pivot['부족업종'] = pivot.apply(get_scarce_industries, axis=1)

# --- 최종 테이블 결합 ---
# HHI·폐업률은 행정동별_HHI_폐업률_결합.csv의 2024~2025 평균 사용
# 행정동 개편(용신동·개포3동·상일1동·상일2동)은 01·02코드에서 이미 통일 처리됨
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
