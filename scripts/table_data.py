
import logging
from typing import NamedTuple, Optional
import os
import numpy as np
import pandas as pd
import pypsa

class extreme_period(NamedTuple):
    period: pd.Interval
    peak_hour: pd.Timestamp
    summed_cost: float
    peak_cost: float


def get_peak_hour_from_period(
    n: pypsa.Network,
    p: pd.Interval,
) -> pd.Timestamp:
    """Find the hour with the highest system cost (load * nodal_price) for a given interval."""
    nodal_costs = n.buses_t["marginal_price"].loc[p.left : p.right] * n.loads_t.p.loc[p.left : p.right]
    total_costs = nodal_costs.sum(axis=1)
    peak_hour = total_costs.idxmax()
    peak_cost = total_costs.max()
    return peak_hour, peak_cost


def global_difficult_periods(
    n: pypsa.Network,
    min_length: int,
    max_length: int,
    T: float,
    month_bounds: Optional[tuple[int, int]] = None,
) -> list[extreme_period]:
    """Find intervals with high global system cost."""
    nodal_costs = n.buses_t["marginal_price"] * n.loads_t["p_set"]
    total_costs = nodal_costs.sum(axis="columns")

    if month_bounds is not None:
        total_costs = total_costs.loc[
            (total_costs.index.month >= month_bounds[0])
            & (total_costs.index.month <= month_bounds[1])
        ]

    C = pd.Series(
        index=pd.IntervalIndex.from_tuples(
            [], closed="both", dtype="interval[datetime64[ns], both]"
        ),
        dtype="float64",
    )

    for w in range(min_length - 1, max_length - 1):
        intervals = pd.IntervalIndex.from_arrays(
            left=total_costs.index[:-w], right=total_costs.index[w:], closed="both"
        )
        costs = total_costs.rolling(w + 1).sum().iloc[w:]
        costs.index = intervals
        costs = costs.loc[costs.index.length <= pd.Timedelta(hours=w + 1)]
        costs = costs.loc[costs > T]

        if len(C) > 0:
            costs = costs.loc[
                ~np.array([costs.index.overlaps(I) for I in C.index]).any(axis=0)
            ]

        costs = costs.sort_values(ascending=False)
        non_overlapping_I = pd.IntervalIndex.from_tuples(
            [], closed="both", dtype="interval[datetime64[ns], both]"
        )
        for I in costs.index:
            if not any(non_overlapping_I.overlaps(I)):
                avg_cost = total_costs.loc[I.left : I.right].mean()
                while (
                    I.left > total_costs.index[0]
                    and total_costs.iloc[total_costs.index.searchsorted(I.left) - 1]
                    > avg_cost
                ):
                    I = pd.Interval(
                        left=total_costs.index[
                            total_costs.index.searchsorted(I.left) - 1
                        ],
                        right=I.right,
                        closed="both",
                    )
                while (
                    I.right < total_costs.index[-1]
                    and total_costs.iloc[total_costs.index.searchsorted(I.right) + 1]
                    > avg_cost
                ):
                    I = pd.Interval(
                        left=I.left,
                        right=total_costs.index[
                            total_costs.index.searchsorted(I.right) + 1
                        ],
                        closed="both",
                    )

                i = non_overlapping_I.searchsorted(I)
                non_overlapping_I = non_overlapping_I.insert(i, I)

        for I in non_overlapping_I:
            if len(C) == 0:
                C.loc[I] = total_costs.loc[I.left : I.right].sum()
            else:
                overlapping_I = C.index[C.index.overlaps(I)]
                C = C.drop(overlapping_I)
                left = min([I.left, *overlapping_I.left])
                right = max([I.right, *overlapping_I.right])
                I = pd.Interval(left=left, right=right, closed="both")
                C.loc[I] = total_costs.loc[I.left : I.right].sum()

        C = C.sort_index()

    result = []
    for p in C.index:
        peak_hour, peak_cost = get_peak_hour_from_period(n, p)
        result.append(extreme_period(period=p, peak_hour=peak_hour, summed_cost=C.loc[p], peak_cost=peak_cost))

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    network_folder = os.getenv("NETWORK_FOLDER")
    network_files = [f for f in os.listdir(network_folder) if f.endswith(".nc")]
    ns = {fn: pypsa.Network(os.path.join(network_folder, fn)) for fn in network_files}

    period_config = {
        "min_cost": 100.e+9,
        "min_length": 30,
        "max_length": 336
    }

    period_collection = [
        (file_name, global_difficult_periods(
            n,
            T=period_config["min_cost"],
            min_length=period_config["min_length"],
            max_length=period_config["max_length"],
        ))
        for file_name, n in ns.items()
    ]

    periods = [(file_name, period) for file_name, periods in period_collection for period in periods]

    logging.info(f"Identified {len(periods)} difficult periods.")

    periods_df = pd.DataFrame(
        {
            "start": [p.period.left for _, p in periods],
            "end": [p.period.right for _, p in periods],
            "peak_hour": [p.peak_hour for _, p in periods],
            "summed_cost": [p.summed_cost for _, p in periods],
            "peak_cost": [p.peak_cost for _, p in periods],
            "file_name": [file_name for file_name, _ in periods]
        }
    )

    periods_df.sort_values("start", inplace=True)
    periods_df.reset_index(drop=True, inplace=True)

    periods_df["start"] = periods_df["start"].dt.tz_localize(tz="UTC")
    periods_df["end"] = periods_df["end"].dt.tz_localize(tz="UTC")
    periods_df["peak_hour"] = periods_df["peak_hour"].dt.tz_localize(tz="UTC")

    periods_df.to_csv(f"{network_folder}/table_data.csv", index=False)
