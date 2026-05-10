import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import timedelta

st.set_page_config(page_title="Meta広告 統合分析ダッシュボード", layout="wide")
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

        df[col_date] = pd.to_datetime(df[col_date])

        # サイドバー
        selected_campaigns = st.sidebar.multiselect("キャンペーン選択", df[col_campaign].unique().tolist(), default=df[col_campaign].unique().tolist()[:1])
        f_df = df[df[col_campaign].isin(selected_campaigns)].copy()

        # --- 1. 日別推移（土日網掛け） ---
        df_daily = f_df.groupby([col_date, col_campaign]).agg({col_cost: 'sum', col_lead: 'sum', col_freq: 'mean'}).reset_index()
        df_daily = df_daily.sort_values(by=[col_campaign, col_date])
        df_daily['CPA'] = (df_daily[col_cost] / df_daily[col_lead]).replace([np.inf, -np.inf], np.nan).fillna(0)

        st.subheader("📈 時系列パフォーマンス推移")
        tab_cpa, tab_freq = st.tabs(["💰 日次CPA", "🔄 フリークエンシー"])

        def add_shading(fig, min_d, max_d):
            curr = min_d
            while curr <= max_d:
                if curr.weekday() == 5:
                    fig.add_vrect(x0=curr.strftime('%Y-%m-%d'), x1=(curr + timedelta(days=1)).strftime('%Y-%m-%d'), fillcolor="gray", opacity=0.1, line_width=0)
                curr += timedelta(days=1)
            return fig

        min_d, max_d = df_daily[col_date].min(), df_daily[col_date].max()
        with tab_cpa:
            st.plotly_chart(add_shading(px.line(df_daily, x=col_date, y='CPA', color=col_campaign, markers=True), min_d, max_d), use_container_width=True)
        with tab_freq:
            st.plotly_chart(add_shading(px.line(df_daily, x=col_date, y=col_freq, color=col_campaign, markers=True), min_d, max_d), use_container_width=True)

        st.divider()

        # --- 2. クリエイティブ分析（ここを強化） ---
        st.subheader("🎨 クリエイティブ別 分析")
        
        ad_summary = f_df.groupby(col_ad).agg({col_cost: 'sum', col_lead: 'sum', col_freq: 'mean'}).reset_index()
        ad_summary['CPA'] = (ad_summary[col_cost] / ad_summary[col_lead]).replace([np.inf, -np.inf], np.nan).fillna(0)
        
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.write("**獲得数 vs 効率（獲得規模の確認）**")
            fig_scatter_lead = px.scatter(ad_summary[ad_summary[col_lead] > 0], x=col_lead, y='CPA', size=col_cost, color=col_ad, hover_name=col_ad)
            st.plotly_chart(fig_scatter_lead, use_container_width=True)

        with col_right:
            st.write("**頻度 vs 効率（クリエイティブの摩耗確認）**")
            # X軸をフリークエンシーにする
            fig_scatter_freq = px.scatter(
                ad_summary, 
                x=col_freq, y='CPA', size=col_cost, color=col_ad, hover_name=col_ad,
                labels={col_freq: 'フリークエンシー（接触頻度）', 'CPA': 'CPA (円)'},
                title="接触頻度が増えてCPAが上がっていないか？"
            )
            # 頻度の目安となる2.0に縦線を引く
            fig_scatter_freq.add_vline(x=2.0, line_dash="dash", line_color="red", annotation_text="摩耗ライン(2.0)")
            st.plotly_chart(fig_scatter_freq, use_container_width=True)

        # 詳細テーブル
        disp_ad = ad_summary.sort_values('CPA').copy()
        disp_ad['消化金額'] = disp_ad[col_cost].map('¥{:,.0f}'.format)
        disp_ad['CPA'] = disp_ad['CPA'].map('¥{:,.0f}'.format)
        disp_ad['頻度'] = disp_ad[col_freq].map('{:.2f}'.format)
        st.dataframe(disp_ad[[col_ad, '消化金額', col_lead, 'CPA', '頻度']], use_container_width=True)

    except Exception as e:
        st.error(f"エラー: {e}")
