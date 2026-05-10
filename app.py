import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Meta広告ダッシュボード", layout="wide")
st.title("📊 Meta広告 パフォーマンス分析")

uploaded_file = st.file_uploader("Meta広告のレポートCSVを選択してください", type='csv')

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df = df.fillna(0)

        # 列名の設定
        col_date = '日'
        col_campaign = 'キャンペーン名'
        col_cost = '消化金額 (JPY)' if '消化金額 (JPY)' in df.columns else '消化金額'
        col_lead = 'リード'

        # 日付変換
        df[col_date] = pd.to_datetime(df[col_date])

        # 【重要】1日・1キャンペーン単位にデータを「合算」する処理
        # これにより、同じ日の複数行（広告別など）が1行にまとまります
        df_daily = df.groupby([col_date, col_campaign]).agg({
            col_cost: 'sum',
            col_lead: 'sum'
        }).reset_index()

        # 並び替え
        df_daily = df_daily.sort_values(by=[col_campaign, col_date])

        # サイドバー設定
        st.sidebar.header("表示設定")
        all_campaigns = df_daily[col_campaign].unique().tolist()
        selected_campaigns = st.sidebar.multiselect("キャンペーンを選択", all_campaigns, default=all_campaigns[:1])

        # 絞り込み
        filtered_df = df_daily[df_daily[col_campaign].isin(selected_campaigns)].copy()

        # CPA計算（合算した後の数値で計算）
        filtered_df['CPA'] = filtered_df[col_cost] / filtered_df[col_lead]
        filtered_df['CPA'] = filtered_df['CPA'].replace([np.inf, -np.inf], np.nan).fillna(0)

        # メイン表示
        col1, col2, col3 = st.columns(3)
        t_cost = filtered_df[col_cost].sum()
        t_leads = filtered_df[col_lead].sum()
        a_cpa = t_cost / t_leads if t_leads > 0 else 0
        
        col1.metric("総消化金額", f"¥{int(t_cost):,}")
        col2.metric("総リード数", f"{int(t_leads):,}")
        col3.metric("平均CPA", f"¥{int(a_cpa):,}")

        st.divider()

        # グラフ表示
        st.subheader("日次CPA推移")
        if not filtered_df.empty:
            fig = px.line(filtered_df, x=col_date, y='CPA', color=col_campaign,
                          title="キャンペーン別の日次CPA推移（1日単位で集計）",
                          labels={'CPA': 'CPA (円)', col_date: '日付'},
                          markers=True)
            
            fig.update_xaxes(type='date', tickformat='%m/%d')
            st.plotly_chart(fig, use_container_width=True)

        # サマリーテーブル
        st.subheader("キャンペーン別サマリー")
        summary = filtered_df.groupby(col_campaign).agg({col_cost: 'sum', col_lead: 'sum'}).reset_index()
        summary['平均CPA'] = (summary[col_cost] / summary[col_lead]).replace([np.inf, -np.inf], 0).fillna(0).apply(lambda x: f"¥{int(x):,}")
        st.dataframe(summary, use_container_width=True)

    except Exception as e:
        st.error(f"読み込みエラー: {e}")
else:
    st.info("CSVファイルをアップロードしてください。")
