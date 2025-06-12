"""
損益計算モジュール
ポートフォリオの損益計算とパフォーマンス分析機能
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_pnl(
    ticker: str,
    shares: float,
    avg_cost_jpy: float,
    current_price_local: float,
    exchange_rate: float = 1.0
) -> Dict[str, float]:
    """
    単一銘柄の損益計算（日本円ベース）
    
    Args:
        ticker: ティッカーシンボル
        shares: 保有株数
        avg_cost_jpy: 日本円ベース平均購入単価
        current_price_local: 現在株価（現地通貨）
        exchange_rate: 為替レート（現地通貨→JPY）
    
    Returns:
        dict: 損益情報
    """
    try:
        # 現在価格を日本円に換算
        current_price_jpy = current_price_local * exchange_rate
        
        # 現在評価額
        current_value_jpy = current_price_jpy * shares
        
        # 投資額（簿価）
        cost_basis_jpy = avg_cost_jpy * shares
        
        # 損益額
        pnl_amount = current_value_jpy - cost_basis_jpy
        
        # 損益率
        pnl_percentage = (pnl_amount / cost_basis_jpy) * 100 if cost_basis_jpy > 0 else 0
        
        result = {
            'ticker': ticker,
            'shares': shares,
            'avg_cost_jpy': avg_cost_jpy,
            'current_price_local': current_price_local,
            'current_price_jpy': current_price_jpy,
            'exchange_rate': exchange_rate,
            'current_value_jpy': current_value_jpy,
            'cost_basis_jpy': cost_basis_jpy,
            'pnl_amount': pnl_amount,
            'pnl_percentage': pnl_percentage
        }
        
        logger.debug(f"損益計算完了 {ticker}: {pnl_amount:,.0f}円 ({pnl_percentage:.2f}%)")
        return result
        
    except Exception as e:
        logger.error(f"損益計算エラー {ticker}: {str(e)}")
        return {
            'ticker': ticker,
            'shares': shares,
            'avg_cost_jpy': avg_cost_jpy,
            'current_price_local': 0,
            'current_price_jpy': 0,
            'exchange_rate': exchange_rate,
            'current_value_jpy': 0,
            'cost_basis_jpy': avg_cost_jpy * shares,
            'pnl_amount': -(avg_cost_jpy * shares),
            'pnl_percentage': -100.0
        }


def calculate_portfolio_pnl(
    portfolio_df: pd.DataFrame,
    current_prices: Dict[str, float],
    exchange_rates: Dict[str, float],
    currency_mapping: Dict[str, str]
) -> pd.DataFrame:
    """
    ポートフォリオ全体の損益計算
    
    Args:
        portfolio_df: ポートフォリオデータ
        current_prices: 現在株価辞書
        exchange_rates: 為替レート辞書
        currency_mapping: ティッカーと通貨のマッピング
    
    Returns:
        pd.DataFrame: 損益計算結果
    """
    pnl_results = []
    
    for _, row in portfolio_df.iterrows():
        ticker = row['Ticker']
        shares = row['Shares']
        avg_cost_jpy = row['AvgCostJPY']
        
        # 現在株価を取得
        current_price_local = current_prices.get(ticker, 0)
        
        # 通貨と為替レートを取得
        currency = currency_mapping.get(ticker, 'USD')
        exchange_rate = get_exchange_rate_for_currency(currency, exchange_rates)
        
        # 損益計算
        pnl_data = calculate_pnl(
            ticker=ticker,
            shares=shares,
            avg_cost_jpy=avg_cost_jpy,
            current_price_local=current_price_local,
            exchange_rate=exchange_rate
        )
        
        # 通貨情報を追加
        pnl_data['currency'] = currency
        
        pnl_results.append(pnl_data)
    
    # DataFrameに変換
    pnl_df = pd.DataFrame(pnl_results)
    
    logger.info(f"ポートフォリオ損益計算完了: {len(pnl_df)}銘柄")
    return pnl_df


def get_exchange_rate_for_currency(currency: str, exchange_rates: Dict[str, float]) -> float:
    """
    通貨に対応する為替レートを取得
    
    Args:
        currency: 通貨コード
        exchange_rates: 為替レート辞書
    
    Returns:
        float: 為替レート（JPYに対する）
    """
    if currency == 'JPY':
        return 1.0
    
    rate_mapping = {
        'USD': 'USDJPY=X',
        'EUR': 'EURJPY=X',
        'GBP': 'GBPJPY=X',
        'AUD': 'AUDJPY=X',
        'CAD': 'CADJPY=X',
        'CHF': 'CHFJPY=X'
    }
    
    rate_symbol = rate_mapping.get(currency)
    if rate_symbol and rate_symbol in exchange_rates:
        return exchange_rates[rate_symbol]
    
    # フォールバック：概算レート
    fallback_rates = {
        'USD': 150.0,
        'EUR': 160.0,
        'GBP': 180.0,
        'AUD': 100.0,
        'CAD': 110.0,
        'CHF': 165.0,
        'HKD': 19.0,
        'SGD': 110.0,
        'CNY': 21.0,
        'KRW': 0.11
    }
    
    return fallback_rates.get(currency, 1.0)


def calculate_portfolio_summary(pnl_df: pd.DataFrame) -> Dict[str, float]:
    """
    ポートフォリオサマリーの計算
    
    Args:
        pnl_df: 損益計算結果DataFrame
    
    Returns:
        dict: ポートフォリオサマリー
    """
    try:
        total_cost_basis = pnl_df['cost_basis_jpy'].sum()
        total_current_value = pnl_df['current_value_jpy'].sum()
        total_pnl_amount = pnl_df['pnl_amount'].sum()
        
        overall_pnl_percentage = (total_pnl_amount / total_cost_basis) * 100 if total_cost_basis > 0 else 0
        
        # 勝率計算
        profitable_positions = (pnl_df['pnl_amount'] > 0).sum()
        total_positions = len(pnl_df)
        win_rate = (profitable_positions / total_positions) * 100 if total_positions > 0 else 0
        
        # 最大・最小損益
        max_gain = pnl_df['pnl_amount'].max()
        max_loss = pnl_df['pnl_amount'].min()
        max_gain_pct = pnl_df['pnl_percentage'].max()
        max_loss_pct = pnl_df['pnl_percentage'].min()
        
        # 最大・最小損益銘柄
        max_gain_ticker = pnl_df.loc[pnl_df['pnl_amount'].idxmax(), 'ticker'] if not pnl_df.empty else ''
        max_loss_ticker = pnl_df.loc[pnl_df['pnl_amount'].idxmin(), 'ticker'] if not pnl_df.empty else ''
        
        summary = {
            'total_positions': total_positions,
            'total_cost_basis_jpy': total_cost_basis,
            'total_current_value_jpy': total_current_value,
            'total_pnl_amount_jpy': total_pnl_amount,
            'overall_pnl_percentage': overall_pnl_percentage,
            'win_rate': win_rate,
            'profitable_positions': profitable_positions,
            'losing_positions': total_positions - profitable_positions,
            'max_gain_amount': max_gain,
            'max_loss_amount': max_loss,
            'max_gain_percentage': max_gain_pct,
            'max_loss_percentage': max_loss_pct,
            'max_gain_ticker': max_gain_ticker,
            'max_loss_ticker': max_loss_ticker,
            'average_position_size': total_cost_basis / total_positions if total_positions > 0 else 0
        }
        
        logger.info(f"ポートフォリオサマリー計算完了: 総損益 {total_pnl_amount:,.0f}円 ({overall_pnl_percentage:.2f}%)")
        return summary
        
    except Exception as e:
        logger.error(f"ポートフォリオサマリー計算エラー: {str(e)}")
        return {}


def calculate_sector_allocation(pnl_df: pd.DataFrame, ticker_countries: dict = None) -> pd.DataFrame:
    """
    地域別配分の計算（Yahoo Finance country情報ベース）
    
    Args:
        pnl_df: 損益計算結果DataFrame
        ticker_countries: ティッカー別本社所在国辞書
    
    Returns:
        pd.DataFrame: 地域別配分データ
    """
    try:
        from modules.country_fetcher import classify_region_by_country
        
        # 地域分類関数
        def get_region_for_ticker(ticker):
            if ticker_countries and ticker in ticker_countries:
                country = ticker_countries[ticker]
                return classify_region_by_country(country)
            else:
                # フォールバック：ティッカーサフィックスベース
                if '.T' in ticker or '.JP' in ticker:
                    return '日本'
                elif '.AS' in ticker or '.PA' in ticker or '.DE' in ticker or '.MI' in ticker or '.L' in ticker:
                    return '欧州'
                elif '.TO' in ticker or '.V' in ticker:
                    return '北米（その他）'
                elif '.AX' in ticker:
                    return 'アジア太平洋'
                elif '.HK' in ticker:
                    return 'アジア太平洋'
                else:
                    return '米国'
        
        # 地域分類を適用
        pnl_df = pnl_df.copy()
        pnl_df['country'] = pnl_df['ticker'].apply(get_region_for_ticker)
        
        # 地域別集計
        sector_allocation = pnl_df.groupby('country').agg({
            'current_value_jpy': 'sum',
            'cost_basis_jpy': 'sum',
            'pnl_amount': 'sum',
            'ticker': 'count'
        }).rename(columns={'ticker': 'position_count'})
        
        # 配分比率を計算
        total_value = sector_allocation['current_value_jpy'].sum()
        sector_allocation['allocation_percentage'] = (
            sector_allocation['current_value_jpy'] / total_value * 100
        ) if total_value > 0 else 0
        
        # 損益率を計算
        sector_allocation['pnl_percentage'] = (
            sector_allocation['pnl_amount'] / sector_allocation['cost_basis_jpy'] * 100
        ).fillna(0)
        
        return sector_allocation.reset_index()
        
    except Exception as e:
        logger.error(f"地域配分計算エラー: {str(e)}")
        return pd.DataFrame()


def calculate_performance_metrics(pnl_df: pd.DataFrame, risk_free_rate: float = 0.1) -> Dict[str, float]:
    """
    パフォーマンス指標の計算
    
    Args:
        pnl_df: 損益計算結果DataFrame
        risk_free_rate: リスクフリーレート（年率%）
    
    Returns:
        dict: パフォーマンス指標
    """
    try:
        if pnl_df.empty:
            return {}
        
        # 重み（時価総額比率）を計算
        total_value = pnl_df['current_value_jpy'].sum()
        weights = pnl_df['current_value_jpy'] / total_value if total_value > 0 else np.ones(len(pnl_df)) / len(pnl_df)
        
        # 重み付き平均リターン
        weighted_return = (pnl_df['pnl_percentage'] * weights).sum()
        
        # 銘柄別リターンの標準偏差（簡易版）
        returns_std = pnl_df['pnl_percentage'].std()
        
        # シャープレシオ（簡易計算）
        excess_return = weighted_return - risk_free_rate
        sharpe_ratio = excess_return / returns_std if returns_std > 0 else 0
        
        # 最大ドローダウン（単純版：最大損失銘柄）
        max_drawdown = pnl_df['pnl_percentage'].min()
        
        metrics = {
            'weighted_return': weighted_return,
            'returns_std': returns_std,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'risk_free_rate': risk_free_rate
        }
        
        logger.info(f"パフォーマンス指標計算完了: シャープレシオ {sharpe_ratio:.3f}")
        return metrics
        
    except Exception as e:
        logger.error(f"パフォーマンス指標計算エラー: {str(e)}")
        return {}


def calculate_position_sizing_analysis(pnl_df: pd.DataFrame) -> Dict[str, any]:
    """
    ポジションサイジング分析
    
    Args:
        pnl_df: 損益計算結果DataFrame
    
    Returns:
        dict: ポジションサイジング分析結果
    """
    try:
        if pnl_df.empty:
            return {}
        
        total_value = pnl_df['current_value_jpy'].sum()
        
        # 各ポジションの比率
        pnl_df['position_weight'] = pnl_df['current_value_jpy'] / total_value * 100
        
        # 集中度分析
        top_5_weight = pnl_df.nlargest(5, 'position_weight')['position_weight'].sum()
        top_10_weight = pnl_df.nlargest(10, 'position_weight')['position_weight'].sum()
        
        # ハーフィンダール指数（集中度指標）
        hhi = (pnl_df['position_weight'] ** 2).sum()
        
        # 等分散からの偏差
        equal_weight = 100 / len(pnl_df)
        weight_variance = pnl_df['position_weight'].var()
        
        analysis = {
            'total_positions': len(pnl_df),
            'top_5_concentration': top_5_weight,
            'top_10_concentration': top_10_weight,
            'herfindahl_index': hhi,
            'equal_weight_benchmark': equal_weight,
            'weight_variance': weight_variance,
            'max_position_weight': pnl_df['position_weight'].max(),
            'min_position_weight': pnl_df['position_weight'].min(),
            'largest_position': pnl_df.loc[pnl_df['position_weight'].idxmax(), 'ticker'],
            'smallest_position': pnl_df.loc[pnl_df['position_weight'].idxmin(), 'ticker']
        }
        
        logger.info(f"ポジションサイジング分析完了: 上位5銘柄集中度 {top_5_weight:.1f}%")
        return analysis
        
    except Exception as e:
        logger.error(f"ポジションサイジング分析エラー: {str(e)}")
        return {}