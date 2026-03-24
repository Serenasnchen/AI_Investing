"""
FinancialDataProvider: interface for public market data.

Intended real integrations:
  - Yahoo Finance (via yfinance library — free, no key required)
  - Alpha Vantage API (free tier available)
  - Bloomberg API / Refinitiv Eikon (institutional)
  - Polygon.io (low-cost real-time + historical)

The agent layer never imports a concrete implementation directly;
it receives a FinancialDataProvider instance injected by the orchestrator.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StockQuote:
    """Real-time or delayed quote for a listed security."""
    ticker: str
    name: str
    exchange: str
    price: float
    market_cap_usd_b: float
    pe_ratio: Optional[float] = None
    ev_revenue_ratio: Optional[float] = None   # EV / trailing revenue
    price_to_sales: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    ytd_change_pct: Optional[float] = None      # e.g. -0.42 = -42%
    cash_usd_b: Optional[float] = None          # cash & equivalents


@dataclass
class NewsItem:
    """A news headline associated with a listed company."""
    headline: str
    date: str                  # ISO format preferred: "2025-01-15"
    source: str
    summary: Optional[str] = None
    url: Optional[str] = None


class FinancialDataProvider(ABC):
    """Abstract interface for financial market data APIs."""

    # Subclasses should override to describe the data source in markdown output.
    source_note: str = "Financial data provider"

    @abstractmethod
    def get_quote(self, ticker: str) -> Optional[StockQuote]:
        """
        Retrieve the latest quote and key metrics for a ticker.

        Returns None if the ticker is not found or the API is unavailable.
        """
        ...

    @abstractmethod
    def get_news(self, ticker: str, num_items: int = 5) -> List[NewsItem]:
        """
        Retrieve recent news items for a ticker.

        Returns a list of NewsItem objects in reverse chronological order.
        """
        ...

    def get_stock_data(self, ticker: str) -> Dict[str, Any]:
        """
        Return raw market data for a ticker as a flat dict.

        Keys present when available:
          price, market_cap_usd_b, ev_revenue_ratio, price_to_sales,
          pe_ratio, week_52_high, week_52_low, ytd_change_pct, cash_usd_b
        Missing fields are omitted (not set to None) so callers can use
        dict.get(...) with a default.
        """
        quote = self.get_quote(ticker)
        if quote is None:
            return {}
        result: Dict[str, Any] = {
            "price": quote.price,
            "market_cap_usd_b": quote.market_cap_usd_b,
        }
        for field in (
            "ev_revenue_ratio", "price_to_sales", "pe_ratio",
            "week_52_high", "week_52_low", "ytd_change_pct", "cash_usd_b",
        ):
            val = getattr(quote, field)
            if val is not None:
                result[field] = val
        return result


class RealYFinanceProvider(FinancialDataProvider):
    """
    Production implementation pulling data directly from Yahoo Finance APIs.

    Two-phase data fetch:
      Phase 1 — v8/finance/chart  (no auth required)
                 → current price, 52-week range, YTD, company name, exchange
      Phase 2 — v10/finance/quoteSummary  (requires crumb + cookies)
                 → market cap, EV/Revenue, cash, P/E, P/S
                 Uses curl_cffi with Chrome TLS impersonation to obtain cookies.

    Both phases fall back gracefully: if Phase 2 fails the quote is still
    returned with the Phase 1 fields populated and fundamentals set to None.

    Install dependencies:  pip install yfinance curl_cffi
    Data is subject to a 15-minute delay on NASDAQ/NYSE.
    """

    source_note = "Yahoo Finance (via yfinance)"

    _CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    _SUMMARY_URL = "https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
    _CRUMB_URL = "https://query1.finance.yahoo.com/v1/test/getcrumb"
    _SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"
    _YAHOO_HOME = "https://finance.yahoo.com"

    def __init__(self):
        self._crumb: Optional[str] = None
        self._session = None   # curl_cffi session, lazily initialised

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_quote(self, ticker: str) -> Optional[StockQuote]:
        """
        Fetch a StockQuote for *ticker* from Yahoo Finance.

        Returns None if the ticker is not found or both phases fail.
        """
        try:
            # Phase 1: chart endpoint (no auth)
            chart_data = self._fetch_chart(ticker)
            if chart_data is None:
                logger.warning("[RealYFinanceProvider] No chart data for %s.", ticker)
                return None

            meta = chart_data["meta"]
            price = float(meta.get("regularMarketPrice") or 0)
            if price <= 0:
                logger.warning("[RealYFinanceProvider] Zero price for %s.", ticker)
                return None

            name = meta.get("longName") or meta.get("shortName") or ticker
            exchange = meta.get("fullExchangeName") or meta.get("exchangeName") or "N/A"
            week_52_high = _safe_float(meta.get("fiftyTwoWeekHigh"))
            week_52_low = _safe_float(meta.get("fiftyTwoWeekLow"))

            # YTD from intraday close prices in chart payload
            ytd_change_pct = self._calc_ytd_from_chart(chart_data)

            # Phase 2: quoteSummary for fundamentals (optional, best-effort)
            market_cap_usd_b = None
            ev_revenue_ratio = None
            price_to_sales = None
            pe_ratio = None
            cash_usd_b = None

            summary = self._fetch_summary(ticker)
            if summary:
                price_section = summary.get("price") or {}
                stats = summary.get("defaultKeyStatistics") or {}
                fin = summary.get("financialData") or {}

                mc = _raw(price_section.get("marketCap"))
                market_cap_usd_b = mc / 1e9 if mc else None

                ev_rev = _raw(stats.get("enterpriseToRevenue"))
                ev_revenue_ratio = ev_rev if ev_rev and ev_rev > 0 else None

                ps = _raw(stats.get("priceToSalesTrailing12Months"))
                price_to_sales = ps if ps and ps > 0 else None

                pe = _raw(stats.get("trailingPE"))
                pe_ratio = pe if pe and pe > 0 else None

                cash = _raw(fin.get("totalCash"))
                cash_usd_b = cash / 1e9 if cash else None

            quote = StockQuote(
                ticker=ticker.upper(),
                name=name,
                exchange=exchange,
                price=price,
                market_cap_usd_b=market_cap_usd_b or 0.0,
                pe_ratio=pe_ratio,
                ev_revenue_ratio=ev_revenue_ratio,
                price_to_sales=price_to_sales,
                week_52_high=week_52_high,
                week_52_low=week_52_low,
                ytd_change_pct=ytd_change_pct,
                cash_usd_b=cash_usd_b,
            )
            logger.info(
                "[RealYFinanceProvider] %s: $%.2f | mktcap %s | EV/Rev %s | YTD %s",
                ticker,
                price,
                f"${market_cap_usd_b:.2f}B" if market_cap_usd_b else "N/A",
                f"{ev_revenue_ratio:.1f}x" if ev_revenue_ratio else "N/A",
                f"{ytd_change_pct*100:+.1f}%" if ytd_change_pct is not None else "N/A",
            )
            return quote

        except Exception as exc:
            logger.error("[RealYFinanceProvider] get_quote(%s) failed: %s", ticker, exc)
            return None

    def get_news(self, ticker: str, num_items: int = 5) -> List[NewsItem]:
        """
        Fetch recent news for *ticker* via Yahoo Finance search API.

        Returns an empty list on any error.
        """
        try:
            crumb = self._get_crumb()
            session = self._get_session()
            params: Dict[str, Any] = {
                "q": ticker,
                "newsCount": num_items,
                "quotesCount": 0,
            }
            if crumb:
                params["crumb"] = crumb

            resp = session.get(self._SEARCH_URL, params=params, timeout=10)
            if resp.status_code != 200:
                logger.warning(
                    "[RealYFinanceProvider] News search returned %d for %s.",
                    resp.status_code, ticker,
                )
                return []

            raw_news = resp.json().get("news", [])
            items: List[NewsItem] = []
            for article in raw_news[:num_items]:
                ts = article.get("providerPublishTime")
                date_str = (
                    datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
                    if ts else "unknown"
                )
                headline = (article.get("title") or "").strip()
                if not headline:
                    continue
                items.append(
                    NewsItem(
                        headline=headline,
                        date=date_str,
                        source=article.get("publisher", "Yahoo Finance"),
                        url=article.get("link"),
                    )
                )
            logger.info(
                "[RealYFinanceProvider] News for %s: %d items.", ticker, len(items)
            )
            return items

        except Exception as exc:
            logger.warning(
                "[RealYFinanceProvider] get_news(%s) failed: %s", ticker, exc
            )
            return []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_session(self):
        """Return (and lazily create) a curl_cffi session with Chrome impersonation."""
        if self._session is None:
            try:
                from curl_cffi import requests as cffi_req
                self._session = cffi_req.Session(impersonate="chrome110")
                # Warm up cookies by visiting Yahoo Finance
                self._session.get(self._YAHOO_HOME, timeout=10)
                logger.debug("[RealYFinanceProvider] curl_cffi session initialised.")
            except ImportError:
                import requests
                logger.warning(
                    "[RealYFinanceProvider] curl_cffi not available; "
                    "falling back to requests (some endpoints may fail)."
                )
                self._session = requests.Session()
                self._session.headers["User-Agent"] = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
        return self._session

    def _get_crumb(self) -> Optional[str]:
        """Obtain (and cache) the Yahoo Finance crumb token."""
        if self._crumb:
            return self._crumb
        try:
            session = self._get_session()
            resp = session.get(self._CRUMB_URL, timeout=10)
            crumb = resp.text.strip()
            if resp.status_code == 200 and crumb and "{" not in crumb:
                self._crumb = crumb
                logger.debug("[RealYFinanceProvider] Crumb obtained.")
            else:
                logger.warning(
                    "[RealYFinanceProvider] Crumb fetch failed (status %d).",
                    resp.status_code,
                )
        except Exception as exc:
            logger.warning("[RealYFinanceProvider] Crumb fetch error: %s", exc)
        return self._crumb

    def _fetch_chart(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Call v8/finance/chart — publicly accessible, no auth required.

        Returns the first result dict or None.
        """
        try:
            import requests
            resp = requests.get(
                self._CHART_URL.format(ticker=ticker.upper()),
                params={"interval": "1d", "range": "ytd", "includePrePost": "false"},
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                timeout=10,
            )
            if resp.status_code != 200:
                return None
            results = resp.json().get("chart", {}).get("result") or []
            return results[0] if results else None
        except Exception as exc:
            logger.warning("[RealYFinanceProvider] Chart fetch error for %s: %s", ticker, exc)
            return None

    def _fetch_summary(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Call v10/finance/quoteSummary with crumb — requires curl_cffi session.

        Returns the merged module dict or None on any failure.
        """
        try:
            crumb = self._get_crumb()
            if not crumb:
                return None
            session = self._get_session()
            params: Dict[str, Any] = {
                "modules": "price,defaultKeyStatistics,financialData",
                "formatted": "false",
                "crumb": crumb,
            }
            resp = session.get(
                self._SUMMARY_URL.format(ticker=ticker.upper()),
                params=params,
                timeout=10,
            )
            if resp.status_code != 200:
                logger.debug(
                    "[RealYFinanceProvider] quoteSummary %d for %s.", resp.status_code, ticker
                )
                return None
            result_list = resp.json().get("quoteSummary", {}).get("result") or []
            if not result_list:
                return None
            # Merge all modules into one flat dict
            merged: Dict[str, Any] = {}
            for module in result_list:
                merged.update(module)
            return merged
        except Exception as exc:
            logger.warning(
                "[RealYFinanceProvider] quoteSummary error for %s: %s", ticker, exc
            )
            return None

    @staticmethod
    def _calc_ytd_from_chart(chart_data: Dict[str, Any]) -> Optional[float]:
        """Compute YTD % change from the close prices in a chart API payload."""
        try:
            closes = (
                chart_data.get("indicators", {})
                .get("quote", [{}])[0]
                .get("close", [])
            )
            closes = [c for c in closes if c is not None]
            if len(closes) < 2:
                return None
            start, end = float(closes[0]), float(closes[-1])
            return (end - start) / start if start > 0 else None
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _safe_float(val) -> Optional[float]:
    """Return float(val) if val is truthy and positive, else None."""
    try:
        f = float(val)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def _raw(field) -> Optional[float]:
    """
    Extract a numeric value from a Yahoo Finance quoteSummary field.

    Fields can be dicts ({"raw": 1.23, "fmt": "1.23"}) or plain scalars.
    """
    if field is None:
        return None
    if isinstance(field, dict):
        return _safe_float(field.get("raw"))
    return _safe_float(field)
