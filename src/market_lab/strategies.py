from dataclasses import dataclass
import pandas as pd

@dataclass(frozen=True)
class Strategy:
    name: str = "trend"
    window: int = 50
    threshold: float = 0.03
    def signals(self, bars):
        if self.window < 2 or not 0 < self.threshold < 1:
            raise ValueError("Invalid parameters")
        close = bars.close
        mean = close.rolling(self.window, min_periods=self.window).mean()
        if self.name == "trend":
            # Enter above trailing SMA; exit on/below it. Warmup remains cash.
            return (close > mean).astype(float)
        if self.name == "mean_reversion":
            # Enter below SMA by threshold; exit on recovery to SMA.
            state = 0.0
            targets = []
            for price, avg in zip(close, mean):
                if pd.isna(avg):
                    state = 0.0
                elif price < avg * (1 - self.threshold):
                    state = 1.0
                elif price >= avg:
                    state = 0.0
                targets.append(state)
            return pd.Series(targets, index=bars.index)
        raise ValueError("Unknown strategy")
