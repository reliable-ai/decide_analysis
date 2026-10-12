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
import warnings
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

    # if the input is incorrectly formatted or has some sort of sparsity that
    # makes it impossible to accurately estimate, then we want to throw an error
    # instead of returning bad importances.
    missing_choices = multiverse_results[dimension_order].isna().any()
    if missing_choices.any():
        raise ValueError(
            f"Judgment call(s) {list(missing_choices[missing_choices].index)} "
            f"contain NA values; encode them as an explicit option instead."
        )
    metric_values = multiverse_results[performance_metrics].to_numpy(dtype=float)
    if not np.isfinite(metric_values).all():
        raise ValueError(
            "Performance metric(s) contain NA or infinite values (e.g. failed "
            "runs); drop those universes first."
        )
    num_duplicates = multiverse_results.duplicated(subset=dimension_order).sum()
    if num_duplicates > 0:
        raise ValueError(
            f"{num_duplicates} universe(s) appear more than once (same choices "
            f"for every judgment call); aggregate them first (e.g. over seeds)."
        )

    # if the multiverse is such that the option (singular) available at the jth
    # decision is a deterministic function of the choice made at the ith
    # decision, this means that the ith decision never varies on its own, so its
    # importance is not identifiable since it can't be separated from i. Since
    # the choice for the ith decision is encoded in the choice at i, we can drop
    # the column corresponding to the choice made for decision j. We will give
    # the user a warning in case they were not familiar that this was happening
    # in their multiverse.
    dimension_order = list(dimension_order)  # avoid mutating the input
    for j in list(dimension_order):
        if multiverse_results[j].nunique() < 2:
            raise ValueError(
                f"Judgment call '{j}' has only one option, so it is not a "
                f"valid decision; remove it from dimension_order."
            )
        for i in dimension_order:
            if i != j and multiverse_results.groupby(i)[j].nunique().max() == 1:
                warnings.warn(
                    f"Judgment call '{j}' is fully determined by '{i}', so it "
                    f"will be merged into '{i}' and dropped as a separate "
                    f"decision.",
                    stacklevel=2,
                )
                multiverse_results = multiverse_results.drop(columns=j)
                dimension_order.remove(j)
                break  # since j is removed, stop searching over it

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
    exclude_inert: bool = False,
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
        exclude_inert (bool, optional): Some decisions do not apply in certain
            backgrounds but are still listed there, so all of their options
            give identical results (e.g. in YRBS, combination when y_variable
            is a singleton). Identical results can also happen by coincidence
            when the decision does apply (e.g. with discrete outcomes), so by
            default (False) these backgrounds are kept as zeros and only
            reported through "inert_share". Set to True to calculate the
            importance only over the backgrounds where the decision applies.

    Returns:
        dict: mapping each non-empty tuple of judgment call names (up to
            max_order) to a dict with keys "main_effect" and
            "total_effect", plus "interaction_effect" for subsets with
            |S| >= 2 (omitted for singletons -- see interaction_effect above).
            Only relevant for sparse multiverses, each judgment call's dict also
            has "applicability_share", the proportion of backgrounds included in
            total_effect, and "inert_share", the proportion of backgrounds where
            all options give identical results (see exclude_inert). With
            Lambda = mean and exclude_inert=True, total_effect *
            applicability_share equals the total_effect obtained with
            exclude_inert=False.
    """
    dimension_cols = [
        col for col in multiverse_results.columns if col[1] == "dimension"
    ]
    dimension_names = [col[0] for col in dimension_cols]

    if max_order is None:
        max_order = len(dimension_names)

    # flatten the MultiIndex columns once up front for speed
    flat = multiverse_results.copy()
    flat.columns = [col[0] for col in multiverse_results.columns]
    perf_values = flat[performance_metric].to_numpy()

    def summarize_groups(names):
        # lambda applied within each group formed by `names`.
        # Returns the group each row belongs to alongside one summary value per
        # group so that callers can index numpy arrays rather than
        # slice the frame once per group.
        grouped = flat.groupby(list(names), sort=True)
        group_ids = grouped.ngroup().to_numpy()
        group_summaries = np.array(
            [summary(perf_values[grouped.indices[key]]) for key in sorted(grouped.indices)]
        )
        return group_ids, group_summaries

    # --- main effects: Phi_{s_S}(Lambda_{p_{-S}}(f)) for every subset ---
    main_effect = {}
    for size in range(1, max_order + 1):
        for target_dims in combinations(dimension_names, size):
            _, group_summaries = summarize_groups(target_dims)
            main_effect[target_dims] = float(spread(group_summaries))

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

    # --- total effects: total effect of every subset ---
    total_effect = {}
    applicability_share = {}
    inert_share = {}
    for size in range(1, max_order + 1):
        for target_dims in combinations(dimension_names, size):
            other_dims = [d for d in dimension_names if d not in target_dims]

            if not other_dims:
                # target_dims covers every decision: one background context (the
                # whole dataset), every combination of target_dims is real.
                total_effect[target_dims] = float(spread(perf_values))
                applicability_share[target_dims] = 1.0
                inert_share[target_dims] = float(np.all(perf_values == perf_values[0]))
                continue

            # average-case counterfactual for every combination of target_dims'
            # choices that occurs anywhere in the multiverse: Lambda over the
            # rest of the pipeline, unconditioned on anything else. This also
            # defines the full comparable-set space -- combinations that never
            # occur anywhere are not considered, since there is no data to ground
            # them in.
            combo_ids, imputed_means = summarize_groups(target_dims)
            context_ids = flat.groupby(other_dims, sort=True).ngroup().to_numpy()

            # visit each background context by sorting the rows by context once,
            # rather than slicing the frame once per context
            order = np.argsort(context_ids, kind="stable")
            sorted_ids = context_ids[order]
            starts = np.flatnonzero(
                np.concatenate(([True], sorted_ids[1:] != sorted_ids[:-1]))
            )
            ends = np.concatenate((starts[1:], [len(order)]))
            num_contexts = len(starts)

            # a context is missing a combination whenever no row realises that
            # (context, combination) pair, so count the pairs that do occur
            num_realized = len(
                np.unique(context_ids.astype(np.int64) * len(imputed_means) + combo_ids)
            )
            num_imputed = num_contexts * len(imputed_means) - num_realized

            phi_values = []
            is_inert = []  # whether target_dims is a no-op in each background
            for start, end in zip(starts, ends):
                rows = order[start:end]
                # start from the average-case counterfactual everywhere, then
                # overwrite the combinations this context actually realised
                comparable_set = imputed_means.copy()
                comparable_set[combo_ids[rows]] = perf_values[rows]
                phi_values.append(spread(comparable_set))
                # a background where target_dims has at least two options
                # listed, but they all give the same result
                is_inert.append(
                    len(rows) >= 2 and np.all(perf_values[rows] == perf_values[rows[0]])
                )

            if num_imputed > 0:
                # the multiverse is ragged for this specific subset: at least
                # one background context was missing a real outcome for one
                # of target_dims' choices, so total_effect partly relies on
                # imputed average-case counterfactuals rather than purely
                # observed adjacent universes (see UNBALANCED_TREES.md). This
                # also means total_effect ~= main_effect + interaction_effect
                # only holds approximately for this subset.
                warnings.warn(
                    f"total_effect for {target_dims} used {num_imputed} "
                    f"imputed average-case counterfactual value(s) out of "
                    f"{num_contexts} background contexts (multiverse is "
                    f"ragged for this subset). total_effect ~= main_effect + "
                    f"interaction_effect will only hold approximately here.",
                    stacklevel=2,
                )

            # This addresses the case where the decision doesn't apply in some
            # backgrounds, but is still listed there (thus, there is no
            # difference in the downstream results across its options).
            # This can also happen by coincidence if a decision just doesn't
            # matter as well, so we only report this proportion by default, and
            # leave it out if the user asks to exclude these backgrounds, which
            # is recommended if they know a priori that the decision doesn't
            # apply in some backgrounds.
            is_inert = np.asarray(is_inert)
            inert_share[target_dims] = float(is_inert.mean())
            included = ~is_inert if exclude_inert else np.ones_like(is_inert)
            applicability_share[target_dims] = float(included.mean())

            if not included.any():
                # target_dims does not apply in any background, so there is
                # nothing to estimate; refuse rather than guess
                warnings.warn(
                    f"total_effect for {target_dims} is not estimable: it does "
                    f"not apply in any background context, so it is reported "
                    f"as NaN.",
                    stacklevel=2,
                )
                total_effect[target_dims] = np.nan
                continue

            # aggregate the per-context spreads of the included backgrounds with
            # Lambda (each included background context contributes one value)
            total_effect[target_dims] = float(
                summary(np.asarray(phi_values)[included])
            )

    # --- assemble per-subset results ---
    decomposition = {}
    for target_dims in main_effect:
        entry = {
            "total_effect": total_effect[target_dims],
            "main_effect": main_effect[target_dims],
            "applicability_share": applicability_share[target_dims],
            "inert_share": inert_share[target_dims],
        }
        # interaction_effect(S) == main_effect(S) for |S| == 1 by construction
        # (see the recursion above), so it's only reported for |S| >= 2 to
        # avoid encoding the same number under two names.
        if len(target_dims) >= 2:
            entry["interaction_effect"] = interaction_effect[target_dims]
        decomposition[target_dims] = entry

    return decomposition
