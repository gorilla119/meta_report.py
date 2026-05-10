import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import date, timedelta

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
        col_lead_orig = get_col(['リード'])
        col_app_orig = get_col(['アプリのインストール', 'アプリインストール'])

        if any(v is None for v in [col_date, col_campaign, col_ad, col_cost]):
            st.error("CSVに必要な列が見つかりません。")
            st.stop()

        # データ準備
        df[col_date] = pd.to_datetime(df[col_date])
        df['獲得数'] = df.apply(lambda r: r[col_app_orig] if 'app' in str(r[col_campaign]).lower() and col_app_orig else (r[col_lead_orig] if col_lead_orig else 0), axis=1)

        # --- サイドバー：日付選択の範囲を2026年1月からに制限 ---
        st.sidebar.header("表示設定")
        
        # 制限範囲の設定
        limit_start = date(2026, 1, 1)
        data_max = df[col_date].max().date()
        
        # デフォルト選択範囲を「直近30日間」か「データがある範囲」にする
        default_start = max(limit_start, data_max - timedelta(days=30))
        
        date_range = st.sidebar.date_input(
            "分析期間を選択",
            [default_start, data_max],
            min_value=limit_start, # 1970年まで戻らないように制限
            max_value=data_max
        )

        selected_campaigns = st.sidebar.multiselect("キャンペーン選択", df[col_campaign].unique().tolist(), default=df[col_campaign].unique().tolist()[:1])

        # フィルタリング
        if len(date_range) == 2:
            start_date, end_date = date_range
            mask = (df[col_date].dt.date >= start_date) & (df[col_date].dt.date <= end_date) & (df[col_campaign].isin(selected_campaigns))
            f_df = df[mask].copy()
        else:
            st.stop()

        # --- 表示エリア（グラフ・分析） ---
        # (以前の集計・グラフ・散布図ロジックをここに継続)
        df_daily = f_df.groupby([col_date, col_campaign]).agg({col_cost: 'sum', '獲得数': 'sum'}).reset_index()
        df_daily['CPA'] = (df_daily[col_cost] / df_daily['獲得数']).replace([np.inf, -np.inf], 0).fillna(0)

        st.subheader(f"📈 時系列推移 ({start_date} 〜 {end_date})")
        fig_line = px.line(df_daily, x=col_date, y='CPA', color=col_campaign, markers=True)
        # 土日の網掛け
        curr = pd.to_datetime(start_date)
        while curr <= pd.to_datetime(end_date):
            if curr.weekday() == 5:
                fig_line.add_vrect(x0=curr.strftime('%Y-%m-%d'), x1=(curr + timedelta(days=1)).strftime('%Y-%m-%d'), fillcolor="gray", opacity=0.1, line_width=0)
            curr += timedelta(days=1)
        st.plotly_chart(fig_line, use_container_width=True)

        st.divider()

        # クリエイティブ集計 & CPM計算
        agg_map = {col_cost: 'sum', '獲得数': 'sum', col_imp: 'sum'}
        if col_freq: agg_map[col_freq] = 'mean'
        if col_ctr: agg_map[col_ctr] = 'mean'
        ad_summary = f_df.groupby(col_ad).agg(agg_map).reset_index()
        ad_summary['CPA'] = (ad_summary[col_cost] / ad_summary['獲得数']).replace([np.inf, -np.inf], 0).fillna(0)
        ad_summary['CPM'] = (ad_summary[col_cost] / ad_summary[col_imp] * 1000).replace([np.inf, -np.inf], 0).fillna(0)

        st.subheader("🎨 クリエイティブ詳細")
        disp = ad_summary.sort_values('CPA').copy()
        disp['消化金額'] = disp[col_cost].map('¥{:,.0f}'.format)
        disp['CPA'] = disp['CPA'].map('¥{:,.0f}'.format)
        disp['CPM'] = disp['CPM'].map('¥{:,.0f}'.format)
        st.dataframe(disp[[col_ad, '消化金額', '獲得数', 'CPA', 'CPM']], use_container_width=True)

        # --- 運用判断メモ ---
        st.divider()
        st.subheader("📝 広告停止の「鉄板」判断基準")
        
        m1, m2, m3 = st.columns(3)
        with m1:
            st.error("### 1. CPAの限界値\n目標CPAの**1.5倍を3日連続**で超えたら、そのクリエイティブは「負け」と判断して停止。")
        with m2:
            st.warning("### 2. フリークエンシー\n頻度が**2.0〜2.5**を超え、CPAが上昇し始めたら「摩耗」。内容が良くても休ませるか差し替え。")
        with m3:
            st.info("### 3. CPMとCTRの逆転\nCPMが上がっているのにCTRが下がっているなら、**Metaからの評価が最悪**な状態。即刻停止。")

    except Exception as e:
        st.error(f"エラー: {e}")
