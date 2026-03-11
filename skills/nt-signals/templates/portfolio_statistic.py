# -------------------------------------------------------------------------------------------------
#  NautilusTrader PortfolioStatistic Template
#
#  Subclass PortfolioStatistic to define custom analysis metrics.
#  Statistics are automatically computed by PortfolioAnalyzer after backtests/live runs.
#
#  Return values MUST be JSON-serializable (float, int, str, bool, None).
# -------------------------------------------------------------------------------------------------

from typing import Any

import pandas as pd

from nautilus_trader.analysis.statistic import PortfolioStatistic


class MyPortfolioStatistic(PortfolioStatistic):
    """
    TODO: Describe what this statistic calculates.

    Returns
    -------
    float or None
        TODO: Describe the return value.
    """

    def calculate_from_returns(self, returns: pd.Series) -> Any | None:
        """
        Calculate statistic from a time series of returns.

        Parameters
        ----------
        returns : pd.Series
            Time series of returns.

        Returns
        -------
        Any or None
            The calculated statistic value, or None if insufficient data.
        """
        if not self._check_valid_returns(returns):
            return None

        # TODO: Implement calculation
        # Use self._downsample_to_daily_bins(returns) for annualized metrics
        result = returns.mean()
        return float(result)

    def calculate_from_realized_pnls(self, realized_pnls: pd.Series) -> Any | None:
        """
        Calculate statistic from realized P&L values.

        Parameters
        ----------
        realized_pnls : pd.Series
            Time series of realized P&L values.

        Returns
        -------
        Any or None
            The calculated statistic value, or None if insufficient data.
        """
        if realized_pnls is None or realized_pnls.empty:
            return None

        # TODO: Implement calculation
        result = realized_pnls.sum()
        return float(result)


# Registration:
#
# Add to BacktestEngine or PortfolioAnalyzer:
#   engine.add_statistic(MyPortfolioStatistic())
#
# Or via config:
#   from nautilus_trader.config import BacktestRunConfig
#   config = BacktestRunConfig(
#       ...
#       statistics=[MyPortfolioStatistic()],
#   )
