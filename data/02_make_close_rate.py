"""
행정동별 평균 폐업률 계산 (2020~2025)
서울시 상권분석서비스(점포-행정동) 데이터 사용
대상 업종: 주요 음식업종 7종
출력: 행정동별_평균폐업률_2020_2025.csv
"""

import pandas as pd

RAW_DIR = "raw_data"
YEARS = range(2020, 2026)

TARGET_INDUSTRIES = [
    '일식음식점',
    '중식음식점',
    '치킨전문점',
    '커피-음료',
    '패스트푸드점',
    '한식음식점',
    '호프-간이주점',
]

all_close_rate = []

for year in YEARS:
    file_path = f"{RAW_DIR}/서울시_상권분석서비스(점포-행정동)_{year}년.csv"
    print(f"처리중: {year}")

    df = pd.read_csv(file_path, encoding='cp949')

    # 1분기 데이터만 사용
    df = df[df['기준_년분기_코드'].astype(str).str.endswith('1')].copy()
    df['년도'] = df['기준_년분기_코드'].astype(str).str[:4].astype(int)

    df = df[df['서비스_업종_코드_명'].isin(TARGET_INDUSTRIES)]
    df = df[['년도', '행정동_코드', '서비스_업종_코드_명', '폐업_률']]

    all_close_rate.append(df)

close_rate_df = pd.concat(all_close_rate, ignore_index=True)

mean_close_rate = (
    close_rate_df
    .groupby(['년도', '행정동_코드'])['폐업_률']
    .mean()
    .reset_index(name='평균폐업률')
    .rename(columns={'행정동_코드': '행정동코드'})
)

# 전체 추세 확인용 저장 (2020~2025)
mean_close_rate.to_csv("행정동별_평균폐업률_2020_2025.csv", index=False, encoding='utf-8-sig')

# 분석용: 2024~2025년만 필터링
mean_close_rate = mean_close_rate[mean_close_rate['년도'].isin([2024, 2025])]
mean_close_rate.to_csv("행정동별_평균폐업률_2024_2025.csv", index=False, encoding='utf-8-sig')

print(f"폐업률 계산 완료 (분석용 2024~2025): {mean_close_rate.shape}")
print(mean_close_rate.head())
