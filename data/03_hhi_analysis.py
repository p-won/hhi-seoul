"""
HHI와 폐업률 결합 및 상관분석 (동시점 + 시차 분석)
입력: 행정동별_HHI_2020_2025.csv, 행정동별_평균폐업률_2024_2025.csv (분석용)
출력: 행정동별_HHI_폐업률_결합.csv
      plot_hhi_closerate_scatter.png  — 동시점 산점도
      plot_hhi_closerate_bar.png      — 동시점 구간별 바플롯
      plot_lag_bar.png                — 시차별 구간 비교 바플롯
"""

import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import matplotlib as mpl

mpl.rc('font', family='AppleGothic')
mpl.rc('axes', unicode_minus=False)

LABELS = ['하위20%', '20~40%', '40~60%', '60~80%', '상위20%']

# --- 데이터 로드 ---
final_hhi = pd.read_csv("행정동별_HHI_2020_2025.csv", encoding='utf-8-sig')
mean_close_rate = pd.read_csv("행정동별_평균폐업률_2024_2025.csv", encoding='utf-8-sig')

# --- 결합 (행정동명은 HHI 쪽 기준으로 사용) ---
hhi_close_df = (
    final_hhi[final_hhi['년도'].isin([2024, 2025])]
    .merge(mean_close_rate, on=['년도', '행정동코드'], how='left')
    [['년도', '행정동코드', '행정동명', 'HHI', '평균폐업률']]
)

# 결합 후 폐업률 결측 행정동 출력 (코드 불일치로 인한 NaN)
missing = hhi_close_df[hhi_close_df['평균폐업률'].isna()]
if not missing.empty:
    print(f"[경고] 폐업률 결측 행정동 {len(missing)}개 → 상관분석에서 제외")
    print(missing[['년도', '행정동코드', '행정동명']].to_string(index=False))

hhi_close_df.to_csv("행정동별_HHI_폐업률_결합.csv", index=False, encoding='utf-8-sig')

# 상관분석용: 결측 제외 + 행정동별 2년 평균으로 집계
valid = (
    hhi_close_df.dropna(subset=['HHI', '평균폐업률'])
    .groupby(['행정동코드', '행정동명'])[['HHI', '평균폐업률']]
    .mean()
    .reset_index()
)

# ══════════════════════════════════════════════════════════════════
# 1. 동시점 분석 (HHI 2024~2025 vs 폐업률 2024~2025)
# ══════════════════════════════════════════════════════════════════
r, p = stats.pearsonr(valid['HHI'], valid['평균폐업률'])
print("\n=== [동시점] HHI × 평균폐업률 상관분석 ===")
print(f"Pearson r = {r:.4f}")
print(f"p-value   = {p:.4f}  {'(유의하지 않음, p > 0.05)' if p >= 0.05 else '(유의함, p < 0.05)'}")

# 산점도
plt.figure(figsize=(8, 6))
plt.scatter(valid['HHI'], valid['평균폐업률'], alpha=0.4)
plt.xlabel('HHI')
plt.ylabel('평균폐업률')
plt.title(f'HHI와 평균폐업률 관계 — 동시점\n(r={r:.3f}, p={p:.3f})')
plt.tight_layout()
plt.savefig("plot_hhi_closerate_scatter.png", dpi=150)
plt.show()

# 구간별 바플롯
valid_copy = valid.copy()
valid_copy['HHI구간'] = pd.qcut(valid_copy['HHI'], 5, labels=LABELS)
group_result = valid_copy.groupby('HHI구간', observed=False)['평균폐업률'].mean()

print("\n=== [동시점] HHI 구간별 평균폐업률 ===")
print(group_result.round(2))

ax = group_result.plot(kind='bar', figsize=(8, 5), color='#2196F3')
plt.title(f'HHI 구간별 평균 폐업률 — 동시점 (r={r:.3f})')
plt.xlabel('HHI 구간')
plt.ylabel('평균 폐업률 (%)')
plt.xticks(rotation=0)
for patch in ax.patches:
    ax.annotate(f'{patch.get_height():.2f}',
                (patch.get_x() + patch.get_width() / 2, patch.get_height() + 0.02),
                ha='center', va='bottom')
plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig("plot_hhi_closerate_bar.png", dpi=150)
plt.show()

# HHI 상위/하위 20개 비교
top20 = valid.nlargest(20, 'HHI')
bottom20 = valid.nsmallest(20, 'HHI')
print(f"\n[동시점] HHI 상위 20개 평균 폐업률: {top20['평균폐업률'].mean():.2f}%")
print(f"[동시점] HHI 하위 20개 평균 폐업률: {bottom20['평균폐업률'].mean():.2f}%")

# ══════════════════════════════════════════════════════════════════
# 2. 시차 분석 (과거 HHI vs 폐업률 2024~2025)
# ══════════════════════════════════════════════════════════════════
close_avg = (
    mean_close_rate
    .groupby('행정동코드')['평균폐업률']
    .mean()
    .reset_index()
    .rename(columns={'평균폐업률': '폐업률_2024_2025'})
)

LAG_WINDOWS = {
    '동시점 (2024~2025)': [2024, 2025],
    '1~2년 전 (2022~2023)': [2022, 2023],
    '3~4년 전 (2020~2021)': [2020, 2021],
}

print("\n=== 시차별 HHI × 폐업률 상관분석 ===")
fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)

for ax, (title, years) in zip(axes, LAG_WINDOWS.items()):
    hhi_avg = (
        final_hhi[final_hhi['년도'].isin(years)]
        .groupby('행정동코드')['HHI']
        .mean()
        .reset_index()
    )
    merged = hhi_avg.merge(close_avg, on='행정동코드')
    r_lag, p_lag = stats.pearsonr(merged['HHI'], merged['폐업률_2024_2025'])
    sig = '* p<0.05' if p_lag < 0.05 else 'n.s.'
    print(f"  [{title}]  r={r_lag:.4f},  p={p_lag:.4f}  ({sig})")

    merged['HHI구간'] = pd.qcut(merged['HHI'], 5, labels=LABELS)
    group = merged.groupby('HHI구간', observed=False)['폐업률_2024_2025'].mean()

    bars = ax.bar(LABELS, group.values, color='#2196F3', width=0.6)
    for bar, val in zip(bars, group.values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.02,
                f'{val:.2f}', ha='center', va='bottom', fontsize=9)

    ax.set_title(f'{title}\nr={r_lag:.3f}  {sig}', fontsize=11)
    ax.set_xlabel('HHI 구간')
    ax.set_ylim(3.5, 5.0)
    ax.grid(axis='y', linestyle='--', alpha=0.5)

axes[0].set_ylabel('평균 폐업률 (%)')
fig.suptitle('시차별 HHI 구간 × 폐업률(2024~2025)', fontsize=13, fontweight='bold')
plt.tight_layout()
plt.savefig("plot_lag_bar.png", dpi=150)
plt.show()
