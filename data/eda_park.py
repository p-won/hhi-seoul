import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib as mpl

mpl.rc('font', family='AppleGothic')
mpl.rc('axes', unicode_minus=False)

worker = pd.read_csv('raw_data/worker-dong.csv', encoding='utf-8')
resident = pd.read_csv('raw_data/resident-dong.csv', encoding='utf-8')

w = worker[worker['기준_년분기_코드'].astype(str).str.endswith('1')].copy()
r = resident[resident['기준_년분기_코드'].astype(str).str.endswith('1')].copy()
w['년도'] = w['기준_년분기_코드'].astype(str).str[:4].astype(int)
r['년도'] = r['기준_년분기_코드'].astype(str).str[:4].astype(int)

pop = w[['년도','행정동_코드','행정동_코드_명','총_직장_인구_수']].merge(
    r[['년도','행정동_코드','총_상주인구_수']], on=['년도','행정동_코드']
)
pop = pop[(pop['총_상주인구_수'] > 0) & (pop['년도'] == 2025)].copy()
pop['직장상주비율'] = pop['총_직장_인구_수'] / pop['총_상주인구_수']
pop = pop.sort_values('직장상주비율', ascending=False).reset_index(drop=True)

fig, ax = plt.subplots(figsize=(14, 5))

ax.bar(range(len(pop)), pop['직장상주비율'], width=1.0, color='#90CAF9', edgecolor='none')

# 임계값에 해당하는 x 인덱스 찾기 (정렬된 순서에서 몇 번째 행정동인지)
idx_office = (pop['직장상주비율'] >= 1.0).sum()   # 1.0 이상인 개수 = 경계 인덱스
idx_mixed  = (pop['직장상주비율'] >= 0.2).sum()   # 0.2 이상인 개수 = 경계 인덱스

n_office = idx_office
n_mixed  = idx_mixed - idx_office
n_resid  = len(pop) - idx_mixed

ax.axvline(idx_office, color='#E53935', linestyle='--', linewidth=1.5,
           label=f'오피스형 기준 (비율 ≥ 1.0, 직장인구 ≥ 상주인구)')
ax.axvline(idx_mixed,  color='#FB8C00', linestyle='--', linewidth=1.5,
           label=f'주거형 기준 (비율 < 0.2)')

# 구간 레이블
ax.text(idx_office / 2,          4.7, f'오피스형\n{n_office}개', ha='center', color='#E53935', fontsize=9, fontweight='bold')
ax.text((idx_office + idx_mixed) / 2, 4.7, f'혼합형\n{n_mixed}개',  ha='center', color='#FB8C00', fontsize=9, fontweight='bold')
ax.text((idx_mixed + len(pop)) / 2,   4.7, f'주거형\n{n_resid}개',  ha='center', color='#1565C0', fontsize=9, fontweight='bold')

ax.set_xlabel('행정동 (직장상주비율 높은 순)')
ax.set_ylabel('직장/상주 인구 비율')
ax.set_title(f'행정동별 직장상주비율 분포 (2025, 총 {len(pop)}개 행정동)')
ax.set_xlim(-0.5, len(pop) - 0.5)
ax.set_ylim(0, 5)  # 극단값 클리핑 (명동 50.5 등), 초과 행수 표기
n_over = (pop['직장상주비율'] > 5).sum()
ax.text(1, 4.8, f'y>5 초과 {n_over}개 행정동 잘림', fontsize=8, color='gray')
ax.legend(fontsize=9)
ax.grid(axis='y', linestyle='--', alpha=0.4)

plt.tight_layout()
plt.savefig('plot_worker_threshold.png', dpi=150)
print('저장 완료: plot_worker_threshold.png')


# ══════════════════════════════════════════════════════════════════════════════
# [그래프 1] 대표업종 바차트
# - 각 행정동의 '점유율 1위 업종'이 서울 전체에서 몇 개 동에서 대표업종인지 집계
# - 시사점: 한식 위주로 대표업종이 집중되는지, 특정 업종이 편중되는지 파악
#           상권 다양성이 부족한 구조인지 판단하는 근거가 됨
# ══════════════════════════════════════════════════════════════════════════════
final = pd.read_csv('행정동별_최종분석.csv', encoding='utf-8-sig')

top_counts = final['대표업종'].value_counts().sort_values(ascending=True)

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.barh(top_counts.index, top_counts.values, color='#42A5F5', edgecolor='none')
for bar, val in zip(bars, top_counts.values):
    ax.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
            str(val), va='center', fontsize=9)
ax.set_xlabel('행정동 수')
ax.set_title('행정동별 대표업종(점유율 1위) 분포\n(2025년 기준)')
ax.grid(axis='x', linestyle='--', alpha=0.4)
plt.tight_layout()
plt.savefig('plot_top_industry.png', dpi=150)
print('저장 완료: plot_top_industry.png')


# ══════════════════════════════════════════════════════════════════════════════
# [그래프 2] 과밀/부족 업종 파이차트 (2×2 패널)
# - 과밀: 해당 동 점유율이 서울 평균의 1.5배 초과인 업종이 하나라도 있는 동
# - 부족: 주요 업종(서울 평균 5% 이상) 중 서울 평균 0.5배 미만인 업종이 있는 동
# - 시사점: 서울 음식업 상권의 구조적 과밀·공급 부족 문제를 동 단위로 진단
#           과밀 동이 많다면 특정 업종 쏠림 → 폐업 위험 높아짐을 시사
# ══════════════════════════════════════════════════════════════════════════════
n_total  = len(final)
n_both   = (final['과밀업종'].notna() & final['부족업종'].notna()).sum()
n_over   = (final['과밀업종'].notna() & final['부족업종'].isna()).sum()
n_scarce = (final['과밀업종'].isna()  & final['부족업종'].notna()).sum()
n_none   = (final['과밀업종'].isna()  & final['부족업종'].isna()).sum()

labels = [f'과밀만\n{n_over}개', f'부족만\n{n_scarce}개',
          f'과밀+부족\n{n_both}개', f'해당없음\n{n_none}개']
sizes  = [n_over, n_scarce, n_both, n_none]
colors = ['#EF5350', '#FFA726', '#AB47BC', '#90CAF9']

fig, ax = plt.subplots(figsize=(7, 6))
ax.pie(
    sizes, labels=labels, colors=colors,
    autopct='%1.1f%%', startangle=90,
    wedgeprops={'edgecolor': 'white', 'linewidth': 1.5},
    textprops={'fontsize': 11},
)
ax.set_title(f'행정동별 과밀·부족 업종 현황\n(총 {n_total}개 동, 2025년 기준)',
             fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig('plot_overconc_pie.png', dpi=150)
print(f'저장 완료: plot_overconc_pie.png  |  과밀만:{n_over} 부족만:{n_scarce} 둘다:{n_both} 해당없음:{n_none}')


# ══════════════════════════════════════════════════════════════════════════════
# [그래프 2-2] 업종별 과밀·부족 행정동 수 누적 가로막대
# - 각 업종에 대해 행정동을 과밀(서울평균 1.5배 초과) / 부족(0.5배 미만, 주요업종만)
#   / 해당없음 3가지로 분류하고, 업종별로 누적 가로막대로 표현
# - 시사점: 어느 업종이 서울 전역에서 가장 쏠림이 심한지(과밀 많음),
#           어느 업종이 전반적으로 공급 부족 상태인지 한눈에 비교 가능
# ══════════════════════════════════════════════════════════════════════════════
share_df = pd.read_csv('행정동별_업종점유율_2020_2025.csv', encoding='utf-8-sig')
TARGET_YEAR = share_df['년도'].max()
share_yr = share_df[share_df['년도'] == TARGET_YEAR].copy()

OVERCONC_THRESHOLD = 1.5
SCARCE_THRESHOLD   = 0.5
SCARCE_MIN_AVG     = 0.05

seoul_avg = share_yr.groupby('통합카테고리')['점유율'].mean()

rows = []
for cat, group in share_yr.groupby('통합카테고리'):
    avg = seoul_avg[cat]
    for _, row in group.iterrows():
        val = row['점유율']
        if val > avg * OVERCONC_THRESHOLD:
            label = '과밀'
        elif avg >= SCARCE_MIN_AVG and val < avg * SCARCE_THRESHOLD:
            label = '부족'
        else:
            label = '해당없음'
        rows.append({'통합카테고리': cat, '분류': label})

status_df = pd.DataFrame(rows)
counts = (
    status_df.groupby(['통합카테고리', '분류'])
    .size()
    .unstack(fill_value=0)
    .reindex(columns=['과밀', '부족', '해당없음'], fill_value=0)
)

# 과밀 많은 순으로 정렬
counts = counts.sort_values('과밀', ascending=True)

fig, ax = plt.subplots(figsize=(9, 6))
n_dongs = share_yr['행정동코드'].nunique()

bar_colors = {'과밀': '#EF5350', '부족': '#FFA726', '해당없음': '#CFD8DC'}
left = np.zeros(len(counts))
for col in ['과밀', '부족', '해당없음']:
    vals = counts[col].values
    bars = ax.barh(counts.index, vals, left=left,
                   color=bar_colors[col], label=col, edgecolor='none')
    # 값이 10 이상인 셀에만 숫자 표기
    for bar, val in zip(bars, vals):
        if val >= 10:
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_y() + bar.get_height() / 2,
                    str(val), ha='center', va='center', fontsize=8, color='white', fontweight='bold')
    left += vals

ax.axvline(n_dongs, color='gray', linestyle='--', linewidth=1, alpha=0.6)
ax.text(n_dongs + 1, -0.6, f'전체\n{n_dongs}개', fontsize=8, color='gray')
ax.set_xlabel('행정동 수')
ax.set_title(f'업종별 과밀·부족 행정동 수\n({TARGET_YEAR}년 기준, 전체 {n_dongs}개 행정동)')
ax.legend(loc='lower right', fontsize=10)
ax.grid(axis='x', linestyle='--', alpha=0.3)
plt.tight_layout()
plt.savefig('plot_industry_status_bar.png', dpi=150)
print('저장 완료: plot_industry_status_bar.png')


# ══════════════════════════════════════════════════════════════════════════════
# [그래프 3] 상권타입 분포 바차트
# - 직장/상주인구 비율 기반으로 분류한 오피스형·혼합형·주거형 행정동 수
# - 시사점: 서울 음식업 상권이 주거형 중심임을 확인,
#           상권타입별 HHI·폐업률 차이를 해석하는 배경 정보
# ══════════════════════════════════════════════════════════════════════════════
v2 = pd.read_csv('행정동별_최종분석_v2.csv', encoding='utf-8-sig')

type_order  = ['오피스형', '혼합형', '주거형']
type_colors = ['#EF5350', '#FFA726', '#42A5F5']
type_counts = v2['상권타입'].value_counts().reindex(type_order, fill_value=0)

fig, ax = plt.subplots(figsize=(6, 4))
bars = ax.bar(type_counts.index, type_counts.values,
              color=type_colors, edgecolor='none', width=0.5)
for bar, val in zip(bars, type_counts.values):
    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
            str(val), ha='center', fontsize=11, fontweight='bold')
ax.set_ylabel('행정동 수')
ax.set_title('서울 음식업 상권타입 분포\n(2025년 직장/상주인구 비율 기준)')
ax.set_ylim(0, type_counts.max() * 1.15)
ax.grid(axis='y', linestyle='--', alpha=0.4)
plt.tight_layout()
plt.savefig('plot_commercial_type.png', dpi=150)
print('저장 완료: plot_commercial_type.png')


# ══════════════════════════════════════════════════════════════════════════════
# [그래프 4] 상권타입 × 경쟁구조유형 히트맵
# - 행: 상권타입(오피스형/혼합형/주거형), 열: 경쟁구조유형(6가지)
# - 셀 값: 해당 조합의 행정동 수
# - 시사점: 주거형 상권에서 어떤 경쟁구조가 지배적인지,
#           오피스형에서는 브랜드 경쟁이 강한지 등 상권 성격과 경쟁 구조의 연관성 파악
# ══════════════════════════════════════════════════════════════════════════════
v3 = pd.read_csv('행정동별_최종분석_v3.csv', encoding='utf-8-sig')

# 경쟁구조 순서: HHI 높음 → 낮음, 프랜차이즈 높음 → 낮음 순
comp_order = ['브랜드 경쟁형', '브랜드 집중형', '로컬 독점형',
              '브랜드 혼합형', '분산 혼합형',  '분산 경쟁형']

heatmap_data = (
    v3.groupby(['상권타입', '경쟁구조유형'])
    .size()
    .unstack(fill_value=0)
    .reindex(index=type_order, columns=comp_order, fill_value=0)
)

fig, ax = plt.subplots(figsize=(9, 4))
im = ax.imshow(heatmap_data.values, cmap='Blues', aspect='auto')

ax.set_xticks(range(len(comp_order)))
ax.set_xticklabels(comp_order, fontsize=10)
ax.set_yticks(range(len(type_order)))
ax.set_yticklabels(type_order, fontsize=11)

# 셀에 숫자 표기
for i in range(len(type_order)):
    for j in range(len(comp_order)):
        val = heatmap_data.values[i, j]
        color = 'white' if val > heatmap_data.values.max() * 0.6 else 'black'
        ax.text(j, i, str(val), ha='center', va='center', fontsize=11,
                color=color, fontweight='bold')

ax.set_title('상권타입 × 경쟁구조유형 히트맵\n(행정동 수, 2024~2025년 기준)',
             fontsize=12, fontweight='bold')
plt.colorbar(im, ax=ax, label='행정동 수')
plt.tight_layout()
plt.savefig('plot_competition_heatmap.png', dpi=150)
print('저장 완료: plot_competition_heatmap.png')
