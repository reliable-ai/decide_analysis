"""
This file defines the metrics for assessing the downstream impact of judgment
calls in the multiverse. The supported decision importance measures are:

- Naive tree-based importance. This measure, which can be thought of as "within-
bucket" variation, measures the decrease in downstream spread caused by each
judgment call. When used with mean and variance as the summary statistics, this
metric is equivalent to mean decrease in impurity.
- DECIDE. This measure leverages multiverse structure by comparing universes
which differ only in particular decisions. By measuring the dispersion of each
comparable set (i.e., the universes which only differ in a particular decision),
we can attribute the variation in the downstream results to that decision.
This measure can be thought of as "between-bucket" variation.
"""

# imports
import pandas as pd
import numpy as np
from copy import deepcopy
from collections import defaultdict
from itertools import combinations


def organize_multiverse_results(
    multiverse_results: pd.DataFrame,
    dimension_order: list,
    performance_metrics: list
) -> pd.DataFrame:
    """
    The multiverse results come as a DataFrame with columns for each judgment
    call and performance metric of interest. Here, we properly order the
    judgment calls & get the subset of the results that apply for our analysis.

    Args:
        multiverse_results (pd.DataFrame): A DataFrame containing the results of
            the multiverse analysis.
        dimension_order (list): A list specifying the order of dimensions
            (judgment calls).
        performance_metrics (list): A list of performance metrics to consider.
    """

    # create copy of the multiverse results to avoid modifying the original
    multiverse_results = deepcopy(multiverse_results)

    # get the subset of the results that apply for our analysis
    multiverse_results = multiverse_results[dimension_order + performance_metrics]

    # give each column a certain level using multilevel indexing to denote
    # if it is a dimension (judgment call) or a performance metric
    multiverse_results.columns = pd.MultiIndex.from_tuples(
        [
            (col, "dimension")
            if col in dimension_order
            else (col, "performance_metric")
            for col in multiverse_results.columns
        ]
    )

    return multiverse_results


def spread_in_path(
    multiverse_results: pd.DataFrame,
    decision_path: dict,
    performance_metric: str
) -> pd.DataFrame:
    """
    Calculates the within-bucket variation for a particular decision path.
    This measures how much variance in the performance metric exists after
    making a specific series of judgment calls (i.e., following the specified
    decision path).

    Args:
        multiverse_results (pd.DataFrame): A DataFrame containing the results of
            the multiverse analysis.
        decision_path (dict): A dictionary specifying the series of decisions to
            follow (e.g. {"spell_gap_threshold": 42, "model": "random_forest"}).
        performance_metric (str): The name of the performance metric to analyze.
    Returns:
        float: The variance of the performance metric across the remaining
            universes after filtering for the specified decision path.
    """

    # create copy of the multiverse results to avoid modifying the original
    multiverse_results = deepcopy(multiverse_results)

    # filter the multiverse to only include rows that match the decision path
    for dimension, choice in decision_path.items():
        multiverse_results = multiverse_results[
            multiverse_results[(dimension, "dimension")] == choice
        ]

    # calculate the variance of the performance metric across the remaining
    # universes (i.e., different combinations of the remaining judgment calls)
    variance = multiverse_results[(performance_metric, "performance_metric")].var(
        ddof=0
    )  # use population variance for within-bucket variation

    return variance


def naive_tree_based_importance(
    multiverse_results: pd.MultiIndex, performance_metric: str
) -> dict:
    """
    Calculate the within-bucket variation for a given performance metric. This
    measures how much the performance metric varies within each bucket (i.e.,
    within each combination of judgment calls).

    Args:
        multiverse_results (pd.DataFrame): A DataFrame containing the results
            of the multiverse analysis.
        performance_metric (str): The name of the performance metric to analyze.
    Returns:
        dict: A dictionary containing the within-bucket variation of each
            judgment call for the specified performance metric. Keys are the
            dimension names, values are the variation.
    """

    # because the judgment calls are organized chronologically, we can calculate
    # the within-bucket variation by going column-by-column
    # and calculating the variance of the performance metric across the
    # different forks of the multiverse.

    # create copy of the multiverse results to avoid modifying the original
    multiverse_results = deepcopy(multiverse_results)

    # STEP 1
    # enumerate the nodes in the decision tree, where each node corresponds to
    # the series of judgment calls that lead to that node.
    decision_paths = [
        (0, {})
    ]  # list of tuples of the form (depth, path) where depth is an int and path is a dict of the form {dimension: choice}
    # loop through number of judgment calls, which is number of columns that are dimensions in the multiindex
    for depth in range(
        1, multiverse_results.columns.get_level_values(1).tolist().count("dimension")
    ):
        # get the unique combinations of judgment calls up to this depth
        unique_paths = multiverse_results.iloc[:, :depth].drop_duplicates()
        for _, row in unique_paths.iterrows():
            path = {col[0]: row[col] for col in unique_paths.columns}
            decision_paths.append((depth, path))

    # STEP 2
    # now that we have the decision paths enumerated, we want to organize them
    # into dictionaries keyed by the depth in the decision tree (i.e., the number of judgment calls made),
    # where the value is the list of the decision paths at that depth.
    decision_paths_by_depth = defaultdict(list)
    for depth, path in decision_paths:
        decision_paths_by_depth[depth].append(path)

    # print("`decision_paths_by_depth`:")
    # print(decision_paths_by_depth)

    # STEP 3
    # notice that we can get the variance of circle A by taking variance of all
    # paths that meet depth 0. variance of each B circle by taking variance
    # of each path at depth 1. etc.
    # so to get average variance due to the decision in the multiverse,
    # take mean(spread_in_path(path)) for each path at the depth correspnding to that decision.
    var_by_depth = {}
    for depth, paths in decision_paths_by_depth.items():
        paths_with_var = {}
        for path in paths:
            # get a tuple representation of the path, where the index in the
            # tuple is the order of the judgment call and the value is the
            # choice made for that judgment call. for example, if the first
            # judgment call is "spell_gap_threshold" and the second judgment
            # call is "model", then a path where the spell gap threshold is 42
            # and the model is random forest would be represented as
            # (42, "random_forest").
            path_tuple = []
            for dimension in multiverse_results.columns.get_level_values(0):
                if (dimension, "dimension") in multiverse_results.columns:
                    if dimension in path:
                        path_tuple.append(path[dimension])
            path_tuple = tuple(path_tuple)
            paths_with_var[path_tuple] = spread_in_path(
                multiverse_results, path, performance_metric
            )
        var_by_depth[depth] = paths_with_var

    # print("`var_by_depth`:")
    # print(var_by_depth)

    # STEP 4
    # now we have the variance for each path at each depth. we want to use this
    # to calculate the decrease in variance at each split. specifically, we take
    # the variance of the leaves along a path before a split/decision is made,
    # then calculate the variance of the leaves down each potential decision
    # path. the analyst will want to spend more time on decisions that have a
    # larger range/variance/spread of these variances.
    # range_of_decreases_in_variance_by_depth = {}
    mean_decrease_in_variance_by_depth = {}
    for depth, paths_with_var in var_by_depth.items():
        dimension_name = multiverse_results.columns[depth][0]
        decreases_in_variance = []
        for path_tuple, var in paths_with_var.items():
            # get the paths that are one decision away from this path (i.e.,
            # the paths that are the same as this path except for one additional
            # judgment call)
            paths_one_decision_away = [
                p
                for p in var_by_depth.get(depth + 1, {}).keys()
                if p[:depth] == path_tuple
            ]
            # print(f"At depth {depth}, for path {path_tuple} with variance \
            # {var}, the paths one decision away are: \
            # {paths_one_decision_away}")
            for path_one_decision_away in paths_one_decision_away:
                var_one_decision_away = var_by_depth[depth + 1][path_one_decision_away]
                decrease_in_variance = var - var_one_decision_away
                decreases_in_variance.append(decrease_in_variance)
            # if we are at the last split (children are leaf nodes),
            # then there are no paths one decision away (will be represented as
            # empty list), and the decrease in variance is just the variance of
            # the current path.
            if len(paths_one_decision_away) == 0:
                # print(f"At depth {depth}, for path {path_tuple} with \
                # variance {var}, there are no paths one decision away, so \
                # the decrease in variance is just the variance of the \
                # current path.")
                decreases_in_variance.append(var)
        # could take a variety of functions to summarize the decreases in
        # variance at this depth, such as range, variance, etc.
        # range_of_decreases_in_variance_by_depth[depth] = \
        #     np.max(decreases_in_variance) - np.min(decreases_in_variance)
        mean_decrease_in_variance_by_depth[dimension_name] = np.mean(
            decreases_in_variance
        )

    return mean_decrease_in_variance_by_depth


def decide(
    multiverse_results: pd.DataFrame,
    performance_metric: str,
    max_order: int = 1,
    spread=np.var,
    summary=np.mean,
) -> dict:
    """
    Single entry point for the DECIDE decomposition of a multiverse.

    For every non-empty subset S of judgment calls with |S| <= max_order, this
    reports how much of the variation in the performance metric is attributable
    to S. This should be functional for both full-factorial (balanced)
    multiverses and for irregular/ragged ones (e.g., where a judgment call only
    unlocks certain choices conditional on an upstream decision).

    Dispersion and aggregation are supplied as the generalized spread function
    Phi (`spread`) and summary function Lambda (`summary`). Each receives a 1-D
    numpy array of outcomes and returns a float.
    With the defaults (Phi = population variance, Lambda = mean) the quantities
    below reduce to the usual (unnormalized) Sobol' indices.

    Three quantities are reported per subset S:
      - main_effect        GME(S) = Phi_{s_S}(Lambda_{p_{-S}}(f)): the
                           "closed" first-to-|S|-order effect of S -- how much
                           the summarised outcome moves as S's choices vary,
                           aggregating over everything else. (Var(E[Y|X_S]) by
                           default.)
      - total_effect       DECIDE(S) = Lambda_{p_{-S}}(Phi(comparable set)):
                           the total effect of S -- the spread across S's choices
                           within each fixed background context, aggregated over
                           contexts (with an average-case counterfactual imputed
                           for choices of S that a context never realised).
                           (E[Var(Y|X_{-S})] by default.)
      - interaction_effect the pure marginal (Sobol / functional-ANOVA)
                           interaction of exactly S, obtained by stripping the
                           lower-order effects out of main_effect:
                           interaction_effect(S) = main_effect(S)
                                                   - sum_{T proper subset of S}
                                                        interaction_effect(T).
                           For |S| == 1 this is identical to main_effect, so it
                           is omitted from the returned dict for singletons
                           (main_effect already reports it; see below) and only
                           included for |S| >= 2. This decomposition relies on
                           the additivity of variance, so it is exact only for
                           Phi = variance / Lambda = mean and is a heuristic for
                           other spread functions. On a ragged tree the identity
                           total = main + interaction likewise only holds
                           approximately, since some values are imputed.

    Args:
        multiverse_results (pd.DataFrame): DataFrame with MultiIndex columns
            (name, "dimension"|"performance_metric"), as produced by
            organize_multiverse_results.
        performance_metric (str): Name of the performance metric to analyze.
        max_order (int, optional): Largest subset size to report. Defaults to 1
            (main + total effect for each single judgment call). Pass a larger
            value (or None for the full power set) to also get interaction
            effects up to that order.
        spread (callable, optional): Spread function Phi mapping a 1-D numpy
            array of outcomes to a dispersion value. Defaults to np.var
            (population variance, ddof=0).
        summary (callable, optional): Summary function Lambda mapping a 1-D numpy
            array of outcomes to an aggregate value. Defaults to np.mean.

    Returns:
        dict: mapping each non-empty tuple of judgment call names (up to
            max_order) to a dict with keys "var_total", "main_effect", and
            "total_effect", plus "interaction_effect" for subsets with
            |S| >= 2 (omitted for singletons -- see interaction_effect above).
    """
    dimension_cols = [
        col for col in multiverse_results.columns if col[1] == "dimension"
    ]
    dimension_names = [col[0] for col in dimension_cols]

    perf_col = (performance_metric, "performance_metric")

    if max_order is None:
        max_order = len(dimension_names)

    def summarize_groups(cols):
        # lambda applied within each group formed by `cols`, returning one
        # summary value per group (indexed by the group's key tuple).
        return (
            multiverse_results[perf_col]
            .groupby([multiverse_results[col] for col in cols])
            .apply(lambda s: summary(s.to_numpy()))
        )

    # var_total is the same scalar for every subset (total spread of outcomes).
    var_total = float(spread(multiverse_results[perf_col].to_numpy()))

    # --- main effects: Phi_{s_S}(Lambda_{p_{-S}}(f)) for every subset ---
    main_effect = {}
    for size in range(1, max_order + 1):
        for target_dims in combinations(dimension_names, size):
            target_dim_cols = [(d, "dimension") for d in target_dims]
            group_summaries = summarize_groups(target_dim_cols)
            main_effect[target_dims] = float(spread(group_summaries.to_numpy()))

    # --- pure marginal (Sobol) interaction ---
    # interaction_effect(S) = main_effect(S) - sum over proper subsets T of S of
    # interaction_effect(T). Because every proper subset of an S with
    # |S| <= max_order is itself enumerated above, this is always well-defined.
    interaction_effect = {}
    for size in range(1, max_order + 1):
        for target_dims in combinations(dimension_names, size):
            lower = sum(
                interaction_effect[sub]
                for r in range(1, size) # no-op if size=1, so nothing happens
                for sub in combinations(target_dims, r)
            )
            interaction_effect[target_dims] = main_effect[target_dims] - lower

    # --- total effects: ragged-tree safe total effect of every subset ---
    total_effect = {}
    for size in range(1, max_order + 1):
        for target_dims in combinations(dimension_names, size):
            target_dim_cols = [(d, "dimension") for d in target_dims]
            other_dims = [d for d in dimension_names if d not in target_dims]
            other_dim_cols = [(d, "dimension") for d in other_dims]

            if not other_dim_cols:
                # target_dims covers every decision: one background context (the
                # whole dataset), every combination of target_dims is real.
                total_effect[target_dims] = float(
                    spread(multiverse_results[perf_col].to_numpy())
                )
                continue

            # average-case counterfactual for every combination of target_dims'
            # choices that occurs anywhere in the multiverse: Lambda over the
            # rest of the pipeline, unconditioned on anything else. This also
            # defines the full comparable-set space -- combinations that never
            # occur anywhere are not considered, since there is no data to ground
            # them in.
            grouped_means = summarize_groups(target_dim_cols)
            # normalize keys to tuples: groupby collapses a single-column key to
            # a bare scalar Index rather than a 1-element-tuple MultiIndex, which
            # would otherwise mismatch the tuple keys built from itertuples below.
            if len(target_dim_cols) == 1:
                imputed_means = {(k,): v for k, v in grouped_means.items()}
            else:
                imputed_means = grouped_means.to_dict()
            full_combo_space = list(imputed_means.keys())

            phi_values = []
            for _context, context_rows in multiverse_results.groupby(
                [multiverse_results[col] for col in other_dim_cols]
            ):
                real_by_combo = dict(
                    zip(
                        context_rows[target_dim_cols].itertuples(
                            index=False, name=None
                        ),
                        context_rows[perf_col],
                    )
                )
                comparable_set = [
                    real_by_combo[combo]
                    if combo in real_by_combo
                    else imputed_means[combo]
                    for combo in full_combo_space
                ]
                phi_values.append(spread(np.asarray(comparable_set)))

            # aggregate the per-context spreads with Lambda (equal weight per
            # background context by default)
            total_effect[target_dims] = float(summary(np.asarray(phi_values)))

    # --- assemble per-subset results ---
    decomposition = {}
    for target_dims in main_effect:
        entry = {
            "var_total": var_total,
            "main_effect": main_effect[target_dims],
            "total_effect": total_effect[target_dims],
        }
        # interaction_effect(S) == main_effect(S) for |S| == 1 by construction
        # (see the recursion above), so it's only reported for |S| >= 2 to
        # avoid encoding the same number under two names.
        if len(target_dims) >= 2:
            entry["interaction_effect"] = interaction_effect[target_dims]
        decomposition[target_dims] = entry

    return decomposition
