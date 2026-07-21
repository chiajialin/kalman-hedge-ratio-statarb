"""
Plot ES and NQ daily closing prices rebased to 100 at the start of the sample.

Rebasing both series to a common starting value of 100 allows direct visual
comparison of cumulative price appreciation despite the two contracts trading
at very different absolute price levels.
"""

import pandas as pd
import matplotlib.pyplot as plt

DATA_DIR = "data/raw"
OUTPUT_PATH = "data/processed/rebased_prices.png"


def load_prices(data_dir: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load ES and NQ daily OHLCV CSVs from data_dir."""
    es = pd.read_csv(f"{data_dir}/es_daily.csv", index_col="date", parse_dates=True)
    nq = pd.read_csv(f"{data_dir}/nq_daily.csv", index_col="date", parse_dates=True)
    return es, nq


def plot_rebased_prices(es: pd.DataFrame, nq: pd.DataFrame, save_path: str = None) -> None:
    """Plot ES and NQ closing prices rebased to 100 at the start of the sample."""
    es_rebased = es["close"] / es["close"].iloc[0] * 100
    nq_rebased = nq["close"] / nq["close"].iloc[0] * 100

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(es_rebased.index, es_rebased, label="ES (S&P 500 E-mini)", color="steelblue")
    ax.plot(nq_rebased.index, nq_rebased, label="NQ (Nasdaq-100 E-mini)", color="darkorange")

    ax.set_title("ES and NQ Continuous Futures — Daily Close (Rebased to 100)", fontsize=13)
    ax.set_xlabel("Date")
    ax.set_ylabel("Rebased Price (start = 100)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150)
        print(f"Saved to {save_path}")
    plt.show()


if __name__ == "__main__":
    es, nq = load_prices(DATA_DIR)
    plot_rebased_prices(es, nq, save_path=OUTPUT_PATH)
