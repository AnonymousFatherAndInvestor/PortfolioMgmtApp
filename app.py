"""
株式ポートフォリオ管理Webアプリ
メインアプリケーション
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Dict, Any, List
import logging

# ローカルモジュールのインポート
from modules.data_loader import load_portfolio_data, validate_portfolio_data, display_data_summary
from modules.price_fetcher import (
    cached_get_current_prices, cached_get_exchange_rates, 
    determine_currency_from_ticker, convert_to_jpy, get_historical_data, get_stock_chart_data
)
from modules.pnl_calculator import (
    calculate_portfolio_pnl, calculate_portfolio_summary,
    calculate_sector_allocation, calculate_performance_metrics
)
from modules.country_fetcher import cached_get_multiple_ticker_countries
from modules.risk_calculator import (
    calculate_portfolio_risk, calculate_var_cvar, stress_test_scenario
)
from modules.visualizer import (
    create_pnl_chart, create_allocation_pie, create_correlation_heatmap,
    create_var_distribution, create_performance_summary_chart, create_sector_allocation_chart,
    create_price_history_chart, create_stock_candlestick_chart
)
from utils.currency_mapper import get_currency_mapping, get_market_info
from utils.helpers import (
    format_currency, format_percentage, display_error_message,
    display_success_message, display_warning_message, show_loading_spinner,
    calculate_returns
)

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main_dashboard():
    """メインダッシュボード"""
    st.set_page_config(
        page_title="ポートフォリオ管理",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # セッションステートの初期化
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = 0
    if 'uploaded_data' not in st.session_state:
        st.session_state.uploaded_data = None
    if 'portfolio_df' not in st.session_state:
        st.session_state.portfolio_df = None
    
    st.title("📊 株式ポートフォリオ管理ダッシュボード")
    st.markdown("---")
    
    # サイドバー：ファイルアップロード
    with st.sidebar:
        st.header("📁 データインポート")
        uploaded_file = st.file_uploader(
            "CSVファイルをアップロード",
            type=['csv'],
            help="ファイル形式: Ticker, Shares, AvgCostJPY"
        )
        
        if uploaded_file:
            st.success("ファイルが正常にアップロードされました！")
            
            # セッションステートにファイルデータを保存
            if st.session_state.uploaded_data != uploaded_file.getvalue():
                st.session_state.uploaded_data = uploaded_file.getvalue()
                st.session_state.portfolio_df = None  # データが変更されたらリセット
            
            # 簡易プレビュー
            try:
                preview_df = pd.read_csv(uploaded_file)
                uploaded_file.seek(0)  # ファイルポインタをリセット
                st.write("**データプレビュー:**")
                st.dataframe(preview_df.head(), use_container_width=True)
            except:
                pass
            
        st.markdown("---")
        st.subheader("📋 CSVファイル形式")
        st.code("""
Ticker,Shares,AvgCostJPY
AAPL,100,15000
MSFT,50,25000
7203.T,1000,800
        """)
    
    # メインコンテンツ
    if uploaded_file is not None:
        # セッションステートからデータを取得するか新規処理
        if st.session_state.portfolio_df is None:
            portfolio_df = validate_and_load_portfolio_data(uploaded_file)
            if portfolio_df is not None:
                st.session_state.portfolio_df = portfolio_df
        else:
            portfolio_df = st.session_state.portfolio_df
        
        if portfolio_df is not None:
            display_portfolio_dashboard(portfolio_df)
    else:
        display_welcome_page()


def validate_and_load_portfolio_data(uploaded_file) -> Optional[pd.DataFrame]:
    """ポートフォリオデータの検証と読み込み"""
    try:
        # CSVファイルの読み込み
        portfolio_df = load_portfolio_data(uploaded_file)
        
        if portfolio_df is not None:
            display_success_message(f"ポートフォリオデータを正常に読み込みました（{len(portfolio_df)}銘柄）")
            return portfolio_df
        else:
            return None
            
    except Exception as e:
        display_error_message(e, "ファイル読み込み中にエラーが発生しました")
        return None


def display_portfolio_dashboard(portfolio_df: pd.DataFrame):
    """ポートフォリオダッシュボードの表示"""
    
    try:
        # データサマリーの表示
        display_data_summary(portfolio_df)
        
        with show_loading_spinner("リアルタイムデータを取得中..."):
            # 1. 株価と為替レートを取得
            tickers = portfolio_df['Ticker'].tolist()
            current_prices = cached_get_current_prices(tuple(tickers))
            exchange_rates = cached_get_exchange_rates()
            
            # 2. 通貨マッピングを作成
            currency_mapping = get_currency_mapping(tickers)
            
            # 3. 損益計算
            pnl_df = calculate_portfolio_pnl(
                portfolio_df, current_prices, exchange_rates, currency_mapping
            )
            
            if pnl_df.empty:
                display_warning_message("損益計算ができませんでした。しばらく後に再試行してください。")
                return
        
        # ポートフォリオサマリーを計算
        portfolio_summary = calculate_portfolio_summary(pnl_df)
        
        # 基本メトリクス表示
        display_portfolio_metrics(portfolio_summary)
        
        st.markdown("---")
        
        # タブによる詳細表示
        tab_names = [
            "📈 パフォーマンス", "⚠️ リスク分析", "🌍 配分分析", 
            "📊 株価チャート", "🔍 詳細データ"
        ]
        
        # ユニークキーでタブを管理
        selected_tab = st.radio(
            "表示するタブを選択:",
            options=tab_names,
            index=st.session_state.current_tab,
            horizontal=True,
            key="tab_selector"
        )
        
        # 現在のタブインデックスを更新
        if selected_tab:
            st.session_state.current_tab = tab_names.index(selected_tab)
        
        st.markdown("---")
        
        # 選択されたタブの内容を表示
        if selected_tab == "📈 パフォーマンス":
            display_performance_analysis(pnl_df, portfolio_summary)
        elif selected_tab == "⚠️ リスク分析":
            display_risk_analysis(pnl_df, tickers, portfolio_df)
        elif selected_tab == "🌍 配分分析":
            display_allocation_analysis(pnl_df, tickers)
        elif selected_tab == "📊 株価チャート":
            display_stock_charts(tickers)
        elif selected_tab == "🔍 詳細データ":
            display_detailed_data(pnl_df, portfolio_df, tickers)
            
    except Exception as e:
        display_error_message(e, "ダッシュボード表示中にエラーが発生しました")


def display_portfolio_metrics(summary: Dict[str, float]):
    """ポートフォリオメトリクスの表示"""
    if not summary:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="総評価額",
            value=format_currency(summary.get('total_current_value_jpy', 0)),
            delta=format_currency(summary.get('total_pnl_amount_jpy', 0))
        )
    
    with col2:
        st.metric(
            label="総損益率",
            value=format_percentage(summary.get('overall_pnl_percentage', 0)),
            delta=f"{summary.get('profitable_positions', 0)}勝/{summary.get('losing_positions', 0)}敗"
        )
    
    with col3:
        st.metric(
            label="勝率",
            value=format_percentage(summary.get('win_rate', 0)),
            delta=f"平均ポジション: {format_currency(summary.get('average_position_size', 0))}"
        )
    
    with col4:
        best_ticker = summary.get('max_gain_ticker', '')
        worst_ticker = summary.get('max_loss_ticker', '')
        st.metric(
            label="最高/最低パフォーマンス",
            value=f"{best_ticker}: {format_percentage(summary.get('max_gain_percentage', 0))}",
            delta=f"{worst_ticker}: {format_percentage(summary.get('max_loss_percentage', 0))}"
        )


def display_performance_analysis(pnl_df: pd.DataFrame, summary: Dict[str, float]):
    """パフォーマンス分析の表示"""
    st.subheader("📈 パフォーマンス分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 損益チャート
        pnl_chart = create_pnl_chart(pnl_df)
        st.plotly_chart(pnl_chart, use_container_width=True)
    
    with col2:
        # 資産配分チャート
        allocation_chart = create_allocation_pie(pnl_df)
        st.plotly_chart(allocation_chart, use_container_width=True)
    
    # パフォーマンスサマリー
    if summary:
        performance_chart = create_performance_summary_chart(summary)
        st.plotly_chart(performance_chart, use_container_width=True)


def display_risk_analysis(pnl_df: pd.DataFrame, tickers: list, portfolio_df: pd.DataFrame):
    """リスク分析の表示"""
    st.subheader("⚠️ リスク分析")
    
    # セッションステートでリスク分析設定を管理
    if 'risk_analysis_period' not in st.session_state:
        st.session_state.risk_analysis_period = "1y"
    if 'risk_time_scale' not in st.session_state:
        st.session_state.risk_time_scale = "日次"
    
    # 設定UI
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.write("分析期間を選択してください：")
    with col2:
        analysis_period = st.selectbox(
            "データ期間",
            options=["1mo", "3mo", "6mo", "ytd", "1y", "2y", "5y"],
            index=["1mo", "3mo", "6mo", "ytd", "1y", "2y", "5y"].index(st.session_state.risk_analysis_period),
            help="相関分析・リスク指標計算に使用する過去データの期間",
            key="risk_analysis_period_selector"
        )
        st.session_state.risk_analysis_period = analysis_period
    
    with col3:
        time_scale = st.selectbox(
            "リスク時間軸",
            options=["日次", "月次", "年次"],
            index=["日次", "月次", "年次"].index(st.session_state.risk_time_scale),
            help="VaR/CVaRとストレステストの表示時間スケール",
            key="risk_time_scale_selector"
        )
        st.session_state.risk_time_scale = time_scale
    
    # 時間スケール変換係数を事前に計算
    def get_time_scale_factor(scale):
        if scale == "日次":
            return 1, "日"
        elif scale == "月次":
            return np.sqrt(20), "月"  # 20営業日
        elif scale == "年次":
            return np.sqrt(252), "年"  # 252営業日
        return 1, "日"
    
    scale_factor, scale_label = get_time_scale_factor(time_scale)
    
    try:
        with show_loading_spinner(f"過去{analysis_period}のデータを取得中..."):
            # 実際の過去データを取得
            historical_data = get_historical_data(tickers, period=analysis_period)
            
            if historical_data.empty:
                st.warning("過去データの取得に失敗しました。しばらく後に再試行してください。")
                return
            
            # データが少なすぎる場合の警告
            if len(historical_data) < 20:
                st.warning(f"データ期間が短すぎます（{len(historical_data)}日）。より長い期間を選択することをお勧めします。")
            
            # 日次リターンを計算
            returns_df = pd.DataFrame()
            for ticker in tickers:
                if ticker in historical_data.columns:
                    returns = calculate_returns(historical_data[ticker])
                    if not returns.empty:
                        returns_df[ticker] = returns
            
            if returns_df.empty:
                st.error("リターンデータの計算に失敗しました。")
                return
            
            st.info(f"📊 分析期間: {analysis_period} ({len(returns_df)}営業日のデータ)")
            
            # ポートフォリオ重みを計算
            total_value = pnl_df['current_value_jpy'].sum()
            weights = (pnl_df['current_value_jpy'] / total_value).values
            
            # データが揃っている銘柄のみでウェイトを再計算
            valid_tickers = [ticker for ticker in tickers if ticker in returns_df.columns]
            valid_pnl = pnl_df[pnl_df['ticker'].isin(valid_tickers)]
            
            if len(valid_tickers) != len(tickers):
                missing_tickers = set(tickers) - set(valid_tickers)
                st.warning(f"以下の銘柄のデータが不足しているため、分析から除外されます: {', '.join(missing_tickers)}")
            
            if len(valid_tickers) < 2:
                st.error("相関分析には少なくとも2銘柄のデータが必要です。")
                return
            
            # 有効な銘柄のウェイトを再計算
            valid_total_value = valid_pnl['current_value_jpy'].sum()
            valid_weights = (valid_pnl['current_value_jpy'] / valid_total_value).values
            
            # リスク指標計算
            risk_metrics = calculate_portfolio_risk(returns_df[valid_tickers], valid_weights)
            
            if risk_metrics:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📊 リスク指標")
                    portfolio_vol_scaled = risk_metrics.get('portfolio_volatility', 0) * scale_factor
                    st.metric(f"ポートフォリオボラティリティ（{scale_label}次）", 
                             format_percentage(portfolio_vol_scaled * 100))
                    st.metric("平均相関", 
                             f"{risk_metrics.get('average_correlation', 0):.3f}")
                    st.metric("分散効果", 
                             f"{risk_metrics.get('diversification_ratio', 1):.2f}x")
                    
                    # 個別銘柄ボラティリティの表示
                    with st.expander(f"個別銘柄ボラティリティ（{scale_label}次）"):
                        individual_vols = risk_metrics.get('individual_volatilities', pd.Series())
                        for ticker, vol in individual_vols.items():
                            vol_scaled = vol * scale_factor
                            st.write(f"**{ticker}**: {format_percentage(vol_scaled * 100)}")
                
                with col2:
                    # 相関ヒートマップ
                    if 'correlation_matrix' in risk_metrics:
                        corr_chart = create_correlation_heatmap(risk_metrics['correlation_matrix'])
                        st.plotly_chart(corr_chart, use_container_width=True)
            
            # ポートフォリオリターンを計算
            portfolio_returns = (returns_df[valid_tickers] * valid_weights).sum(axis=1)
            
            # VaR/CVaR計算
            var_metrics = calculate_var_cvar(pd.Series(portfolio_returns))
            
            if var_metrics:
                st.subheader(f"📉 VaR/CVaR分析（{scale_label}次）")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    var_95_scaled = var_metrics.get('VaR_95', 0) * scale_factor
                    st.metric(f"VaR (95%)", format_percentage(var_95_scaled * 100))
                
                with col2:
                    cvar_95_scaled = var_metrics.get('CVaR_95', 0) * scale_factor
                    st.metric(f"CVaR (95%)", format_percentage(cvar_95_scaled * 100))
                
                with col3:
                    var_99_scaled = var_metrics.get('VaR_99', 0) * scale_factor
                    st.metric(f"VaR (99%)", format_percentage(var_99_scaled * 100))
                
                with col4:
                    daily_vol = portfolio_returns.std()
                    scaled_vol = daily_vol * scale_factor
                    st.metric(f"{scale_label}率ボラティリティ", format_percentage(scaled_vol * 100))
                
                # VaR分布チャート（時間軸に応じてスケール）
                var_chart = create_var_distribution(pd.Series(portfolio_returns), var_metrics, scale_factor, scale_label)
                st.plotly_chart(var_chart, use_container_width=True)
                
                # ストレステスト
                st.subheader("🚨 ストレステスト")
                stress_results = stress_test_scenario(returns_df[valid_tickers], valid_weights, 
                                                     stress_factor=1.5, correlation_shock=0.8)
                
                if stress_results:
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        normal_vol = stress_results.get('normal_portfolio_vol', 0)
                        normal_vol_scaled = normal_vol * scale_factor
                        st.metric(f"通常時ボラティリティ（{scale_label}次）", format_percentage(normal_vol_scaled * 100))
                    
                    with col2:
                        stressed_vol = stress_results.get('stressed_portfolio_vol', 0)
                        stressed_vol_scaled = stressed_vol * scale_factor
                        st.metric(f"ストレス時ボラティリティ（{scale_label}次）", format_percentage(stressed_vol_scaled * 100))
                    
                    with col3:
                        stress_multiplier = stress_results.get('stress_multiplier', 1)
                        st.metric("ストレス倍率", f"{stress_multiplier:.2f}x")
                    
                    with col4:
                        # ストレス時の想定損失（95%信頼区間、約2標準偏差）
                        stress_loss_95 = -stressed_vol_scaled * 1.96  # 負の値として表示
                        st.metric(f"想定最大損失 95%（{scale_label}次）", format_percentage(stress_loss_95 * 100))
                    
                    # ストレステスト詳細
                    with st.expander("🔍 ストレステスト詳細"):
                        st.write("**ストレス条件:**")
                        st.write(f"- ボラティリティ増加倍率: {stress_results.get('stress_factor', 1.5):.1f}倍")
                        st.write(f"- ストレス時相関係数: {stress_results.get('correlation_shock', 0.8):.1f}")
                        st.write(f"- 通常時ポートフォリオボラティリティ（年率）: {format_percentage(normal_vol * 100)}")
                        st.write(f"- ストレス時ポートフォリオボラティリティ（年率）: {format_percentage(stressed_vol * 100)}")
                        
                        st.write("**想定損失シナリオ（ストレス時）:**")
                        scenarios = [
                            ("68%信頼区間（1σ）", -stressed_vol_scaled * 1.0, "約68%の確率で損失がこの範囲内"),
                            ("95%信頼区間（1.96σ）", -stressed_vol_scaled * 1.96, "約95%の確率で損失がこの範囲内"),
                            ("99%信頼区間（2.58σ）", -stressed_vol_scaled * 2.58, "約99%の確率で損失がこの範囲内"),
                            ("99.7%信頼区間（3σ）", -stressed_vol_scaled * 3.0, "約99.7%の確率で損失がこの範囲内")
                        ]
                        
                        for scenario_name, loss_pct, description in scenarios:
                            st.write(f"- **{scenario_name}**: {format_percentage(loss_pct * 100)} ({description})")
                
                # 統計情報の詳細表示
                with st.expander(f"📈 詳細統計（{scale_label}次ベース）"):
                    stats_col1, stats_col2 = st.columns(2)
                    
                    with stats_col1:
                        st.write(f"**リターン統計（{scale_label}次）:**")
                        
                        # 時間軸に応じた統計表示
                        if time_scale == "日次":
                            avg_return_scaled = portfolio_returns.mean()
                            max_return_scaled = portfolio_returns.max()
                            min_return_scaled = portfolio_returns.min()
                            st.write(f"平均日次リターン: {format_percentage(avg_return_scaled * 100)}")
                            st.write(f"最大日次リターン: {format_percentage(max_return_scaled * 100)}")
                            st.write(f"最小日次リターン: {format_percentage(min_return_scaled * 100)}")
                            st.write(f"年率リターン（参考）: {format_percentage(avg_return_scaled * 252 * 100)}")
                        
                        elif time_scale == "月次":
                            avg_return_scaled = portfolio_returns.mean() * 20  # 20営業日
                            max_return_scaled = portfolio_returns.max() * np.sqrt(20)
                            min_return_scaled = portfolio_returns.min() * np.sqrt(20)
                            st.write(f"平均月次リターン: {format_percentage(avg_return_scaled * 100)}")
                            st.write(f"想定最大月次リターン: {format_percentage(max_return_scaled * 100)}")
                            st.write(f"想定最小月次リターン: {format_percentage(min_return_scaled * 100)}")
                            st.write(f"年率リターン（参考）: {format_percentage(avg_return_scaled * 12 * 100)}")
                        
                        elif time_scale == "年次":
                            avg_return_scaled = portfolio_returns.mean() * 252  # 252営業日
                            max_return_scaled = portfolio_returns.max() * np.sqrt(252)
                            min_return_scaled = portfolio_returns.min() * np.sqrt(252)
                            st.write(f"平均年次リターン: {format_percentage(avg_return_scaled * 100)}")
                            st.write(f"想定最大年次リターン: {format_percentage(max_return_scaled * 100)}")
                            st.write(f"想定最小年次リターン: {format_percentage(min_return_scaled * 100)}")
                    
                    with stats_col2:
                        st.write("**リスク統計:**")
                        skewness = portfolio_returns.skew()
                        kurtosis = portfolio_returns.kurtosis()
                        daily_vol = portfolio_returns.std()
                        scaled_vol = daily_vol * scale_factor
                        
                        st.write(f"歪度: {skewness:.3f}")
                        st.write(f"尖度: {kurtosis:.3f}")
                        st.write(f"{scale_label}次ボラティリティ: {format_percentage(scaled_vol * 100)}")
                        st.write(f"データ期間: {len(portfolio_returns)}営業日")
                        st.write(f"欠損データ: {portfolio_returns.isna().sum()}日")
    
    except Exception as e:
        display_error_message(e, "リスク分析中にエラーが発生しました")


def display_allocation_analysis(pnl_df: pd.DataFrame, tickers: List[str]):
    """配分分析の表示"""
    st.subheader("🌍 配分分析")
    
    try:
        # 本社所在国情報を取得
        with show_loading_spinner("企業の本社所在国情報を取得中..."):
            ticker_countries = cached_get_multiple_ticker_countries(tuple(tickers))
        
        # デバッグ情報表示
        with st.expander("🔍 本社所在国情報の詳細"):
            st.write("**取得された本社所在国情報:**")
            for ticker, country in ticker_countries.items():
                status = "✅" if country else "❌"
                country_display = country if country else "取得失敗"
                st.write(f"{status} **{ticker}**: {country_display}")
        
        # 地域別配分を計算
        sector_df = calculate_sector_allocation(pnl_df, ticker_countries)
        
        if not sector_df.empty:
            # 地域配分チャート
            sector_chart = create_sector_allocation_chart(sector_df)
            st.plotly_chart(sector_chart, use_container_width=True)
            
            # 配分テーブル
            st.subheader("📋 地域別配分詳細")
            display_df = sector_df.copy()
            
            # 列名を日本語に変更
            display_df = display_df.rename(columns={
                'country': '地域',
                'current_value_jpy': '現在価値（円）',
                'cost_basis_jpy': '取得原価（円）',
                'pnl_amount': '損益金額（円）',
                'position_count': '銘柄数',
                'allocation_percentage': '配分比率（%）',
                'pnl_percentage': '損益率（%）'
            })
            
            # 数値フォーマット
            display_df['現在価値（円）'] = display_df['現在価値（円）'].apply(
                lambda x: format_currency(x)
            )
            display_df['取得原価（円）'] = display_df['取得原価（円）'].apply(
                lambda x: format_currency(x)
            )
            display_df['損益金額（円）'] = display_df['損益金額（円）'].apply(
                lambda x: format_currency(x)
            )
            display_df['配分比率（%）'] = display_df['配分比率（%）'].apply(
                lambda x: format_percentage(x)
            )
            display_df['損益率（%）'] = display_df['損益率（%）'].apply(
                lambda x: format_percentage(x)
            )
            
            st.dataframe(display_df, use_container_width=True)
            
            # サマリー情報
            st.subheader("📊 地域別サマリー")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                top_region = sector_df.loc[sector_df['allocation_percentage'].idxmax(), 'country']
                top_allocation = sector_df['allocation_percentage'].max()
                st.metric("最大配分地域", f"{top_region}", f"{top_allocation:.1f}%")
            
            with col2:
                best_region = sector_df.loc[sector_df['pnl_percentage'].idxmax(), 'country']
                best_performance = sector_df['pnl_percentage'].max()
                st.metric("最高パフォーマンス地域", f"{best_region}", f"{best_performance:+.1f}%")
            
            with col3:
                total_regions = len(sector_df)
                profitable_regions = len(sector_df[sector_df['pnl_percentage'] > 0])
                st.metric("分散状況", f"{total_regions}地域", f"利益地域: {profitable_regions}")
    
    except Exception as e:
        display_error_message(e, "配分分析中にエラーが発生しました")


def display_detailed_data(pnl_df: pd.DataFrame, original_df: pd.DataFrame, tickers: List[str]):
    """詳細データの表示"""
    st.subheader("🔍 詳細データ")
    
    # 損益詳細テーブル
    st.subheader("💰 損益詳細")
    
    try:
        # 本社所在国情報を取得（配分分析と同じデータを使用）
        if 'ticker_countries_cache' not in st.session_state:
            with show_loading_spinner("企業の本社所在国情報を取得中..."):
                st.session_state.ticker_countries_cache = cached_get_multiple_ticker_countries(tuple(tickers))
        
        ticker_countries = st.session_state.ticker_countries_cache
        
        # 表示用にフォーマット
        display_pnl_df = pnl_df.copy()
        
        # 本社所在国と地域情報を追加
        from modules.country_fetcher import classify_region_by_country
        
        def get_country_info(ticker):
            country = ticker_countries.get(ticker)
            region = classify_region_by_country(country)
            return country if country else "取得失敗", region
        
        # 本社所在国と地域カラムを追加
        country_data = [get_country_info(ticker) for ticker in display_pnl_df['ticker']]
        display_pnl_df['本社所在国'] = [data[0] for data in country_data]
        display_pnl_df['地域'] = [data[1] for data in country_data]
        
        # 数値カラムをフォーマット
        numeric_columns = ['avg_cost_jpy', 'current_price_jpy', 'current_value_jpy', 
                          'cost_basis_jpy', 'pnl_amount']
        
        for col in numeric_columns:
            if col in display_pnl_df.columns:
                display_pnl_df[col] = display_pnl_df[col].apply(lambda x: format_currency(x))
        
        if 'pnl_percentage' in display_pnl_df.columns:
            display_pnl_df['pnl_percentage'] = display_pnl_df['pnl_percentage'].apply(
                lambda x: format_percentage(x)
            )
        
        # カラム順序を調整（ティッカー、本社所在国、地域を先頭に）
        columns_order = ['ticker', '本社所在国', '地域']
        other_columns = [col for col in display_pnl_df.columns if col not in columns_order]
        display_pnl_df = display_pnl_df[columns_order + other_columns]
        
        st.dataframe(display_pnl_df, use_container_width=True)
        
    except Exception as e:
        display_error_message(e, "詳細データ表示中にエラーが発生しました")
        # エラー時は元の表示にフォールバック
        display_pnl_df = pnl_df.copy()
        numeric_columns = ['avg_cost_jpy', 'current_price_jpy', 'current_value_jpy', 
                          'cost_basis_jpy', 'pnl_amount']
        
        for col in numeric_columns:
            if col in display_pnl_df.columns:
                display_pnl_df[col] = display_pnl_df[col].apply(lambda x: format_currency(x))
        
        if 'pnl_percentage' in display_pnl_df.columns:
            display_pnl_df['pnl_percentage'] = display_pnl_df['pnl_percentage'].apply(
                lambda x: format_percentage(x)
            )
        
        st.dataframe(display_pnl_df, use_container_width=True)
    
    # オリジナルデータ
    with st.expander("📄 オリジナルデータ"):
        st.dataframe(original_df, use_container_width=True)
    
    # データダウンロード
    col1, col2 = st.columns(2)
    
    with col1:
        pnl_csv = pnl_df.to_csv(index=False)
        st.download_button(
            label="📥 損益データをダウンロード",
            data=pnl_csv,
            file_name="portfolio_pnl.csv",
            mime="text/csv"
        )
    
    with col2:
        original_csv = original_df.to_csv(index=False)
        st.download_button(
            label="📥 オリジナルデータをダウンロード",
            data=original_csv,
            file_name="portfolio_original.csv",
            mime="text/csv"
        )


def display_stock_charts(tickers: List[str]):
    """株価チャートの表示"""
    st.subheader("📊 株価チャート")
    
    if not tickers:
        st.warning("表示する銘柄がありません。")
        return
    
    # セッションステートでチャート設定を管理
    if 'chart_ticker' not in st.session_state:
        st.session_state.chart_ticker = tickers[0] if tickers else ""
    if 'chart_period' not in st.session_state:
        st.session_state.chart_period = "1mo"
    
    # 銘柄選択
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_ticker = st.selectbox(
            "表示する銘柄を選択",
            options=tickers,
            index=tickers.index(st.session_state.chart_ticker) if st.session_state.chart_ticker in tickers else 0,
            help="チャートを表示する銘柄を選択してください",
            key="chart_ticker_selector"
        )
        st.session_state.chart_ticker = selected_ticker
    
    with col2:
        chart_period = st.selectbox(
            "期間",
            options=["1mo", "3mo", "6mo", "ytd", "1y", "2y", "5y"],
            index=["1mo", "3mo", "6mo", "ytd", "1y", "2y", "5y"].index(st.session_state.chart_period),
            help="チャート表示期間を選択してください",
            key="chart_period_selector"
        )
        st.session_state.chart_period = chart_period
    
    if selected_ticker:
        try:
            with show_loading_spinner(f"{selected_ticker}のチャートデータを取得中..."):
                chart_data = get_stock_chart_data(selected_ticker, period=chart_period)
                
                if not chart_data.empty:
                    # ローソク足チャート
                    candlestick_chart = create_stock_candlestick_chart(chart_data, selected_ticker)
                    st.plotly_chart(candlestick_chart, use_container_width=True)
                    
                    # 基本統計情報
                    with st.expander("📈 期間統計"):
                        col1, col2, col3, col4 = st.columns(4)
                        
                        period_return = ((chart_data['Close'].iloc[-1] / chart_data['Close'].iloc[0]) - 1) * 100
                        high_price = chart_data['High'].max()
                        low_price = chart_data['Low'].min()
                        avg_volume = chart_data['Volume'].mean()
                        
                        with col1:
                            st.metric("期間リターン", f"{period_return:+.2f}%")
                        with col2:
                            st.metric("期間最高値", f"{high_price:.2f}")
                        with col3:
                            st.metric("期間最安値", f"{low_price:.2f}")
                        with col4:
                            st.metric("平均出来高", f"{avg_volume:,.0f}")
                else:
                    st.error(f"{selected_ticker}のチャートデータを取得できませんでした。")
                    
        except Exception as e:
            display_error_message(e, f"{selected_ticker}のチャート表示中にエラーが発生しました")



def display_welcome_page():
    """ウェルカムページの表示"""
    st.markdown("""
    ## 👋 ようこそ！
    
    このアプリケーションは株式ポートフォリオの管理と分析を行うためのツールです。
    
    ### 🚀 機能
    - **CSVインポート**: ポートフォリオデータの簡単アップロード
    - **リアルタイム株価**: Yahoo Financeからの最新データ取得
    - **損益計算**: 多通貨対応の精密な損益計算
    - **リスク分析**: VaR、CVaR、ボラティリティ等の計算
    - **可視化**: インタラクティブなチャートとグラフ
    
    ### 📋 使用方法
    1. 左のサイドバーからCSVファイルをアップロード
    2. データが自動的に分析され、ダッシュボードが表示されます
    3. 各タブで詳細な分析結果を確認できます
    
    ### 📁 CSVファイル形式
    ```
    Ticker,Shares,AvgCostJPY
    AAPL,100,15000
    MSFT,50,25000
    7203.T,1000,800
    ```
    
    左のサイドバーからサンプルファイルをダウンロードして試してみてください！
    """)
    
    # サンプルファイルダウンロード
    sample_data = {
        'Ticker': ['AAPL', 'MSFT', '7203.T', 'ASML', 'TSLA'],
        'Shares': [100, 50, 1000, 20, 30],
        'AvgCostJPY': [15000, 25000, 800, 60000, 20000]
    }
    sample_df = pd.DataFrame(sample_data)
    sample_csv = sample_df.to_csv(index=False)
    
    st.download_button(
        label="📥 サンプルCSVファイルをダウンロード",
        data=sample_csv,
        file_name="sample_portfolio.csv",
        mime="text/csv"
    )


if __name__ == "__main__":
    main_dashboard()