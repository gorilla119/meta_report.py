import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Meta広告分析：クリエイティブ編", layout="wide")
st.title("🎨 Meta広告 クリエイティブ分析")

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
        col_ctr = 'CTR(すべて)' if 'CTR(すべて)' in df.columns else 'CTR'

        # 日付変換
        df[col_date] = pd.to_datetime(df[col_date])

        # サイドバーでキャンペーン絞り込み
        st.sidebar.header("表示設定")
        selected_campaigns = st.sidebar.multiselect("キャンペーン選択", df[col_campaign].unique().tolist(), default=df[col_campaign].unique().tolist()[:1])
        f_df = df[df[col_campaign].isin(selected_campaigns)].copy()

        # --- クリエイティブ単位の集計 ---
        ad_summary = f_df.groupby(col_ad).agg({
            col_cost: 'sum',
            col_lead: 'sum',
            'インプレッション': 'sum',
            'クリック(すべて)': 'sum'
        }).reset_index()

        # 指標計算
        ad_summary['CPA'] = (ad_summary[col_cost] / ad_summary[col_lead]).replace([np.inf, -np.inf], 0).fillna(0)
        ad_summary['CTR'] = (ad_summary['クリック(すべて)'] / ad_summary['インプレッション']).fillna(0)
        
        # CPAが良い順に並び替え
        ad_summary = ad_summary.sort_values('CPA', ascending=True)

        # メイン表示
        st.subheader("🚀 クリエイティブ別パフォーマンス（CPA順）")
        
        # 表の表示（見た目を整える）
        styled_summary = ad_summary.copy()
        styled_summary['消化金額'] = styled_summary[col_cost].map('¥{:,.0f}'.format)
        styled_summary['CPA'] = styled_summary['CPA'].map('¥{:,.0f}'.format)
        styled_summary['CTR'] = (styled_summary['CTR'] * 100).map('{:.2f}%'.format)
        
        st.dataframe(styled_summary[[col_ad, '消化金額', col_lead, 'CPA', 'CTR']], use_container_width=True)

        st.divider()

        # --- 散布図：効率（CPA） vs 規模（リード数） ---
        st.subheader("📍 獲得数と効率のマトリクス分析")
        st.caption("右下にあるほど『安くたくさん取れている』優秀なクリエイティブ、左上にあるほど『高く少ししか取れていない』改善が必要なクリエイティブです。")
        
        # バブルチャート（円の大きさは消化金額）
        fig_scatter = px.scatter(
            ad_summary[ad_summary[col_lead] > 0], # 獲得があるものに限定
            x=col_lead, 
            y='CPA',
            size=col_cost,
            color=col_ad,
            hover_name=col_ad,
            labels={col_lead: 'リード獲得数', 'CPA': 'CPA (円)'},
            title="クリエイティブ別マトリクス"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    except Exception as e:
        st.error(f"エラー: {e}")
else:
    st.info("CSVをアップロードしてください。")
