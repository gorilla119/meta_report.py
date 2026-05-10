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

        # 列名の特定
        def get_col(keywords):
            for col in df.columns:
                if any(k in col for k in keywords): return col
            return None

        col_date = get_col(['日'])
        col_campaign = get_col(['キャンペーン名'])
        col_ad = get_col(['広告名'])
        col_cost = get_col(['消化金額'])
        col_freq = get_col(['フリークエンシー'])
        col_imp = get_col(['インプレッション'])
        col_ctr = get_col(['CTR'])
        col_lead_orig = get_col(['リード'])
        col_app_orig = get_col(['アプリのインストール', 'アプリインストール'])

        # 必須チェック
        essential = {"日": col_date, "キャンペーン": col_campaign, "広告名": col_ad, "消化金額": col_cost}
        if any(v is None for v in essential.values()):
            st.error("CSVに必要な列が見つかりません。")
            st.stop()

        # データ準備
        df[col_date] = pd.to_datetime(df[col_date])
        df['獲得数'] = df.apply(lambda r: r[col_app_orig] if 'app' in str(r[col_campaign]).lower() and col_app_orig else (r[col_lead_orig] if col_lead_orig else 0), axis=1)

        # --- サイドバー：日付選択とキャンペーン選択 ---
        min_date_val = df[col_date].min().date()
        max_date_val = df[col_date].max().date()
        
        st.sidebar.header("表示設定")
        date_range = st.sidebar.date_input("分析期間を選択", [min_date_val, max_date_val], min_value=min_date_val, max_value=max_date_val)
        
        all_campaigns = df[col_campaign].unique().tolist()
        selected_campaigns = st.sidebar.multiselect("キャンペーン選択", all_campaigns, default=all_campaigns[:1])

        # フィルタリング適用
        if len(date_range) == 2:
            start_date, end_date = date_range
            mask = (df[col_date].dt.date >= start_date) & (df[col_date].dt.date <= end_date) & (df[col_campaign].isin(selected_campaigns))
            f_df = df[mask].copy()
        else:
            st.stop()

        # --- 1. 時系列グラフ ---
        df_daily = f_df.groupby([col_date, col_campaign]).agg({col_cost: 'sum', '獲得数': 'sum'}).reset_index()
        df_daily['CPA'] = (df_daily[col_cost] / df_daily['獲得数']).replace([np.inf, -np.inf], 0).fillna(0)

        st.subheader(f"📈 時系列推移 ({start_date} 〜 {end_date})")
        fig_line = px.line(df_daily, x=col_date, y='CPA', color=col_campaign, markers=True)
        
        curr = pd.to_datetime(start_date)
        while curr <= pd.to_datetime(end_date):
            if curr.weekday() == 5:
                fig_line.add_vrect(x0=curr.strftime('%Y-%m-%d'), x1=(curr + timedelta(days=1)).strftime('%Y-%m-%d'), fillcolor="gray", opacity=0.1, line_width=0)
            curr += timedelta(days=1)
        st.plotly_chart(fig_line, use_container_width=True)

        st.divider()

        # --- 2. クリエイティブ分析 ---
        st.subheader("🎨 クリエイティブ別分析")
        agg_map = {col_cost: 'sum', '獲得数': 'sum', col_imp: 'sum'}
        if col_freq: agg_map[col_freq] = 'mean'
        if col_ctr: agg_map[col_ctr] = 'mean'
        
        ad_summary = f_df.groupby(col_ad).agg(agg_map).reset_index()
        ad_summary['CPA'] = (ad_summary[col_cost] / ad_summary['獲得数']).replace([np.inf, -np.inf], 0).fillna(0)
        ad_summary['CPM'] = (ad_summary[col_cost] / ad_summary[col_imp] * 1000).replace([np.inf, -np.inf], 0).fillna(0)

        disp = ad_summary.sort_values('CPA').copy()
        disp['消化金額'] = disp[col_cost].map('¥{:,.0f}'.format)
        disp['CPA'] = disp['CPA'].map('¥{:,.0f}'.format)
        disp['CPM'] = disp['CPM'].map('¥{:,.0f}'.format)
        if col_freq: disp['頻度'] = disp[col_freq].map('{:.2f}'.format)
        if col_ctr: disp['CTR'] = (disp[col_ctr] * 100).map('{:.2f}%'.format)

        st.dataframe(disp[[col_ad, '消化金額', '獲得数', 'CPA', 'CPM'] + ([f for f in ['頻度', 'CTR'] if f in disp.columns])], use_container_width=True)

        # --- 3. 運用メモエリア ---
        st.divider()
        st.subheader("📝 広告停止の判断基準（メモ）")
        
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.info("**1. CPA（獲得単価）**\n許容CPAの1.5倍〜2倍を3日間継続して超えたら停止を検討。")
        with m_col2:
            st.warning("**2. フリークエンシー（頻度）**\n数値が2.0〜2.5を超え、かつCPAが悪化し始めたら「飽き」のサイン。停止して新クリエイティブへ。")
        with m_col3:
            st.success("**3. CTR & CPM**\nCTRが低すぎる＝画像が弱い。CPMが急騰＝ターゲットが競合過多。これらが悪化しCPAも高いなら即停止。")

    except Exception as e:
        st.error(f"エラー: {e}")
