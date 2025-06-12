"""
企業の本社所在国取得モジュール
Yahoo Financeから企業の本社所在国情報を取得する機能
"""

import yfinance as yf
import streamlit as st
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


def get_ticker_country(ticker: str) -> Optional[str]:
    """
    ティッカーシンボルから本社所在国を取得
    
    Args:
        ticker: ティッカーシンボル
    
    Returns:
        str: 本社所在国名、取得失敗時はNone
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # 'country'フィールドから取得
        country = info.get('country')
        if country:
            logger.debug(f"取得成功: {ticker} -> {country}")
            return country
        else:
            logger.warning(f"国情報が見つかりません: {ticker}")
            return None
            
    except Exception as e:
        logger.error(f"国情報取得エラー {ticker}: {str(e)}")
        return None


def get_multiple_ticker_countries(tickers: List[str]) -> Dict[str, Optional[str]]:
    """
    複数銘柄の本社所在国を一括取得
    
    Args:
        tickers: ティッカーシンボルのリスト
    
    Returns:
        Dict[str, Optional[str]]: ティッカーをキーとした本社所在国の辞書
    """
    countries = {}
    
    for ticker in tickers:
        try:
            country = get_ticker_country(ticker)
            countries[ticker] = country
        except Exception as e:
            logger.error(f"国情報取得エラー {ticker}: {str(e)}")
            countries[ticker] = None
    
    logger.info(f"本社所在国取得完了: {len([c for c in countries.values() if c])}/{len(tickers)}銘柄")
    return countries


def classify_region_by_country(country: Optional[str]) -> str:
    """
    本社所在国から地域を分類
    
    Args:
        country: 本社所在国名
    
    Returns:
        str: 地域名（日本、米国、欧州、アジア太平洋、その他）
    """
    if not country:
        return "その他"
    
    country = country.upper().strip()
    
    # 日本
    if country in ['JAPAN']:
        return "日本"
    
    # 米国
    if country in ['UNITED STATES', 'USA', 'US']:
        return "米国"
    
    # 欧州
    european_countries = [
        'GERMANY', 'FRANCE', 'UNITED KINGDOM', 'UK', 'GREAT BRITAIN',
        'ITALY', 'SPAIN', 'NETHERLANDS', 'SWITZERLAND', 'SWEDEN',
        'NORWAY', 'DENMARK', 'FINLAND', 'BELGIUM', 'AUSTRIA',
        'IRELAND', 'PORTUGAL', 'LUXEMBOURG', 'GREECE', 'POLAND',
        'CZECH REPUBLIC', 'HUNGARY', 'SLOVAKIA', 'SLOVENIA',
        'CROATIA', 'ROMANIA', 'BULGARIA', 'ESTONIA', 'LATVIA',
        'LITHUANIA', 'MALTA', 'CYPRUS'
    ]
    
    if country in european_countries:
        return "欧州"
    
    # アジア太平洋
    asia_pacific_countries = [
        'CHINA', 'SOUTH KOREA', 'KOREA', 'TAIWAN', 'HONG KONG',
        'SINGAPORE', 'MALAYSIA', 'THAILAND', 'INDONESIA',
        'PHILIPPINES', 'VIETNAM', 'INDIA', 'AUSTRALIA',
        'NEW ZEALAND'
    ]
    
    if country in asia_pacific_countries:
        return "アジア太平洋"
    
    # カナダ
    if country in ['CANADA']:
        return "北米（その他）"
    
    # その他
    return "その他"


@st.cache_data(ttl=3600)  # 1時間キャッシュ
def cached_get_multiple_ticker_countries(tickers_tuple: tuple) -> Dict[str, Optional[str]]:
    """
    キャッシュ機能付きの複数銘柄本社所在国取得
    
    Args:
        tickers_tuple: ティッカーシンボルのタプル（キャッシュキー用）
    
    Returns:
        Dict[str, Optional[str]]: 本社所在国辞書
    """
    return get_multiple_ticker_countries(list(tickers_tuple))