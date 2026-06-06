import pandas as pd

all_hhi = []

for year in range(2020, 2027):

    file_path = f"소상공인시장진흥공단_상가(상권)정보_서울_{year}03.csv"

    print(f"처리중: {year}")

    # 데이터 읽기
    df = pd.read_csv(file_path, encoding='utf-8')

    # 음식 업종만
    food_df = df[df['상권업종대분류명'] == '음식'].copy()

    # 필요한 컬럼만
    food_df = food_df[
        ['상호명', '상권업종중분류명', '행정동코드', '행정동명']
    ]

    # 년도 추가
    food_df['년도'] = year

    # 행정동 × 업종별 업체수
    industry_count = (
        food_df
        .groupby(
            ['년도', '행정동코드', '행정동명', '상권업종중분류명']
        )
        .size()
        .reset_index(name='업체수')
    )

    # 행정동 전체 업체수
    total_count = (
        food_df
        .groupby(
            ['년도', '행정동코드', '행정동명']
        )
        .size()
        .reset_index(name='전체업체수')
    )

    # 결합
    industry_share = industry_count.merge(
        total_count,
        on=['년도', '행정동코드', '행정동명'],
        how='left'
    )

    # 점유율
    industry_share['점유율'] = (
        industry_share['업체수']
        / industry_share['전체업체수']
    )

    # HHI 요소
    industry_share['점유율제곱'] = (
        industry_share['점유율'] ** 2
    ) * 10000

    # 행정동별 HHI
    hhi_df = (
        industry_share
        .groupby(
            ['년도', '행정동코드', '행정동명']
        )['점유율제곱']
        .sum()
        .reset_index(name='HHI')
    )

    all_hhi.append(hhi_df)

# 모든 연도 합치기
final_hhi = pd.concat(all_hhi, ignore_index=True)

print(final_hhi.shape)
final_hhi.head()


# In[2]:


final_hhi.to_csv(
    "행정동별_HHI_2020_2026.csv",
    index=False,
    encoding='utf-8-sig'
)


# In[3]:


final_hhi = final_hhi.sort_values(
    ['행정동코드', '년도']
)

final_hhi['HHI변화량'] = (
    final_hhi
    .groupby('행정동코드')['HHI']
    .diff()
)

final_hhi['HHI변화율'] = (
    final_hhi
    .groupby('행정동코드')['HHI']
    .pct_change()
    * 100
)


# In[4]:


hhi_change_summary = (
    final_hhi
    .pivot(
        index=['행정동코드', '행정동명'],
        columns='년도',
        values='HHI'
    )
)

hhi_change_summary['증가량'] = (
    hhi_change_summary[2026]
    - hhi_change_summary[2020]
)


# In[5]:


top20_hhi_growth = (
    hhi_change_summary
    .sort_values('증가량', ascending=False)
    .head(20)
    .reset_index()
)

print(top20_hhi_growth[
    ['행정동코드', '행정동명', '증가량']
])


# In[6]:


top5_dongs = top20_hhi_growth['행정동코드'].head(5).tolist()

import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib as mpl

# 한글 폰트 설정
mpl.rc('font', family='Malgun Gothic')
mpl.rc('axes', unicode_minus=False)
sns.set(font='Malgun Gothic', font_scale=1.2)

get_ipython().run_line_magic('matplotlib', 'inline')

# TOP5 행정동 데이터만 추출
plot_df = final_hhi[
    final_hhi['행정동코드'].isin(top5_dongs)
]

plt.figure(figsize=(12, 6))

for dong in top5_dongs:

    temp = plot_df[
        plot_df['행정동코드'] == dong
    ].sort_values('년도')

    dong_name = temp['행정동명'].iloc[0]

    plt.plot(
        temp['년도'],
        temp['HHI'],
        marker='o',
        label=dong_name
    )

plt.title('HHI 증가량 TOP5 행정동 추이')
plt.xlabel('년도')
plt.ylabel('HHI')
plt.legend()
plt.grid(True)

plt.show()


# In[7]:


import pandas as pd

all_close_rate = []

target_industries = [
    '일식음식점',
    '중식음식점',
    '치킨전문점',
    '커피-음료',
    '패스트푸드점',
    '한식음식점',
    '호프-간이주점'
]

for year in range(2020, 2026):

    file_path = f"서울시_상권분석서비스(점포-행정동)_{year}년.csv"

    print(f"처리중: {year}")

    df = pd.read_csv(file_path, encoding='cp949')

    # 1분기만 선택
    df = df[
        df['기준_년분기_코드'].astype(str).str.endswith('1')
    ].copy()

    # 년도 생성
    df['년도'] = (
        df['기준_년분기_코드']
        .astype(str)
        .str[:4]
        .astype(int)
    )

    # 필요한 업종만 선택
    df = df[
        df['서비스_업종_코드_명'].isin(target_industries)
    ]

    # 필요한 컬럼만 남기기
    df = df[
        [
            '년도',
            '행정동_코드',
            '서비스_업종_코드_명',
            '폐업_률'
        ]
    ]

    all_close_rate.append(df)

# 전체 연도 결합
close_rate_df = pd.concat(
    all_close_rate,
    ignore_index=True
)

print(close_rate_df.shape)
close_rate_df.head()


# In[8]:


mean_close_rate = (
    close_rate_df
    .groupby(['년도', '행정동_코드'])['폐업_률']
    .mean()
    .reset_index(name='평균폐업률')
)


# In[9]:


hhi_close_df = final_hhi.merge(
    mean_close_rate,
    left_on=['년도', '행정동코드'],
    right_on=['년도', '행정동_코드'],
    how='left'
)

hhi_close_df = final_hhi.merge(
    mean_close_rate,
    left_on=['년도', '행정동코드'],
    right_on=['년도', '행정동_코드'],
    how='left'
)

hhi_close_df = hhi_close_df.drop(
    columns=['행정동_코드']
)

hhi_close_df = hhi_close_df[
    [
        '년도',
        '행정동코드',
        '행정동명',
        'HHI',
        '평균폐업률'
    ]
]

print(hhi_close_df.shape)

hhi_close_df.head()


# In[10]:


hhi_close_df[['HHI', '평균폐업률']].corr()


# In[11]:


import matplotlib.pyplot as plt

plt.figure(figsize=(8,6))

plt.scatter(
    hhi_close_df['HHI'],
    hhi_close_df['평균폐업률'],
    alpha=0.5
)

plt.xlabel('HHI')
plt.ylabel('평균폐업률')
plt.title('HHI와 평균폐업률')

plt.show()


# In[12]:


hhi_close_df['HHI구간'] = pd.qcut(
    hhi_close_df['HHI'],
    5,
    labels=[
        '하위20%',
        '20~40%',
        '40~60%',
        '60~80%',
        '상위20%'
    ]
)

hhi_close_df.groupby(
    'HHI구간'
)['평균폐업률'].mean()

group_result = (
    hhi_close_df
    .groupby('HHI구간')['평균폐업률']
    .mean()
)

ax = group_result.plot(
    kind='bar',
    figsize=(8, 5)
)

plt.title('HHI 구간별 평균 폐업률')
plt.xlabel('HHI 구간')
plt.ylabel('평균 폐업률 (%)')
plt.xticks(rotation=0)

# 수치 표시
for p in ax.patches:
    ax.annotate(
        f'{p.get_height():.2f}',
        (p.get_x() + p.get_width()/2, p.get_height()),
        ha='center',
        va='bottom'
    )

plt.grid(axis='y')

plt.show()


# In[15]:


hhi_close_df['HHI구간'] = pd.qcut(
    hhi_close_df['HHI'],
    10,
    labels=[
        '0~10%',
        '10~20%',
        '20~30%',
        '30~40%',
        '40~50%',
        '50~60%',
        '60~70%',
        '70~80%',
        '80~90%',
        '90~100%'
    ]
)

hhi_close_df.groupby(
    'HHI구간'
)['평균폐업률'].mean()

group_result = (
    hhi_close_df
    .groupby('HHI구간')['평균폐업률']
    .mean()
)

ax = group_result.plot(
    kind='bar',
    figsize=(8, 5)
)

plt.title('HHI 구간별 평균 폐업률')
plt.xlabel('HHI 구간')
plt.ylabel('평균 폐업률 (%)')
plt.xticks(rotation=0)

# 수치 표시
for p in ax.patches:
    ax.annotate(
        f'{p.get_height():.2f}',
        (p.get_x() + p.get_width()/2, p.get_height()),
        ha='center',
        va='bottom'
    )

plt.grid(axis='y')

plt.show()


# In[14]:


top20_hhi = (
    hhi_close_df
    .sort_values('HHI', ascending=False)
    .head(20)
)

top20_hhi['평균폐업률'].mean()

bottom20_hhi = (
    hhi_close_df
    .sort_values('HHI')
    .head(20)
)

bottom20_hhi['평균폐업률'].mean()

print(
    "HHI 상위20 평균 폐업률:",
    top20_hhi['평균폐업률'].mean()
)

print(
    "HHI 하위20 평균 폐업률:",
    bottom20_hhi['평균폐업률'].mean()
)


# In[ ]:




