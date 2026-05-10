import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ページ設定
st.set_page_config(page_title="Meta広告 統合分析ダッシュボード", layout="wide")

st.title("🚀 Meta広告 統合分析ダッシュボード")

uploaded_file = st.file_uploader("Meta広告のレポートCSVを選択してください", type='csv')

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df = df.fillna(0)

        # 列名の設定
        col_date = '日'
        col_campaign = 'キャンペーン名'
        col_ad = '広告名'
        col_cost = '消化金額 (JPY)' if '消化金額 (JPY)' in df.columns else '消化金額'
        col_lead = 'リード'

        # 日付変換
        df[col_date] = pd.to_datetime(df[col_date])

        # サイドバーでキャンペーン絞り込み
        st.sidebar.header("表示設定")
        all_campaigns = df[col_campaign].unique().tolist()
        selected_campaigns = st.sidebar.multiselect("キャンペーン選択", all_campaigns, default=all_campaigns[:1])
        
        # 絞り込みデータ
        f_df = df[df[col_campaign].isin(selected_campaigns)].copy()

        # --- 1. 日別集計（グラフ用） ---
        df_daily = f_df.groupby([col_date, col_campaign]).agg({col_cost: 'sum', col_lead: 'sum'}).reset_index()
        df_daily = df_daily.sort_values(by=[col_campaign, col_date])
        df_daily['CPA'] = (df_daily[col_cost] / df_daily[col_lead]).replace([np.inf, -np.inf], np.nan).fillna(0)

        # --- 2. クリエイティブ集計（分析用） ---
        ad_summary = f_df.groupby(col_ad).agg({col_cost: 'sum', col_lead: 'sum'}).reset_index()
        ad_summary['CPA'] = (ad_summary[col_cost] / ad_summary[col_lead]).replace([np.inf, -np.inf], np.nan).fillna(0)
        ad_summary = ad_summary.sort_values('CPA', ascending=True)

        # --- メイン画面表示 ---
        # サマリー
        c1, c2, c3 = st.columns(3)
        t_cost = f_df[col_cost].sum()
        t_leads = f_df[col_lead].sum()
        a_cpa = t_cost / t_leads if t_leads > 0 else 0
        c1.metric("総消化金額", f"¥{int(t_cost):,}")
        c2.metric("総リード数", f"{int(t_leads):,}")
        c3.metric("平均CPA", f"¥{int(a_cpa):,}")

        st.divider()

        # セクション1：日次推移
        st.subheader("📈 日次CPA推移")
        fig_line = px.line(df_daily, x=col_date, y='CPA', color=col_campaign, markers=True, title="日ごとの効率変化")
        fig_line.update_xaxes(type='date', tickformat='%m/%d')
        st.plotly_chart(fig_line, use_container_width=True)

        st.divider()

        # セクション2：クリエイティブ分析
        st.subheader("🎨 クリエイティブ別パフォーマンス")
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.write("CPAが良い順（安く取れている順）")
            # 表の表示
            disp_ad = ad_summary.copy()
            disp_ad['消化金額'] = disp_ad[col_cost].map('¥{:,.0f}'.format)
            disp_ad['CPA'] = disp_ad['CPA'].map('¥{:,.0f}'.format)
            st.dataframe(disp_ad[[col_ad, '消化金額', col_lead, 'CPA']], use_container_width=True)

        with col_right:
            st.write("獲得数 vs 効率（円の大きさは消化金額）")
            fig_scatter = px.scatter(ad_summary[ad_summary[col_lead] > 0], x=col_lead, y='CPA', size=col_cost, color=col_ad, hover_name=col_ad)
            st.plotly_chart(fig_scatter, use_container_width=True)

    except Exception as e:
        st.error(f"読み込みエラー: {e}")
else:
    st.info("CSVファイルをアップロードしてください。")
