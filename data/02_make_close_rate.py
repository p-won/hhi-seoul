"""
행정동별 평균 폐업률 계산 (2020~2025)
서울시 상권분석서비스(점포-행정동) 데이터 사용
출력: 행정동별_평균폐업률_2020_2025.csv
출력: 행정동별_평균폐업률_2024_2025.csv  (03코드 이후 분석에 사용)
"""

import pandas as pd
import numpy as np

RAW_DIR = "raw_data"
YEARS = range(2020, 2026)

# 01코드(소상공인) 업종 분류와의 매핑은 추후 추가 예정
TARGET_INDUSTRIES = [
    '양식음식점',
    '제과점',
    '분식전문점',
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

    # 1분기 데이터만 사용 (01코드의 3월 스냅샷과 시점을 맞추기 위함)
    df = df[df['기준_년분기_코드'].astype(str).str.endswith('1')].copy()
    df['년도'] = df['기준_년분기_코드'].astype(str).str[:4].astype(int)

    df = df[df['서비스_업종_코드_명'].isin(TARGET_INDUSTRIES)]
    df = df[['년도', '행정동_코드', '서비스_업종_코드_명', '점포_수', '폐업_률']]

    # ── 행정동 개편: 구코드 → 신코드로 통일 ──────────────────────────────────
    # 일원2동(11680740) → 개포3동(11680675): 1:1 통합
    # 상일동(11740520) → 상일1동(11740525) + 상일2동(11740526): 1→2 분동
    #   분동의 경우 구코드 행의 폐업률을 두 신코드에 동일하게 복제
    DONG_RECODE = {11680740: 11680675}
    df['행정동_코드'] = df['행정동_코드'].replace(DONG_RECODE)

    # 상일동 분동 처리: 상일동 행을 상일1동·상일2동 행으로 복제
    sangil = df[df['행정동_코드'] == 11740520].copy()
    if not sangil.empty:
        sangil1 = sangil.copy(); sangil1['행정동_코드'] = 11740525
        sangil2 = sangil.copy(); sangil2['행정동_코드'] = 11740526
        df = pd.concat([df[df['행정동_코드'] != 11740520], sangil1, sangil2], ignore_index=True)
    # ──────────────────────────────────────────────────────────────────────────

    # 폐업률 100% 초과는 데이터 오류(점포수=0이거나 폐업수>점포수)로 NaN 처리
    # → groupby mean()에서 자동 제외되어 나머지 업종으로만 평균 계산
    invalid = df['폐업_률'] > 100
    if invalid.any():
        print(f"  [이상값] {year}년: 폐업률 100% 초과 {invalid.sum()}건 → NaN 처리")
        print(df[invalid][['행정동_코드', '서비스_업종_코드_명', '점포_수', '폐업_률']].to_string(index=False))
    df.loc[invalid, '폐업_률'] = np.nan

    all_close_rate.append(df)

close_rate_df = pd.concat(all_close_rate, ignore_index=True)

# 업종별 점포수를 가중치로 적용한 행정동별 평균 폐업률 계산
# 점포가 많은 업종의 폐업률이 더 많이 반영됨 (단순 평균 대비 현실 반영도 향상)
def weighted_mean_close_rate(g):
    valid = g.dropna(subset=['폐업_률'])
    if valid.empty or valid['점포_수'].sum() == 0:
        return np.nan
    return np.average(valid['폐업_률'], weights=valid['점포_수'])

mean_close_rate = (
    close_rate_df
    .groupby(['년도', '행정동_코드'])
    .apply(weighted_mean_close_rate, include_groups=False)
    .reset_index(name='평균폐업률')
    .rename(columns={'행정동_코드': '행정동코드'})
)

# 전체 추세 확인용 저장 (2020~2025)
mean_close_rate.to_csv("행정동별_평균폐업률_2020_2025.csv", index=False, encoding='utf-8-sig')

# 분석용: 최근 2년만 사용 (코로나 영향 기간 제외)
mean_close_rate_recent = mean_close_rate[mean_close_rate['년도'].isin([2024, 2025])]
mean_close_rate_recent.to_csv("행정동별_평균폐업률_2024_2025.csv", index=False, encoding='utf-8-sig')

print(f"\n폐업률 계산 완료 (분석용 2024~2025): {mean_close_rate_recent.shape}")
print(mean_close_rate_recent.head())
