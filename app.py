import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import date, timedelta

st.set_page_config(page_title="Meta広告 統合分析ボード", layout="wide")
st.title("🚀 Meta広告 統合分析ダッシュボード")

uploaded_file = st.file_uploader("Meta広告のレポートCSVを選択してください", type='csv')

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df = df.fillna(0)

        # 1. 列名の特定
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

        # 2. データ前処理
        df[col_date] = pd.to_datetime(df[col_date])
        df['獲得数'] = df.apply(lambda r: r[col_app_orig] if 'app' in str(r[col_campaign]).lower() and col_app_orig else (r[col_lead_orig] if col_lead_orig else 0), axis=1)

        # 3. サイドバー設定（カレンダーの初期値をCSVのデータに合わせる）
        st.sidebar.header("表示設定")
        
        # CSV内の実際の日付範囲を取得
        data_min = df[col_date].min().date()
        data_max = df[col_date].max().date()
        
        # 制限の開始日（2026年1月1日以降、かつCSVにデータがある日）
        limit_start = date(2026, 1, 1)
        
        # もしCSVのデータがすべて2026年より前なら、警告を出してCSVの最小値を使う
        if data_max < limit_start:
            st.warning(f"アップロードされたデータは2026年以前のものです。期間制限を解除して表示します。")
            limit_start = data_min

        date_range = st.sidebar.date_input(
            "分析期間を選択", 
            [data_min, data_max], # 初期値をCSVの全期間にする
            min_value=limit_start, 
            max_value=data_max
        )

        all_campaigns = df[col_campaign].unique().tolist()
        selected_campaigns = st.sidebar.multiselect("キャンペーン選択", all_campaigns, default=all_campaigns[:1])

        # 4. フィルタリング実行
        if len(date_range) == 2:
            start_d, end_d = date_range
            mask = (df[col_date].dt.date >= start_d) & (df[col_date].dt.date <= end_d) & (df[col_campaign].isin(selected_campaigns))
            f_df = df[mask].copy()
        else:
            st.info("期間を2箇所（開始日と終了日）選択してください。")
            st.stop()

        if f_df.empty:
            st.warning("選択された条件に合致するデータがありません。期間やキャンペーンを変えてみてください。")
            st.stop()

        # --- 以降、表示処理（グラフ・散布図・表・メモ） ---
        # (以前のコードと同様の集計とpx.line, px.scatterを記述)
        
        # 日次グラフ
        df_daily = f_df.groupby([col_date, col_campaign]).agg({col_cost: 'sum', '獲得数': 'sum'}).reset_index()
        df_daily['CPA'] = (df_daily[col_cost] / df_daily['獲得数']).replace([np.inf, -np.inf], 0).fillna(0)
        
        st.subheader(f"📈 時系列推移 ({start_d} 〜 {end_d})")
        fig_line = px.line(df_daily, x=col_date, y='CPA', color=col_campaign, markers=True)
        # 土日の網掛け
        curr = pd.to_datetime(start_d)
        while curr <= pd.to_datetime(end_d):
            if curr.weekday() == 5:
                fig_line.add_vrect(x0=curr.strftime('%Y-%m-%d'), x1=(curr + timedelta(days=1)).strftime('%Y-%m-%d'), fillcolor="gray", opacity=0.1, line_width=0)
            curr += timedelta(days=1)
        st.plotly_chart(fig_line, use_container_width=True)

        # クリエイティブ分析
        st.divider()
        st.subheader("🎨 クリエイティブ分析")
        agg_map = {col_cost: 'sum', '獲得数': 'sum', col_imp: 'sum'}
        if col_freq: agg_map[col_freq] = 'mean'
        if col_ctr: agg_map[col_ctr] = 'mean'
        ad_summary = f_df.groupby(col_ad).agg(agg_map).reset_index()
        ad_summary['CPA'] = (ad_summary[col_cost] / ad_summary['獲得数']).replace([np.inf, -np.inf], 0).fillna(0)
        ad_summary['CPM'] = (ad_summary[col_cost] / ad_summary[col_imp] * 1000).replace([np.inf, -np.inf], 0).fillna(0)

        c1, c2 = st.columns(2)
        with c1:
            st.write("**獲得数 vs CPA**")
            st.plotly_chart(px.scatter(ad_summary[ad_summary['獲得数'] > 0], x='獲得数', y='CPA', size=col_cost, color=col_ad, hover_name=col_ad), use_container_width=True)
        with c2:
            if col_freq:
                st.write("**頻度 vs CPA**")
                fig_f = px.scatter(ad_summary, x=col_freq, y='CPA', size=col_cost, color=col_ad, hover_name=col_ad)
                fig_f.add_vline(x=2.0, line_dash="dash", line_color="red")
                st.plotly_chart(fig_f, use_container_width=True)

        st.write("**詳細テーブル**")
        disp = ad_summary.sort_values('CPA').copy()
        disp['消化金額'] = disp[col_cost].map('¥{:,.0f}'.format)
        disp['CPA'] = disp['CPA'].map('¥{:,.0f}'.format)
        disp['CPM'] = disp['CPM'].map('¥{:,.0f}'.format)
        st.dataframe(disp[[col_ad, '消化金額', '獲得数', 'CPA', 'CPM']], use_container_width=True)

        # 運用メモ
        st.divider()
        st.subheader("📝 運用判断メモ")
        st.info("CPAが目標の1.5倍を3日超えたら停止 / 頻度2.0超えで摩耗注意")

    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
