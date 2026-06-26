"""
행정동별 상권 타입 분류 (오피스형 / 주거형 / 혼합형)
직장인구 / 상주인구 비율 기반

입력: raw_data/worker-dong.csv, raw_data/resident-dong.csv
출력: 행정동별_상권타입.csv
      행정동별_최종분석_v2.csv  — 기존 최종분석 + 상권타입 결합
"""

import pandas as pd

RAW_DIR = "raw_data"

# 분류 기준 (직장인구 / 상주인구 비율)
# 1.0: 직장인구 ≥ 상주인구 → 명확한 의미선, 분포상 자연스러운 변곡점
# 0.2: 분포상 완만해지는 지점, 이하는 순수 주거 성격
OFFICE_THRESHOLD = 1.0
RESIDENTIAL_THRESHOLD = 0.2

# --- 1분기 데이터만 사용 (HHI 기준과 통일) ---
def load_q1(path, encoding='utf-8'):
    df = pd.read_csv(path, encoding=encoding)
    df = df[df['기준_년분기_코드'].astype(str).str.endswith('1')].copy()
    df['년도'] = df['기준_년분기_코드'].astype(str).str[:4].astype(int)
    return df

worker = load_q1(f"{RAW_DIR}/worker-dong.csv")
resident = load_q1(f"{RAW_DIR}/resident-dong.csv")

# 2026 데이터 제외 (프로젝트 전체 기준 통일)
worker = worker[worker['년도'] <= 2025]
resident = resident[resident['년도'] <= 2025]

# 필요한 컬럼만
worker = worker[['년도', '행정동_코드', '행정동_코드_명', '총_직장_인구_수']]
resident = resident[['년도', '행정동_코드', '총_상주인구_수']]

# --- 결합 ---
pop_df = worker.merge(resident, on=['년도', '행정동_코드'], how='inner')

# 상주인구 0인 행정동 제외 (비정상 데이터)
pop_df = pop_df[pop_df['총_상주인구_수'] > 0].copy()

# --- 직장/상주 비율 계산 ---
pop_df['직장상주비율'] = pop_df['총_직장_인구_수'] / pop_df['총_상주인구_수']

# --- 상권 타입 분류 ---
def classify_type(ratio):
    if ratio >= OFFICE_THRESHOLD:
        return '오피스형'
    elif ratio < RESIDENTIAL_THRESHOLD:
        return '주거형'
    else:
        return '혼합형'

pop_df['상권타입'] = pop_df['직장상주비율'].apply(classify_type)

# --- 출력 ---
result = pop_df[[
    '년도', '행정동_코드', '행정동_코드_명',
    '총_직장_인구_수', '총_상주인구_수', '직장상주비율', '상권타입'
]].rename(columns={
    '행정동_코드': '행정동코드',
    '행정동_코드_명': '행정동명',
})

result.to_csv("행정동별_상권타입.csv", index=False, encoding='utf-8-sig')

print(f"처리 완료: {result.shape}")
print("\n=== 상권 타입 분포 (연도별) ===")
print(result.groupby(['년도', '상권타입']).size().unstack(fill_value=0))

# --- 최종분석 테이블과 결합 ---
try:
    final_df = pd.read_csv("행정동별_최종분석.csv", encoding='utf-8-sig')

    # 최신 연도 상권타입만 결합
    latest_year = result['년도'].max()
    latest_type = result[result['년도'] == latest_year][
        ['행정동코드', '총_직장_인구_수', '총_상주인구_수', '직장상주비율', '상권타입']
    ]

    final_v2 = final_df.merge(latest_type, on='행정동코드', how='left')

    # 상권타입별 HHI 위험도
    # HHI 분포 기준 (2024~2025 평균): 평균 1976, 중앙값 1948, 75%ile 2159, 90%ile 2350
    # 오피스형: 점심 수요가 있어 업종 집중도가 높아도 버틸 여지 있음
    # 주거형: 저녁 경쟁 구도라 집중도 높으면 위험
    # 혼합형: 중간
    HHI_HIGH = 2350   # 상위 10% 기준
    HHI_MID  = 2159   # 상위 25% 기준

    def hhi_risk(row):
        if pd.isna(row.get('상권타입')) or pd.isna(row.get('HHI')):
            return None
        hhi = row['HHI']
        t = row['상권타입']
        if t == '오피스형':
            if hhi >= HHI_HIGH:
                return '주의 (오피스형·고집중)'
            else:
                return '안전 (오피스형·점심수요 흡수)'
        elif t == '주거형':
            if hhi >= HHI_HIGH:
                return '위험 (주거형·저녁경쟁 포화)'
            elif hhi >= HHI_MID:
                return '주의 (주거형·중간집중)'
            else:
                return '안전 (주거형·분산)'
        else:  # 혼합형
            if hhi >= HHI_HIGH:
                return '주의 (혼합형·고집중)'
            else:
                return '보통 (혼합형)'

    if 'HHI' in final_v2.columns and '상권타입' in final_v2.columns:
        final_v2['HHI위험도'] = final_v2.apply(hhi_risk, axis=1)

    final_v2.to_csv("행정동별_최종분석_v2.csv", index=False, encoding='utf-8-sig')
    print(f"\n최종분석 v2 저장 완료: {final_v2.shape}")
    print("\n=== 상권타입 × HHI위험도 분포 ===")
    if 'HHI위험도' in final_v2.columns:
        print(final_v2.groupby(['상권타입', 'HHI위험도']).size().to_string())

except FileNotFoundError:
    print("\n행정동별_최종분석.csv 없음 — 04_industry_density.py 먼저 실행하세요.")
