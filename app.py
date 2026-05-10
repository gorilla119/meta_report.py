import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import timedelta

st.set_page_config(page_title="Meta広告 統合分析ボード", layout="wide")
st.title("🚀 Meta広告 統合分析ダッシュボード")

uploaded_file = st.file_uploader("Meta広告のレポートCSVを選択してください", type='csv')

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df = df.fillna(0)

        # 列名設定
        col_date = '日'
        col_campaign = 'キャンペーン名'
        col_ad = '広告名'
        col_cost = '消化金額 (JPY)' if '消化金額 (JPY)' in df.columns else '消化金額'
        col_lead = 'リード'
        col_freq = 'フリークエンシー'

        # 日付変換
        df[col_date] = pd.to_datetime(df[col_date])

        # サイドバー設定
        all_campaigns = df[col_campaign].unique().tolist()
        selected_campaigns = st.sidebar.multiselect("キャンペーン選択", all_campaigns, default=all_campaigns[:1])
        f_df = df[df[col_campaign].isin(selected_campaigns)].copy()

        # 日別集計
        df_daily = f_df.groupby([col_date, col_campaign]).agg({
            col_cost: 'sum', col_lead: 'sum', col_freq: 'mean'
        }).reset_index()
        df_daily = df_daily.sort_values(by=[col_campaign, col_date])
        df_daily['CPA'] = (df_daily[col_cost] / df_daily[col_lead]).replace([np.inf, -np.inf], np.nan).fillna(0)

        # --- サマリー表示 ---
        c1, c2, c3, c4 = st.columns(4)
        t_cost, t_leads = f_df[col_cost].sum(), f_df[col_lead].sum()
        c1.metric("総消化金額", f"¥{int(t_cost):,}")
        c2.metric("総リード数", f"{int(t_leads):,}")
        c3.metric("平均CPA", f"¥{int(t_cost/t_leads):,}" if t_leads > 0 else "¥0")
        c4.metric("平均頻度", f"{f_df[col_freq].mean():.2f}")

        st.divider()

        # --- グラフ表示（土日の背景色追加） ---
        st.subheader("📈 日次パフォーマンス推移")
        tab1, tab2 = st.tabs(["💰 CPA推移", "🔄 フリークエンシー推移"])

        # 土日の範囲を特定する関数
        def add_weekend_shading(fig, min_date, max_date):
            curr_date = min_date
            while curr_date <= max_date:
                if curr_date.weekday() == 5:  # 土曜日
                    fig.add_vrect(
                        x0=curr_date.strftime('%Y-%m-%d'),
                        x1=(curr_date + timedelta(days=1)).strftime('%Y-%m-%d'),
                        fillcolor="gray", opacity=0.2, line_width=0,
                        annotation_text="Weekend", annotation_position="top left"
                    )
                curr_date += timedelta(days=1)
            return fig

        min_d, max_d = df_daily[col_date].min(), df_daily[col_date].max()

        with tab1:
            fig_line = px.line(df_daily, x=col_date, y='CPA', color=col_campaign, markers=True)
            fig_line = add_weekend_shading(fig_line, min_d, max_d)
            st.plotly_chart(fig_line, use_container_width=True)
            
        with tab2:
            fig_freq = px.line(df_daily, x=col_date, y=col_freq, color=col_campaign, markers=True)
            fig_freq = add_weekend_shading(fig_freq, min_d, max_d)
            st.plotly_chart(fig_freq, use_container_width=True)

        # --- クリエイティブ分析（以下省略・前回同様） ---
        st.divider()
        st.subheader("🎨 クリエイティブ詳細")
        ad_sum = f_df.groupby(col_ad).agg({col_cost: 'sum', col_lead: 'sum', col_freq: 'mean'}).reset_index()
        ad_sum['CPA'] = (ad_sum[col_cost] / ad_sum[col_lead]).replace([np.inf, -np.inf], 0).fillna(0)
        st.dataframe(ad_sum.sort_values('CPA'))

    except Exception as e:
        st.error(f"エラー: {e}")
