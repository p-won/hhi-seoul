"""
연도별 행정동 프랜차이즈 비율 + 전체 점포수 정리
실행: python franchise_ratio_summarize.py
"""

import pandas as pd

df = pd.read_csv("../crawling/seoul_franchise_ratio.csv", encoding="utf-8-sig")

# 연도별 분기 합산 (행정동 기준)
annual = (
    df.groupby(["연도", "자치구", "행정동"])[["전체_점포수", "프랜차이즈_점포수"]]
    .sum()
    .reset_index()
)
annual["프랜차이즈_비율(%)"] = (
    annual["프랜차이즈_점포수"] / annual["전체_점포수"] * 100
).round(2)

# 전체 점포수 피벗
pivot_total = annual.pivot(index=["자치구", "행정동"], columns="연도", values="전체_점포수")
pivot_total.columns = [f"{y}년_전체점포수" for y in pivot_total.columns]

# 프랜차이즈 비율 피벗
pivot_ratio = annual.pivot(index=["자치구", "행정동"], columns="연도", values="프랜차이즈_비율(%)")
pivot_ratio.columns = [f"{y}년_프랜차이즈비율(%)" for y in pivot_ratio.columns]

# 연도 순서대로 전체점포수/비율 교차 배치
years = sorted(df["연도"].unique())
cols = []
for y in years:
    cols.append(f"{y}년_전체점포수")
    cols.append(f"{y}년_프랜차이즈비율(%)")

result = pd.concat([pivot_total, pivot_ratio], axis=1)[cols].reset_index()

print(result.to_string(index=False))

result.to_csv("annual_franchise_ratio.csv", index=False, encoding="utf-8-sig")
print("\n✔ annual_franchise_ratio.csv 저장 완료")
