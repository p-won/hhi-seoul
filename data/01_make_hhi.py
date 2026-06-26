"""
행정동별 음식업종 HHI 계산 (2020~2025)
소상공인시장진흥공단 상가(상권)정보 데이터 사용
출력: 행정동별_HHI_2020_2025.csv
출력: 행정동별_업종점유율_2020_2025.csv  (04_industry_density.py 에서 사용)

[통합 카테고리 기준]
소상공인 중분류/소분류 → 서울시 상권분석서비스 업종명과 통일
기타 간이 중분류는 소분류에 따라 세분화하여 매핑
"""

import pandas as pd

RAW_DIR = "raw_data"
# 2026 데이터는 행정동 코드 오염(용신동→신설동+용두동 역전현상) 확인으로 제외
YEARS = range(2020, 2026)

# ── 통합 카테고리 매핑 ────────────────────────────────────────────────────────
# 키: (상권업종중분류명, 상권업종소분류명)
# 값: 통합카테고리 (02코드 서울시 상권분석 업종명과 통일)
# 중분류만으로 결정되는 업종은 소분류 자리에 None
CATEGORY_MAP = {
    # 중분류로 바로 결정
    ('한식',        None): '한식음식점',
    ('서양식',      None): '양식음식점',
    ('일식',        None): '일식음식점',
    ('중식',        None): '중식음식점',
    ('주점',        None): '호프-간이주점',
    ('비알코올 ',   None): '커피-음료',   # 원본에 후행 공백 있음

    # 기타 간이: 소분류로 세분화
    ('기타 간이', '치킨'):                   '치킨전문점',
    ('기타 간이', '버거'):                   '패스트푸드점',
    ('기타 간이', '피자'):                   '패스트푸드점',
    ('기타 간이', '빵/도넛'):                '제과점',
    ('기타 간이', '아이스크림/빙수'):         '제과점',
    ('기타 간이', '토스트/샌드위치/샐러드'):  '제과점',
    ('기타 간이', '김밥/만두/분식'):          '분식전문점',
    ('기타 간이', '그 외 기타 간이 음식점'):  '기타',
    ('기타 간이', '떡/한과'):                '기타',

    # 기타로 묶이는 중분류
    ('구내식당·뷔페', None): '기타',
    ('동남아시아',   None): '기타',
    ('기타 외국',   None): '기타',
}

def assign_category(mid, sub):
    """중분류+소분류 → 통합카테고리. 매핑 없으면 None 반환."""
    # 소분류 기준 매핑 먼저 시도 (기타 간이 세분화)
    if (mid, sub) in CATEGORY_MAP:
        return CATEGORY_MAP[(mid, sub)]
    # 중분류만으로 결정되는 경우
    if (mid, None) in CATEGORY_MAP:
        return CATEGORY_MAP[(mid, None)]
    return None
# ─────────────────────────────────────────────────────────────────────────────

all_hhi = []
all_industry_share = []

for year in YEARS:
    file_path = f"{RAW_DIR}/소상공인시장진흥공단_상가(상권)정보_서울_{year}03.csv"
    print(f"처리중: {year}")

    df = pd.read_csv(file_path, encoding='utf-8')

    food_raw = df[df['상권업종대분류명'] == '음식'][
        ['상가업소번호', '상호명', '지점명', '상권업종중분류명', '상권업종소분류명', '행정동코드', '행정동명']
    ].copy()

    before = len(food_raw)

    # ── 중복 제거 ──────────────────────────────────────────────────────────────
    # [케이스 3] 완전 동일 반복: 상가업소번호까지 같은 행 → 첫 번째만 유지
    food_raw = food_raw.drop_duplicates(subset='상가업소번호', keep='first')

    # [케이스 1] 같은 가게가 업종 분류만 다르게 이중 등록된 경우
    #   → 행정동코드 + 상호명 + 지점명(NaN은 동일로 취급)이 같으면 첫 번째만 유지
    #   지점명이 다른 경우(예: 투썸플레이스 vs 투썸플레이스 광화문점)는 실제 다른 지점이므로 제거하지 않음
    food_raw['지점명_key'] = food_raw['지점명'].fillna('')
    food_raw = food_raw.drop_duplicates(subset=['행정동코드', '상호명', '지점명_key'], keep='first')
    food_raw = food_raw.drop(columns='지점명_key')

    after = len(food_raw)
    removed = before - after

    # 중복 제거 후 남아있는 상호명+행정동 중복(=지점명이 다른 정상 케이스) 출력
    dup_mask = food_raw.duplicated(subset=['행정동코드', '상호명'], keep=False)
    dup_df = food_raw[dup_mask].sort_values(['행정동코드', '상호명'])
    print(f"  [중복 제거] {year}년: {removed}행 삭제 → 잔여 중복(다른 지점) {dup_df.groupby(['행정동코드','상호명']).ngroups}건 ({len(dup_df)}행)")
    if not dup_df.empty:
        print(dup_df.to_string(index=False))
        print()
    # ─────────────────────────────────────────────────────────────────────────

    # 2023년 행정동 개편: 신설동(11230515)+용두동(11230533) → 용신동(11230536)
    # 개편 이전 데이터(2020~2022)도 용신동 코드로 통일해 전 기간 비교 가능하게 함
    DONG_RECODE = {11230515: 11230536, 11230533: 11230536}
    food_raw['행정동코드'] = food_raw['행정동코드'].replace(DONG_RECODE)
    food_raw.loc[food_raw['행정동코드'] == 11230536, '행정동명'] = '용신동'

    # ── 통합 카테고리 부여 ────────────────────────────────────────────────────
    food_raw['통합카테고리'] = food_raw.apply(
        lambda r: assign_category(r['상권업종중분류명'], r['상권업종소분류명']), axis=1
    )

    # 매핑 안 된 업소 확인 출력
    unmapped = food_raw[food_raw['통합카테고리'].isna()]
    if not unmapped.empty:
        print(f"  [미매핑] {year}년: {len(unmapped)}건")
        print(unmapped[['상권업종중분류명','상권업종소분류명']].value_counts().to_string())
        print()

    # 매핑된 업소만 사용
    food_df = food_raw[food_raw['통합카테고리'].notna()][
        ['상호명', '통합카테고리', '행정동코드', '행정동명']
    ].copy()
    food_df['년도'] = year
    # ─────────────────────────────────────────────────────────────────────────

    industry_count = (
        food_df
        .groupby(['년도', '행정동코드', '행정동명', '통합카테고리'])
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

final_hhi.to_csv("행정동별_HHI_2020_2025.csv", index=False, encoding='utf-8-sig')
final_industry_share.to_csv("행정동별_업종점유율_2020_2025.csv", index=False, encoding='utf-8-sig')

print(f"\nHHI 계산 완료: {final_hhi.shape}")
print(f"연도별 행정동 수:\n{final_hhi.groupby('년도')['행정동코드'].nunique()}")
print(final_hhi.head())
