"""
可視化モジュール
チャートとグラフの生成機能
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def create_pnl_chart(pnl_df: pd.DataFrame) -> go.Figure:
    """
    銘柄別損益棒グラフ
    
    Args:
        pnl_df: 損益計算結果DataFrame
    
    Returns:
        plotly.graph_objects.Figure: 損益チャート
    """
    try:
        if pnl_df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="データがありません",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        # 色の設定（損益に応じて）
        colors = ['red' if x < 0 else 'green' for x in pnl_df['pnl_amount']]
        
        fig = go.Figure(data=[
            go.Bar(
                x=pnl_df['ticker'],
                y=pnl_df['pnl_amount'],
                marker_color=colors,
                text=pnl_df['pnl_percentage'].apply(lambda x: f"{x:.1f}%"),
                textposition='auto',
                hovertemplate='<b>%{x}</b><br>' +
                            '損益額: ¥%{y:,.0f}<br>' +
                            '損益率: %{text}<br>' +
                            '<extra></extra>'
            )
        ])
        
        fig.update_layout(
            title='銘柄別損益',
            xaxis_title='ティッカー',
            yaxis_title='損益額 (円)',
            hovermode='x unified',
            height=500
        )
        
        # ゼロラインを追加
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        
        return fig
        
    except Exception as e:
        logger.error(f"損益チャート作成エラー: {str(e)}")
        return go.Figure()


def create_allocation_pie(pnl_df: pd.DataFrame) -> go.Figure:
    """
    資産配分円グラフ
    
    Args:
        pnl_df: 損益計算結果DataFrame
    
    Returns:
        plotly.graph_objects.Figure: 配分チャート
    """
    try:
        if pnl_df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="データがありません",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        fig = go.Figure(data=[
            go.Pie(
                labels=pnl_df['ticker'],
                values=pnl_df['current_value_jpy'],
                textinfo='label+percent',
                hovertemplate='<b>%{label}</b><br>' +
                            '評価額: ¥%{value:,.0f}<br>' +
                            '比率: %{percent}<br>' +
                            '<extra></extra>'
            )
        ])
        
        fig.update_layout(
            title='ポートフォリオ資産配分',
            height=500,
            showlegend=True
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"配分チャート作成エラー: {str(e)}")
        return go.Figure()


def create_correlation_heatmap(correlation_matrix: pd.DataFrame) -> go.Figure:
    """
    相関行列ヒートマップ
    
    Args:
        correlation_matrix: 相関行列DataFrame
    
    Returns:
        plotly.graph_objects.Figure: 相関ヒートマップ
    """
    try:
        if correlation_matrix.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="データがありません",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        fig = go.Figure(data=go.Heatmap(
            z=correlation_matrix.values,
            x=correlation_matrix.columns,
            y=correlation_matrix.index,
            colorscale='RdBu',
            zmid=0,
            zmin=-1,
            zmax=1,
            text=np.round(correlation_matrix.values, 3),
            texttemplate='%{text}',
            textfont={"size": 10},
            hovertemplate='<b>%{y} vs %{x}</b><br>' +
                         '相関係数: %{z:.3f}<br>' +
                         '<extra></extra>'
        ))
        
        fig.update_layout(
            title='銘柄間相関係数',
            height=600,
            xaxis_title='',
            yaxis_title=''
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"相関ヒートマップ作成エラー: {str(e)}")
        return go.Figure()


def create_var_distribution(portfolio_returns: pd.Series, var_values: Dict[str, float], scale_factor: float = 1.0, scale_label: str = "日") -> go.Figure:
    """
    VaR可視化（ヒストグラム + VaRライン）
    
    Args:
        portfolio_returns: ポートフォリオリターン系列
        var_values: VaR値辞書
        scale_factor: 時間軸変換係数（月次: √20, 年次: √252）
        scale_label: 時間軸ラベル（日、月、年）
    
    Returns:
        plotly.graph_objects.Figure: VaR分布チャート
    """
    try:
        if portfolio_returns.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="データがありません",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        fig = go.Figure()
        
        # ヒストグラム（時間軸に応じてスケール）
        scaled_returns = portfolio_returns * scale_factor
        fig.add_trace(go.Histogram(
            x=scaled_returns * 100,  # パーセント表示
            nbinsx=50,
            name="リターン分布",
            opacity=0.7,
            marker_color='lightblue'
        ))
        
        # VaRライン（時間軸に応じてスケール）
        colors = ['red', 'darkred']
        for i, (var_name, var_val) in enumerate(var_values.items()):
            if 'VaR' in var_name:
                confidence = var_name.split('_')[1]
                scaled_var = var_val * scale_factor
                fig.add_vline(
                    x=scaled_var * 100,
                    line_dash="dash",
                    line_color=colors[i % len(colors)],
                    annotation_text=f"VaR{confidence}%: {scaled_var:.2%}",
                    annotation_position="top"
                )
        
        fig.update_layout(
            title=f'ポートフォリオリターン分布とVaR（{scale_label}次）',
            xaxis_title=f'{scale_label}次リターン (%)',
            yaxis_title='頻度',
            height=500,
            showlegend=True
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"VaR分布チャート作成エラー: {str(e)}")
        return go.Figure()


def create_risk_contribution_chart(risk_data: Dict[str, any]) -> go.Figure:
    """
    リスク寄与度チャート
    
    Args:
        risk_data: リスク寄与度データ
    
    Returns:
        plotly.graph_objects.Figure: リスク寄与度チャート
    """
    try:
        if not risk_data or 'tickers' not in risk_data:
            fig = go.Figure()
            fig.add_annotation(
                text="データがありません",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        fig = go.Figure()
        
        # リスク寄与率
        fig.add_trace(go.Bar(
            x=risk_data['tickers'],
            y=risk_data['risk_contribution_pct'],
            name='リスク寄与率',
            marker_color='orange',
            yaxis='y1'
        ))
        
        # ポジション比率
        fig.add_trace(go.Scatter(
            x=risk_data['tickers'],
            y=risk_data['weights'] * 100,
            mode='markers+lines',
            name='ポジション比率',
            marker_color='blue',
            yaxis='y2'
        ))
        
        fig.update_layout(
            title='リスク寄与度分析',
            xaxis_title='ティッカー',
            yaxis=dict(title='リスク寄与率 (%)', side='left'),
            yaxis2=dict(title='ポジション比率 (%)', side='right', overlaying='y'),
            height=500,
            showlegend=True
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"リスク寄与度チャート作成エラー: {str(e)}")
        return go.Figure()


def create_performance_summary_chart(summary: Dict[str, float]) -> go.Figure:
    """
    パフォーマンスサマリーチャート
    
    Args:
        summary: ポートフォリオサマリー
    
    Returns:
        plotly.graph_objects.Figure: サマリーチャート
    """
    try:
        if not summary:
            fig = go.Figure()
            fig.add_annotation(
                text="データがありません",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        # メトリクス
        metrics = ['総損益率', '勝率', '最大利益率', '最大損失率']
        values = [
            summary.get('overall_pnl_percentage', 0),
            summary.get('win_rate', 0),
            summary.get('max_gain_percentage', 0),
            summary.get('max_loss_percentage', 0)
        ]
        
        # 色の設定
        colors = ['green' if v > 0 else 'red' if v < 0 else 'gray' for v in values]
        
        fig = go.Figure(data=[
            go.Bar(
                x=metrics,
                y=values,
                marker_color=colors,
                text=[f"{v:.1f}%" for v in values],
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            title='パフォーマンスサマリー',
            yaxis_title='パーセント (%)',
            height=400
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"パフォーマンスサマリーチャート作成エラー: {str(e)}")
        return go.Figure()


def create_sector_allocation_chart(sector_df: pd.DataFrame) -> go.Figure:
    """
    セクター別配分チャート
    
    Args:
        sector_df: セクター別配分DataFrame
    
    Returns:
        plotly.graph_objects.Figure: セクター配分チャート
    """
    try:
        if sector_df.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="データがありません",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=['配分比率', '損益率'],
            specs=[[{"type": "pie"}, {"type": "bar"}]]
        )
        
        # 配分円グラフ
        fig.add_trace(
            go.Pie(
                labels=sector_df['country'],
                values=sector_df['allocation_percentage'],
                textinfo='label+percent'
            ),
            row=1, col=1
        )
        
        # 損益率棒グラフ
        colors = ['green' if x > 0 else 'red' for x in sector_df['pnl_percentage']]
        fig.add_trace(
            go.Bar(
                x=sector_df['country'],
                y=sector_df['pnl_percentage'],
                marker_color=colors,
                text=sector_df['pnl_percentage'].apply(lambda x: f"{x:.1f}%"),
                textposition='auto'
            ),
            row=1, col=2
        )
        
        fig.update_layout(
            title='地域別配分と損益',
            height=500,
            showlegend=False
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"セクター配分チャート作成エラー: {str(e)}")
        return go.Figure()


def create_price_history_chart(
    historical_data: pd.DataFrame,
    normalize: bool = True
) -> go.Figure:
    """
    価格履歴チャート
    
    Args:
        historical_data: 過去価格データ
        normalize: 正規化するかどうか
    
    Returns:
        plotly.graph_objects.Figure: 価格履歴チャート
    """
    try:
        if historical_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="データがありません",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        fig = go.Figure()
        
        # データの準備
        data_to_plot = historical_data.copy()
        if normalize:
            # 最初の値を100として正規化
            data_to_plot = data_to_plot.div(data_to_plot.iloc[0]) * 100
        
        # 各銘柄の線を追加
        for column in data_to_plot.columns:
            fig.add_trace(go.Scatter(
                x=data_to_plot.index,
                y=data_to_plot[column],
                mode='lines',
                name=column,
                hovertemplate='<b>%{fullData.name}</b><br>' +
                            '日付: %{x}<br>' +
                            f'{"正規化価格" if normalize else "価格"}: %{{y:.2f}}<br>' +
                            '<extra></extra>'
            ))
        
        title = '価格推移（正規化）' if normalize else '価格推移'
        y_title = '正規化価格 (開始=100)' if normalize else '価格'
        
        fig.update_layout(
            title=title,
            xaxis_title='日付',
            yaxis_title=y_title,
            height=600,
            hovermode='x unified'
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"価格履歴チャート作成エラー: {str(e)}")
        return go.Figure()


def create_stock_candlestick_chart(stock_data: pd.DataFrame, ticker: str) -> go.Figure:
    """
    株価ローソク足チャート
    
    Args:
        stock_data: 株価OHLCV データ
        ticker: ティッカーシンボル
    
    Returns:
        plotly.graph_objects.Figure: ローソク足チャート
    """
    try:
        if stock_data.empty:
            fig = go.Figure()
            fig.add_annotation(
                text="データがありません",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        # サブプロットの作成（価格と出来高）
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=[f'{ticker} 株価', '出来高'],
            row_heights=[0.7, 0.3]
        )
        
        # ローソク足チャート
        fig.add_trace(
            go.Candlestick(
                x=stock_data['Date'],
                open=stock_data['Open'],
                high=stock_data['High'],
                low=stock_data['Low'],
                close=stock_data['Close'],
                name='価格',
                increasing_line_color='green',
                decreasing_line_color='red'
            ),
            row=1, col=1
        )
        
        # 移動平均線を追加（20日、50日）
        if len(stock_data) >= 20:
            ma20 = stock_data['Close'].rolling(window=20).mean()
            fig.add_trace(
                go.Scatter(
                    x=stock_data['Date'],
                    y=ma20,
                    mode='lines',
                    name='MA20',
                    line=dict(color='blue', width=1),
                    opacity=0.7
                ),
                row=1, col=1
            )
        
        if len(stock_data) >= 50:
            ma50 = stock_data['Close'].rolling(window=50).mean()
            fig.add_trace(
                go.Scatter(
                    x=stock_data['Date'],
                    y=ma50,
                    mode='lines',
                    name='MA50',
                    line=dict(color='orange', width=1),
                    opacity=0.7
                ),
                row=1, col=1
            )
        
        # 出来高チャート
        colors = ['green' if close >= open else 'red' 
                 for close, open in zip(stock_data['Close'], stock_data['Open'])]
        
        fig.add_trace(
            go.Bar(
                x=stock_data['Date'],
                y=stock_data['Volume'],
                marker_color=colors,
                name='出来高',
                opacity=0.6
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            title=f'{ticker} 株価チャート',
            xaxis_rangeslider_visible=False,
            height=700,
            showlegend=True
        )
        
        # Y軸の設定
        fig.update_yaxes(title_text="価格", row=1, col=1)
        fig.update_yaxes(title_text="出来高", row=2, col=1)
        fig.update_xaxes(title_text="日付", row=2, col=1)
        
        return fig
        
    except Exception as e:
        logger.error(f"ローソク足チャート作成エラー: {str(e)}")
        return go.Figure()


def create_news_sentiment_chart(sentiment_data: Dict) -> go.Figure:
    """
    ニュースセンチメントチャート
    
    Args:
        sentiment_data: センチメント分析結果
    
    Returns:
        plotly.graph_objects.Figure: センチメントチャート
    """
    try:
        if not sentiment_data or sentiment_data.get('total', 0) == 0:
            fig = go.Figure()
            fig.add_annotation(
                text="データがありません",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        labels = ['ポジティブ', 'ネガティブ', 'ニュートラル']
        values = [
            sentiment_data.get('positive', 0),
            sentiment_data.get('negative', 0),
            sentiment_data.get('neutral', 0)
        ]
        colors = ['green', 'red', 'gray']
        
        fig = go.Figure(data=[
            go.Pie(
                labels=labels,
                values=values,
                marker_colors=colors,
                textinfo='label+percent+value',
                hovertemplate='<b>%{label}</b><br>' +
                            '記事数: %{value}<br>' +
                            '比率: %{percent}<br>' +
                            '<extra></extra>'
            )
        ])
        
        fig.update_layout(
            title=f'ニュースセンチメント分析 (総記事数: {sentiment_data.get("total", 0)})',
            height=400,
            showlegend=True
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"センチメントチャート作成エラー: {str(e)}")
        return go.Figure()