"""
행정동별 음식업종 HHI 계산 (2020~2026)
소상공인시장진흥공단 상가(상권)정보 데이터 사용
출력: 행정동별_HHI_2020_2026.csv
출력: 행정동별_업종점유율_2020_2026.csv  (04_industry_density.py 에서 사용)
"""

import pandas as pd

RAW_DIR = "raw_data"
YEARS = range(2020, 2027)

all_hhi = []
all_industry_share = []

for year in YEARS:
    file_path = f"{RAW_DIR}/소상공인시장진흥공단_상가(상권)정보_서울_{year}03.csv"
    print(f"처리중: {year}")

    df = pd.read_csv(file_path, encoding='utf-8')

    food_df = df[df['상권업종대분류명'] == '음식'][
        ['상호명', '상권업종중분류명', '행정동코드', '행정동명']
    ].copy()
    food_df['년도'] = year

    industry_count = (
        food_df
        .groupby(['년도', '행정동코드', '행정동명', '상권업종중분류명'])
        .size()
        .reset_index(name='업체수')
    )

    total_count = (
        food_df
        .groupby(['년도', '행정동코드', '행정동명'])
        .size()
        .reset_index(name='전체업체수')
    )

    industry_share = industry_count.merge(
        total_count, on=['년도', '행정동코드', '행정동명'], how='left'
    )
    industry_share['점유율'] = industry_share['업체수'] / industry_share['전체업체수']
    industry_share['점유율제곱'] = (industry_share['점유율'] ** 2) * 10000

    hhi_df = (
        industry_share
        .groupby(['년도', '행정동코드', '행정동명'])['점유율제곱']
        .sum()
        .reset_index(name='HHI')
    )

    all_hhi.append(hhi_df)
    all_industry_share.append(industry_share)

final_hhi = pd.concat(all_hhi, ignore_index=True)
final_industry_share = pd.concat(all_industry_share, ignore_index=True)

final_hhi.to_csv("행정동별_HHI_2020_2026.csv", index=False, encoding='utf-8-sig')
final_industry_share.to_csv("행정동별_업종점유율_2020_2026.csv", index=False, encoding='utf-8-sig')

print(f"HHI 계산 완료: {final_hhi.shape}")
print(final_hhi.head())
