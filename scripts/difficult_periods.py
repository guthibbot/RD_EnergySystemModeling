# SPDX-FileCopyrightText: 2023 Koen van Greevenbroek & Aleksander Grochowicz
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Find difficult periods across a collection of networks.

We use the dual variables corresponding to "demand met"-constraints to
identify periods that were difficult for the energy system model. For
this, we need optimised networks.
"""

import logging
from typing import NamedTuple, Optional

import numpy as np
import pandas as pd
import pypsa
#from _helpers import configure_logging


class extreme_period(NamedTuple):
    period: pd.Interval
    peak_hour: pd.Timestamp


def get_peak_hour_from_period(
    n: pypsa.Network,
    p: pd.Interval,
) -> list:
    """Find the hour with the highest system cost (load * nodal_price) for a given interval.

    Parameters
    ----------
    n : pypsa.Network
        The network for which to find difficult periods.
    p: pd.Interval
        Period of interest, represented as pd.Interval.

    Returns
    -------
    peak_hours: list[pd.Timestamp]
        A list of the most extreme timestamp for the list of periods of interest."""

    return (
        (
            n.buses_t["marginal_price"].loc[p.left : p.right]
            * n.loads_t.p.loc[p.left : p.right]
        )
        .sum(axis=1)
        .idxmax()
    )


def global_difficult_periods(
    n: pypsa.Network,
    min_length: int,
    max_length: int,
    T: float,
    month_bounds: Optional[tuple[int, int]] = None,
) -> pd.DataFrame:
    """Find intervals with high global system cost.

    The intervals will have a length between `min_length` and
    `max_length`, over which the total system costs adds up to a value
    greater than `T`.

    NOTE: for now, this function assumes that the network `n` has
    hourly resolution!

    Parameters
    ----------
    n : pypsa.Network
        The network for which to find difficult periods.
    min_length : int
        The minimum length of the intervals to consider, in hours.
    max_length : int
        The maximum length of the intervals to consider, in hours.
    T : float
        The threshold for the total system costs to be exceeded, in EUR.
    month_bounds : Optional[tuple[int, int]] = None
        Optionally, specify in which months to search for difficult
        periods. In this argument is not None, only periods in given
        month interval are returned. The interval is inclusive and
        cyclic. For example, if `month_bounds == (11, 2)`, only
        periods contained entirely within the November-February range
        (inclusive) are returned.

    Returns
    -------
    namedtuple consisting of
        list[pd.Interval]
            A list of the periods of interest, represented as pd.Interval.
        list[pd.Timestamp]
            A list of the most extreme timestamp for the list of periods of interest.
    """

    # TODO: the following only works for hourly resolution!
    nodal_costs = n.buses_t["marginal_price"] * n.loads_t["p_set"]
    total_costs = nodal_costs.sum(axis="columns")

    if month_bounds is not None:
        total_costs = total_costs.loc[
            (total_costs.index.month >= month_bounds[0])
            & (total_costs.index.month <= month_bounds[1])
        ]

    # Create an empty series, but specifying the type of index it's
    # going to have: an datetime interval index.
    C = pd.Series(
        index=pd.IntervalIndex.from_tuples(
            [], closed="both", dtype="interval[datetime64[ns], both]"
        ),
        dtype="float64",
    )

    for w in range(min_length - 1, max_length - 1):
        # Create array of intervals of width w+1
        intervals = pd.IntervalIndex.from_arrays(
            left=total_costs.index[:-w], right=total_costs.index[w:], closed="both"
        )
        # Find total costs for all intervals of width w+1
        costs = total_costs.rolling(w + 1).sum().iloc[w:]
        costs.index = intervals
        # In case we are only looking at intervals within some given
        # months, the index of `costs` might actually consist of two
        # disjoint seasons (e.g. July-October and April-June), leading
        # to some intervals that span the "gap" between these seasons.
        # Filter those out by only keeping intervals with an actual
        # duration of w+1 hours
        costs = costs.loc[costs.index.length <= pd.Timedelta(hours=w + 1)]

        # Filter out the intervals costing less than T
        costs = costs.loc[costs > T]

        # Filter out the intervals that overlap with existing intervals
        if len(C) > 0:
            costs = costs.loc[
                ~np.array([costs.index.overlaps(I) for I in C.index]).any(axis=0)
            ]

        # Also filter out intervals in `non_overlapping_I` that
        # overlap with each other. Sort the intervals by cost (from
        # highest to lowest) and take each interval in turn as long as
        # it doesn't overlap any of the previously taken intervals.
        costs = costs.sort_values(ascending=False)
        # (Again, we need to specify the type of index explicitly when
        # initialising it empty.)
        non_overlapping_I = pd.IntervalIndex.from_tuples(
            [], closed="both", dtype="interval[datetime64[ns], both]"
        )
        for I in costs.index:
            if not any(non_overlapping_I.overlaps(I)):
                # Now that we have committed to selecting the interval
                # I, we can see if it's actually natural to "expand" I
                # in either direction. We only want to expand I by
                # times at which the cost is greater than the average
                # cost of I. First, find the average cost of I.
                avg_cost = total_costs.loc[I.left : I.right].mean()
                # Now, expand I in both directions as long as the cost
                # is greater than the average cost of I
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

                # Insert in sorted order
                i = non_overlapping_I.searchsorted(I)
                non_overlapping_I = non_overlapping_I.insert(i, I)

        # Add the intervals we found one by one. However, since the
        # intervals may be been extended, they may now still overlap
        # with some of the intervals in the index of C.
        # NOTE: this code path is not taken for the periods of our paper!
        for I in non_overlapping_I:
            if len(C) == 0:
                C.loc[I] = total_costs.loc[I.left : I.right].sum()
            else:
                # Find intervals in C that overlap with I
                overlapping_I = C.index[C.index.overlaps(I)]
                # Remove them from C
                C = C.drop(overlapping_I)
                # Create the union of I and all the intervals it overlaps with.
                left = min([I.left, *overlapping_I.left])
                right = max([I.right, *overlapping_I.right])
                I = pd.Interval(left=left, right=right, closed="both")
                # Add the union to C
                C.loc[I] = total_costs.loc[I.left : I.right].sum()

        C = C.sort_index()

    return [extreme_period(p, get_peak_hour_from_period(n, p)) for p in C.index]


## ADJUSTED FOLLOWING PART. MADE SO NO SNAKEMAKE INPUT/OUTPUT NEEDED

import os

if __name__ == "__main__":
    # Configure logging manually if not using snakemake
    logging.basicConfig(level=logging.INFO)

    network_folder = os.getenv("NETWORK_FOLDER")
    #network_folder = "networks/outputs/solved"

    # Get all .nc files from the folder
    network_files = [f for f in os.listdir(network_folder) if f.endswith(".nc")]

    # Load each network
    ns = {fn: pypsa.Network(os.path.join(network_folder, fn)) for fn in network_files}

    ##PERIODS DEFINITIONS COPIED FROM CONFIG FILE
    # Configuration parameters (example values, adapt as needed)
    period_config = {
        "min_cost": 100.e+9,  # minimum total cost of difficult period in EUR
        "min_length": 30,     # minimum duration in hours
        "max_length": 336    # maximum duration in hours; 14 days
    }

    # Get globally difficult periods for each network
    period_collection = [
        (file_name, global_difficult_periods(
            n,
            T=period_config["min_cost"],
            min_length=period_config["min_length"],
            max_length=period_config["max_length"],
        ))
        for file_name, n in ns.items()
    ]

    # Flatten the list of periods
    periods = [(file_name, period) for file_name, periods in period_collection for period in periods]

    logging.info(f"Identified {len(periods)} difficult periods.")

    # Combine the extreme events
    periods_df = pd.DataFrame(
        {
            "start": [p.period.left for _, p in periods],
            "end": [p.period.right for _, p in periods],
            "peak_hour": [p.peak_hour for _, p in periods],
            "file_name": [file_name for file_name, _ in periods]
        }
    )

    # Sort by start date
    periods_df.sort_values("start", inplace=True)
    periods_df.reset_index(drop=True, inplace=True)

    # # Explicitly specify that the timezone is UTC
    # periods_df["start"] = periods_df["start"].dt.tz_localize(tz="UTC")
    # periods_df["end"] = periods_df["end"].dt.tz_localize(tz="UTC")
    # periods_df["peak_hour"] = periods_df["peak_hour"].dt.tz_localize(tz="UTC")

    # Ensure "start", "end", and "peak_hour" columns are datetime before localization
    if not periods_df.empty:
        for col in ["start", "end", "peak_hour"]:
            if not pd.api.types.is_datetime64_any_dtype(periods_df[col]):
                # Convert to datetime if possible
                periods_df[col] = pd.to_datetime(periods_df[col], errors="coerce")

        # Check again if columns are now datetime and localize timezone
        for col in ["start", "end", "peak_hour"]:
            if pd.api.types.is_datetime64_any_dtype(periods_df[col]):
                periods_df[col] = periods_df[col].dt.tz_localize(tz="UTC")
    else:
        logging.warning("No difficult periods identified. Skipping datetime localization.")

    # Save the extreme events to a CSV
    periods_df.to_csv(f"{network_folder}/difficult_periods.csv", index=False)
