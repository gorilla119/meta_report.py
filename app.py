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

        # 列名の特定用キーワード
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
        
        # 成果列の候補（アプリインストール or リード）
        col_lead_orig = get_col(['リード'])
        col_app_orig = get_col(['アプリのインストール', 'アプリインストール'])

        # 必須チェック
        essential = {"日": col_date, "キャンペーン": col_campaign, "広告名": col_ad, "消化金額": col_cost}
        missing = [k for k, v in essential.items() if v is None]
        if missing:
            st.error(f"CSVに必要な列が見つかりません: {missing}")
            st.stop()

        # --- 成果（獲得数）をキャンペーン名で切り替えるロジック ---
        def get_result_count(row):
            campaign_name = str(row[col_campaign]).lower()
            if 'app' in campaign_name:
                return row[col_app_orig] if col_app_orig else 0
            else:
                return row[col_lead_orig] if col_lead_orig else 0

        # 新しい「獲得数」列を作成
        df['獲得数'] = df.apply(get_result_count, axis=1)
        col_result = '獲得数'

        df[col_date] = pd.to_datetime(df[col_date])
        
        # サイドバーで絞り込み
        all_campaigns = df[col_campaign].unique().tolist()
        selected_campaigns = st.sidebar.multiselect("キャンペーン選択", all_campaigns, default=all_campaigns[:1])
        f_df = df[df[col_campaign].isin(selected_campaigns)].copy()

        # --- 1. 日別集計（グラフ） ---
        df_daily = f_df.groupby([col_date, col_campaign]).agg({col_cost: 'sum', col_result: 'sum'}).reset_index()
        df_daily['CPA'] = (df_daily[col_cost] / df_daily[col_result]).replace([np.inf, -np.inf], 0).fillna(0)

        st.subheader("📈 時系列パフォーマンス推移")
        min_d, max_d = df_daily[col_date].min(), df_daily[col_date].max()
        
        fig_line = px.line(df_daily, x=col_date, y='CPA', color=col_campaign, markers=True, title="日次CPA（リード/インストール混在対応）")
        
        # 土日の網掛け
        curr = min_d
        while curr <= max_d:
            if curr.weekday() == 5:
                fig_line.add_vrect(x0=curr.strftime('%Y-%m-%d'), x1=(curr + timedelta(days=1)).strftime('%Y-%m-%d'), fillcolor="gray", opacity=0.1, line_width=0)
            curr += timedelta(days=1)
        st.plotly_chart(fig_line, use_container_width=True)

        st.divider()

        # --- 2. クリエイティブ分析 ---
        st.subheader("🎨 クリエイティブ別分析")
        
        agg_map = {col_cost: 'sum', col_result: 'sum', col_imp: 'sum'}
        if col_freq: agg_map[col_freq] = 'mean'
        if col_ctr: agg_map[col_ctr] = 'mean'

        ad_summary = f_df.groupby(col_ad).agg(agg_map).reset_index()
        
        # 指標計算
        ad_summary['CPA'] = (ad_summary[col_cost] / ad_summary[col_result]).replace([np.inf, -np.inf], 0).fillna(0)
        ad_summary['CPM'] = (ad_summary[col_cost] / ad_summary[col_imp] * 1000).replace([np.inf, -np.inf], 0).fillna(0)
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**獲得数 vs CPA（獲得規模の確認）**")
            st.plotly_chart(px.scatter(ad_summary[ad_summary[col_result] > 0], x=col_result, y='CPA', size=col_cost, color=col_ad, hover_name=col_ad), use_container_width=True)
        with c2:
            if col_freq:
                st.write("**頻度 vs CPA（摩耗チェック）**")
                fig_f = px.scatter(ad_summary, x=col_freq, y='CPA', size=col_cost, color=col_ad, hover_name=col_ad)
                fig_f.add_vline(x=2.0, line_dash="dash", line_color="red")
                st.plotly_chart(fig_f, use_container_width=True)

        # 詳細テーブル
        disp = ad_summary.sort_values('CPA').copy()
        disp['消化金額'] = disp[col_cost].map('¥{:,.0f}'.format)
        disp['CPA'] = disp['CPA'].map('¥{:,.0f}'.format)
        disp['CPM'] = disp['CPM'].map('¥{:,.0f}'.format)
        if col_freq: disp['頻度'] = disp[col_freq].map('{:.2f}'.format)
        if col_ctr: disp['CTR'] = (disp[col_ctr] * 100).map('{:.2f}%'.format)
        
        st.write("**パフォーマンス一覧（CPA順）**")
        show_cols = [col_ad, '消化金額', col_result, 'CPA', 'CPM']
        if col_freq: show_cols.append('頻度')
        if col_ctr: show_cols.append('CTR')
        st.dataframe(disp[show_cols], use_container_width=True)

    except Exception as e:
        st.error(f"エラー: {e}")
