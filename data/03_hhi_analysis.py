"""
HHI와 폐업률 결합 및 상관분석
입력: 행정동별_HHI_2020_2026.csv, 행정동별_평균폐업률_2024_2025.csv (분석용)
출력: 행정동별_HHI_폐업률_결합.csv, 콘솔 분석 결과
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns

mpl.rc('font', family='AppleGothic')  # Mac: AppleGothic / Windows: Malgun Gothic
mpl.rc('axes', unicode_minus=False)

# --- 데이터 로드 ---
final_hhi = pd.read_csv("행정동별_HHI_2020_2026.csv", encoding='utf-8-sig')
mean_close_rate = pd.read_csv("행정동별_평균폐업률_2024_2025.csv", encoding='utf-8-sig')

# 분석 대상: 2024~2025년만 사용
hhi_close_df = final_hhi[final_hhi['년도'].isin([2024, 2025])].merge(
    mean_close_rate,
    on=['년도', '행정동코드'],
    how='left'
)[['년도', '행정동코드', '행정동명', 'HHI', '평균폐업률']]

hhi_close_df.to_csv("행정동별_HHI_폐업률_결합.csv", index=False, encoding='utf-8-sig')

# --- 상관분석 ---
print("=== HHI × 평균폐업률 상관계수 ===")
print(hhi_close_df[['HHI', '평균폐업률']].corr())

# --- 산점도 ---
plt.figure(figsize=(8, 6))
plt.scatter(hhi_close_df['HHI'], hhi_close_df['평균폐업률'], alpha=0.4)
plt.xlabel('HHI')
plt.ylabel('평균폐업률')
plt.title('HHI와 평균폐업률 관계')
plt.tight_layout()
plt.savefig("plot_hhi_closerate_scatter.png", dpi=150)
plt.show()

# --- HHI 구간별 평균 폐업률 ---
hhi_close_df['HHI구간'] = pd.qcut(
    hhi_close_df['HHI'], 5,
    labels=['하위20%', '20~40%', '40~60%', '60~80%', '상위20%']
)

group_result = hhi_close_df.groupby('HHI구간')['평균폐업률'].mean()
print("\n=== HHI 구간별 평균폐업률 ===")
print(group_result)

ax = group_result.plot(kind='bar', figsize=(8, 5))
plt.title('HHI 구간별 평균 폐업률')
plt.xlabel('HHI 구간')
plt.ylabel('평균 폐업률 (%)')
plt.xticks(rotation=0)
for p in ax.patches:
    ax.annotate(f'{p.get_height():.2f}',
                (p.get_x() + p.get_width() / 2, p.get_height()),
                ha='center', va='bottom')
plt.grid(axis='y')
plt.tight_layout()
plt.savefig("plot_hhi_closerate_bar.png", dpi=150)
plt.show()

# --- HHI 상위/하위 20개 비교 ---
top20 = hhi_close_df.nlargest(20, 'HHI')
bottom20 = hhi_close_df.nsmallest(20, 'HHI')
print(f"\nHHI 상위 20개 평균 폐업률: {top20['평균폐업률'].mean():.2f}%")
print(f"HHI 하위 20개 평균 폐업률: {bottom20['평균폐업률'].mean():.2f}%")
