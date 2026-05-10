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

        # 列名のマッピング（ヘッダー画像に基づき調整）
        col_date = '日'
        col_campaign = 'キャンペーン名'
        col_ad = '広告名'
        col_cost = '消化金額 (JPY)' if '消化金額 (JPY)' in df.columns else '消化金額'
        col_lead = 'リード'
        col_freq = 'フリークエンシー'
        col_ctr = 'CTR(すべて)' if 'CTR(すべて)' in df.columns else 'CTR'
        col_cpm = 'CPM (1,000回インプレッションあたりの単価) (JPY)' if 'CPM (1,000回インプレッションあたりの単価) (JPY)' in df.columns else 'CPM'

        df[col_date] = pd.to_datetime(df[col_date])

        # サイドバー設定
        selected_campaigns = st.sidebar.multiselect("キャンペーン選択", df[col_campaign].unique().tolist(), default=df[col_campaign].unique().tolist()[:1])
        f_df = df[df[col_campaign].isin(selected_campaigns)].copy()

        # --- 1. 日別推移グラフ ---
        df_daily = f_df.groupby([col_date, col_campaign]).agg({col_cost: 'sum', col_lead: 'sum', col_freq: 'mean'}).reset_index()
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

        # --- 2. クリエイティブ分析 ---
        st.subheader("🎨 クリエイティブ別 総合分析")
        
        # 集計（CTRとCPMは平均値で集計）
        ad_summary = f_df.groupby(col_ad).agg({
            col_cost: 'sum', 
            col_lead: 'sum', 
            col_freq: 'mean',
            col_ctr: 'mean',
            col_cpm: 'mean'
        }).reset_index()
        
        ad_summary['CPA'] = (ad_summary[col_cost] / ad_summary[col_lead]).replace([np.inf, -np.inf], np.nan).fillna(0)
        
        col_left, col_right = st.columns([1, 1])
        with col_left:
            st.write("**獲得数 vs 効率（バブルサイズ：消化金額）**")
            st.plotly_chart(px.scatter(ad_summary[ad_summary[col_lead] > 0], x=col_lead, y='CPA', size=col_cost, color=col_ad, hover_name=col_ad), use_container_width=True)
        with col_right:
            st.write("**頻度 vs 効率（バブルサイズ：消化金額）**")
            fig_f = px.scatter(ad_summary, x=col_freq, y='CPA', size=col_cost, color=col_ad, hover_name=col_ad)
            fig_f.add_vline(x=2.0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_f, use_container_width=True)

        # 詳細テーブルにCTR/CPMを追加
        disp_ad = ad_summary.sort_values('CPA').copy()
        disp_ad['消化金額'] = disp_ad[col_cost].map('¥{:,.0f}'.format)
        disp_ad['CPA'] = disp_ad['CPA'].map('¥{:,.0f}'.format)
        disp_ad['頻度'] = disp_ad[col_freq].map('{:.2f}'.format)
        disp_ad['CTR'] = (disp_ad[col_ctr] * 100).map('{:.2f}%'.format) # %表示に変換
        disp_ad['CPM'] = disp_ad[col_cpm].map('¥{:,.0f}'.format)
        
        st.write("**全指標一覧（CPAが良い順）**")
        st.dataframe(disp_ad[[col_ad, '消化金額', col_lead, 'CPA', '頻度', 'CTR', 'CPM']], use_container_width=True)

    except Exception as e:
        st.error(f"エラー: {e}")
