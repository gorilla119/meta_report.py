import streamlit as st
import pandas as pd
import plotly.express as px

# ページ設定
st.set_page_config(page_title="Meta広告ダッシュボード", layout="wide")

st.title("📊 Meta広告 パフォーマンス分析")
st.caption("CSVをアップロードして、日次CPAやキャンペーンごとの数値を可視化します")

# ファイルアップローダー
uploaded_file = st.file_uploader("Meta広告のレポートCSVを選択してください", type='csv')

if uploaded_file is not None:
    # CSVの読み込み
    df = pd.read_csv(uploaded_file)
    
    # 欠損値を0で埋める
    df = df.fillna(0)

    # 必要な列の自動特定（ヘッダー名が一部切れている場合を考慮）
    col_date = '日'
    col_campaign = 'キャンペーン名'
    col_cost = '消化金額 (JPY)' if '消化金額 (JPY)' in df.columns else '消化金額'
    col_lead = 'リード'

    # 日付列を日付型に変換
    df[col_date] = pd.to_datetime(df[col_date])

    # サイドバーでキャンペーンをフィルタリング
    st.sidebar.header("表示設定")
    all_campaigns = df[col_campaign].unique().tolist()
    selected_campaigns = st.sidebar.multiselect("キャンペーンを選択", all_campaigns, default=all_campaigns[:2])

    # データの絞り込み
    filtered_df = df[df[col_campaign].isin(selected_campaigns)].copy()

    # 指標の計算
    filtered_df['CPA'] = filtered_df[col_cost] / filtered_df[col_lead]
    filtered_df['CPA'] = filtered_df['CPA'].replace([float('inf'), -float('inf')], 0) # 0除算対策

    # メイン表示
    col1, col2, col3 = st.columns(3)
    total_cost = filtered_df[col_cost].sum()
    total_leads = filtered_df[col_lead].sum()
    avg_cpa = total_cost / total_leads if total_leads > 0 else 0
    
    col1.metric("総消化金額", f"¥{int(total_cost):,}")
    col2.metric("総リード数", f"{int(total_leads):,}")
    col3.metric("平均CPA", f"¥{int(avg_cpa):,}")

    st.divider()

    # グラフ：日次CPA推移
    st.subheader("日次CPA推移")
    if not filtered_df.empty:
        fig = px.line(filtered_df, x=col_date, y='CPA', color=col_campaign,
                      title="キャンペーン別の日次CPA推移",
                      labels={'CPA': 'CPA (円)', col_date: '日付'},
                      markers=True)
        st.plotly_chart(fig, use_container_width=True)

    # サマリーテーブル
    st.subheader("キャンペーン別サマリー")
    summary = filtered_df.groupby(col_campaign).agg({
        col_cost: 'sum',
        col_lead: 'sum'
    }).reset_index()
    summary['平均CPA'] = summary[col_cost] / summary[col_lead]
    summary['平均CPA'] = summary['平均CPA'].apply(lambda x: f"¥{int(x):,}" if x > 0 else "¥0")
    
    st.dataframe(summary, use_container_width=True)

else:
    st.info("左側の『Browse files』ボタン、またはドラッグ＆ドロップでCSVファイルをアップロードしてください。")
    st.markdown("""
    ### 使い方
    1. Meta広告マネージャーから「日別」のレポートを書き出す（CSV形式）。
    2. 上記のアップローダーにファイルを放り込む。
    3. 見たいキャンペーンを左のメニューから選ぶと、グラフが更新されます。
    """)
