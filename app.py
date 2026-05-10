import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ページ設定
st.set_page_config(page_title="Meta広告ダッシュボード", layout="wide")

st.title("📊 Meta広告 パフォーマンス分析")
st.caption("CSVをアップロードして、日次CPAやキャンペーンごとの数値を可視化します")

# ファイルアップローダー
uploaded_file = st.file_uploader("Meta広告のレポートCSVを選択してください", type='csv')

if uploaded_file is not None:
    try:
        # CSVの読み込み
        df = pd.read_csv(uploaded_file)
        df = df.fillna(0)

        # 列名の特定
        col_date = '日'
        col_campaign = 'キャンペーン名'
        col_cost = '消化金額 (JPY)' if '消化金額 (JPY)' in df.columns else '消化金額'
        col_lead = 'リード'

        # 日付変換
        df[col_date] = pd.to_datetime(df[col_date])

        # サイドバー設定
        st.sidebar.header("表示設定")
        all_campaigns = df[col_campaign].unique().tolist()
        selected_campaigns = st.sidebar.multiselect("キャンペーンを選択", all_campaigns, default=all_campaigns[:2])

        # 絞り込み
        filtered_df = df[df[col_campaign].isin(selected_campaigns)].copy()

        # 【修正ポイント】CPA計算（0除算や無限大を安全に処理）
        filtered_df['CPA'] = filtered_df[col_cost] / filtered_df[col_lead]
        filtered_df['CPA'] = filtered_df['CPA'].replace([np.inf, -np.inf], np.nan).fillna(0)

        # サマリー数値
        col1, col2, col3 = st.columns(3)
        total_cost = filtered_df[col_cost].sum()
        total_leads = filtered_df[col_lead].sum()
        avg_cpa = total_cost / total_leads if total_leads > 0 else 0
        
        col1.metric("総消化金額", f"¥{int(total_cost):,}")
        col2.metric("総リード数", f"{int(total_leads):,}")
        col3.metric("平均CPA", f"¥{int(avg_cpa):,}")

        st.divider()

        # グラフ
        st.subheader("日次CPA推移")
        if not filtered_df.empty:
            fig = px.line(filtered_df, x=col_date, y='CPA', color=col_campaign,
                          title="キャンペーン別の日次CPA推移",
                          labels={'CPA': 'CPA (円)', col_date: '日付'},
                          markers=True)
            st.plotly_chart(fig, use_container_width=True)

        # 【修正ポイント】サマリーテーブルの書式設定
        st.subheader("キャンペーン別サマリー")
        summary = filtered_df.groupby(col_campaign).agg({
            col_cost: 'sum',
            col_lead: 'sum'
        }).reset_index()
        
        # 安全にCPAを計算
        summary['平均CPA_数値'] = summary[col_cost] / summary[col_lead]
        
        # 表示用のフォーマット（エラー回避）
        def format_cpa(val):
            if np.isinf(val) or np.isnan(val) or val <= 0:
                return "¥0 (CVなし)"
            # あまりに巨大な数字（異常値）もカット
            if val > 1000000000:
                return "上限超過"
            return f"¥{int(val):,}"

        summary['平均CPA'] = summary['平均CPA_数値'].apply(format_cpa)
        
        # 見栄えのために不要な列を隠して表示
        display_summary = summary[[col_campaign, col_cost, col_lead, '平均CPA']]
        st.dataframe(display_summary, use_container_width=True)

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
        st.info("CSVのヘッダー名が正しいか、またはデータが空でないか確認してください。")

else:
    st.info("CSVファイルをアップロードしてください。")
