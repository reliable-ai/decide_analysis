"""
Legacy multiverse metrics kept for reference / backwards compatibility.

The variance-decomposition family (main effect, total effect, and their
interactions) now lives in a single `decide` function in `metrics.py`.
The functions below are the earlier, superseded
implementations, preserved here rather than deleted:

- `between_bucket_variation`, `total_variance_decomposition`, and
  `total_variance_decomposition_with_interactions` are reproduced exactly by
  `decide` on balanced (full-factorial) multiverses; they assume a balanced
  design and raise on ragged trees.
- `generalized_main_effect` and `catchy_name_total_effect` are the ragged-safe
  main-effect and total-effect estimators whose logic `decide` now inlines.
- `buv_interactions` computes a genuinely different quantity that `decide` does
  not reproduce: a *conditional* pairwise interaction. It fixes every other
  decision, decomposes the c_i x c_k grid within each fixed context, and
  averages those per-context interaction variances. This coincides with
  `decide`'s marginal interaction only when there are no >=3-way interactions
  involving the pair; when higher-order interactions exist the two diverge,
  since the conditional version also absorbs the pair's share of those
  higher-order terms. It is also pairwise-only and assumes a balanced design.
"""

import pandas as pd
import numpy as np
from copy import deepcopy
from itertools import combinations


def buv_interactions(
    multiverse_results: pd.DataFrame,
    performance_metric: str,
) -> dict:
    """
    Computes BUV_int(i, k) for all pairs of dimensions (i < k).

    For each pair, fixes all other dimensions and computes the pure interaction
    variance V_joint - V_i - V_k, then averages over all fixed contexts.

    V_joint is the variance of the full c_i x c_k grid of outcomes. V_i is the
    variance of the row means (marginalising over k), and V_k is the variance of
    the column means (marginalising over i). Their difference isolates the
    variance attributable strictly to the joint movement of i and k, removing
    each dimension's independent main effect.

    Args:
        multiverse_results: DataFrame with MultiIndex columns
            (name, "dimension"|"performance_metric").
        performance_metric: Name of the performance metric to analyze.

    Returns:
        dict mapping (dim_i, dim_k) tuples to BUV_int(i, k) float values.
    """
    dimension_cols = [col for col in multiverse_results.columns
                      if col[1] == "dimension"]
    dimension_names = [col[0] for col in dimension_cols]

    perf_col = (performance_metric, "performance_metric")
    buv_int = {}

    for dim_i, dim_k in combinations(dimension_names, 2):
        other_dims = [d for d in dimension_names if d != dim_i and d != dim_k]
        other_dim_cols = [(d, "dimension") for d in other_dims]

        if other_dim_cols:
            # V_joint: Variance over the i*k grid for each context
            # We use [[perf_col]] to avoid the tuple-subsetting error, then extract the Series
            v_joint = multiverse_results.groupby(other_dim_cols)[[perf_col]].var(ddof=0)[perf_col]

            # V_i: Average over k first, then take variance over i within each context
            mean_over_k = multiverse_results.groupby(other_dim_cols + [(dim_i, "dimension")])[[perf_col]].mean()[perf_col]
            v_i = mean_over_k.groupby(level=list(range(len(other_dim_cols)))).var(ddof=0)

            # V_k: Average over i first, then take variance over k within each context
            mean_over_i = multiverse_results.groupby(other_dim_cols + [(dim_k, "dimension")])[[perf_col]].mean()[perf_col]
            v_k = mean_over_i.groupby(level=list(range(len(other_dim_cols)))).var(ddof=0)

            # Average the interaction variance across all fixed contexts
            interaction_var = (v_joint - v_i - v_k).mean()

        else:
            # Edge case: Only two dimensions exist in the entire dataset
            v_joint = multiverse_results[perf_col].var(ddof=0)

            # Wrap grouping keys in lists to ensure safe MultiIndex tuple handling
            v_i = multiverse_results.groupby([(dim_i, "dimension")])[[perf_col]].mean()[perf_col].var(ddof=0)
            v_k = multiverse_results.groupby([(dim_k, "dimension")])[[perf_col]].mean()[perf_col].var(ddof=0)

            interaction_var = v_joint - v_i - v_k

        buv_int[(dim_i, dim_k)] = float(interaction_var)

    return buv_int


def between_bucket_variation(multiverse_results: pd.MultiIndex,
                             performance_metric: str) -> dict:
    """
    Calculate the between-bucket variation for a given performance metric. This
    measures how much the performance metric varies across different buckets
    (i.e., different combinations of judgment calls).
    
    For each decision point s_i, we fix all other decisions (both upstream and
    downstream) and vary only s_i across its possible choices. The variation in
    the performance metric across those choices is attributable to s_i. We
    repeat this for every possible combination of the other decisions, giving
    a distribution of variations attributable to s_i.

    Args:
        multiverse_results (pd.DataFrame): A DataFrame containing the results
            of the multiverse analysis.
        performance_metric (str): The name of the performance metric to analyze.
    Returns:
        dict: A dictionary mapping each judgment call (dimension name) to a
            list of variation values (one per unique combination of all other
            decisions). Each value is the variance of the performance metric
            when only that judgment call is varied.
    """
    
    # create copy of the multiverse results to avoid modifying the original
    multiverse_results = deepcopy(multiverse_results)
    
    # get the list of dimension columns (judgment calls) in order
    dimension_cols = [col for col in multiverse_results.columns
                      if col[1] == "dimension"]
    dimension_names = [col[0] for col in dimension_cols]
    
    # IDEA
    # for each decision node s_i in the multiverse tree, we want to get the
    # decision paths that differ only in the choice made at s_i. if we order the
    # nodes as (s_1, ..., s_{i-1}, s_i, s_{i+1}, ..., s_d), where we have d
    # decisions, for each decision, we want the set
    # {(s_1, ..., s_{i-1}, j, s_{i+1}, ..., s_d): j is a possible choice at s_i}
    # along with the accuracy of each of these paths.
    
    # set up storage for later
    between_variation = {}
    
    # for each decision point s_i, fix all other decisions and vary only s_i
    for depth, target_dim in enumerate(dimension_names):
        
        # get s_j where i!=j (i.e., all dimensions except the target dimension)
        other_dims = [d for d in dimension_names if d != target_dim]
        
        # get all unique combinations of the OTHER dimensions
        other_dim_cols = [(d, "dimension") for d in other_dims]
        unique_other_combos = multiverse_results[other_dim_cols] \
            .drop_duplicates()
            
        # print(f"For target dimension {target_dim} at depth {depth}, the other dimensions are {other_dims} and the unique combinations of the other dimensions are:")
        # print(unique_other_combos)
        
        # for each unique combination of the other decisions, compute the
        # variance of the performance metric across the different choices of s_i
        variations = []
        for row_idx, other_decisions in unique_other_combos.iterrows():
            # print("row_idx")
            # print(row_idx)
            # print("other_decisions")
            # print(other_decisions)
            # filter to rows matching this combination of other decisions
            mask = pd.Series(True, index=multiverse_results.index)
            for other_dim in other_dims:
                mask &= (multiverse_results[(other_dim, "dimension")]
                         == other_decisions[(other_dim, "dimension")])
            # this subset of the multiverse differs only in the choice made at
            # s_i, so any variation in the performance metric across this
            # subset can be attributed to s_i.
            subset = multiverse_results.loc[mask]
            
            # print(f"Subset of multiverse results that differ only in the choice made at \
            #     target dimension {target_dim} for this combination of other \
            #         decisions:")
            # print(subset)
            
            # the remaining rows differ only in s_i — compute variance of
            # the performance metric across the different choices for s_i.
            # how do we best leverage these sets? each individual set tells us
            # how the decision at depth i impacts the performance metric by
            # comparison to other leaves in the set, we can see how important
            # the decision was for driving a good conclusion/outcome. so we can
            # take a summary statistic of the spread of the performance metric
            # within each group, such as taking the variance (or range) of the
            # performance metric of the leaves in the group, and later average
            # it across groups to get an overall measure of how much the
            # decision at depth i drives results.
            var = subset[(performance_metric, "performance_metric")].var()
            variations.append(var)
        
        # get the average variance within group, as mentioned in the notes above
        avg_spread = np.mean(variations)
        between_variation[target_dim] = avg_spread
    
    return between_variation


def total_variance_decomposition(multiverse_results: pd.MultiIndex,
                                 performance_metric: str) -> dict:
    """
    Applies the law of total variance, which tells us that for random variables
    $X$ and $Y$, $Var(Y) = E[Var(Y | X)] + Var(E[Y | X])$.
    
    The given `multiverse_results` object contains the final results for each
    universe, such that each universe is one row, with the columns representing
    the judgment calls made and the performance of that universe according to
    various user-selected metrics (e.g. accuracy, MSE, etc.).
    
    Consider one judgment call which we would like to examine to determine how
    much variation in the final result stems from this decision. In this case,
    the "groups" that we are conditioning on are determined by the other
    decisions made, such that each group consists of the universes where the
    set of decisions made for the other decisions are identical. If we have $d$
    decisions, each one having $c_1, ..., c_d$ options, and we are interested in
    the $i$th decision, that means that there are $c_1 * ... * c_{i-1} * c_{i+1}
    * c_d$ groups of size $c_i$.
    
    For each decision $i$ in {1, ..., $d$}, we want to calculate the following
    three quantities:
    1. $Var(Y)$: the variance of the performance metric across all universes in
        the multiverse.
    2. $E[Var(Y | X)]$: the expected variance of the performance metric
        within each group.
    3. $Var(E[Y | X])$: the variance of the expected performance metric
        across groups.
        
    Inputs:
        multiverse_results (pd.DataFrame): A DataFrame containing the results
            of the multiverse analysis, with a MultiIndex for columns where
            the first level indicates the name of the column and the second
            level indicates whether it is a "dimension" (judgment call) or a
            "performance_metric".
        performance_metric (str): The name of the performance metric to analyze.
        
    Returns:
        dict: A dictionary mapping each judgment call (dimension name) to a
            dictionary containing the three quantities described above.
    """
    
    # get the list of dimension columns (judgment calls) in order
    dimension_cols = [col for col in multiverse_results.columns
                      if col[1] == "dimension"]
    dimension_names = [col[0] for col in dimension_cols]

    # get the number of unique values for each dimension (judgment call)
    num_unique_values_by_dimension = {
        dimension: multiverse_results[(dimension, "dimension")].nunique()
        for dimension in dimension_names
    }

    perf_col = (performance_metric, "performance_metric")

    # var_total is identical for every target dimension, so compute it once
    var_total = np.var(multiverse_results[perf_col])

    variance_decomposition = {}

    # for each decision point s_i, we want to calculate the three quantities.
    # thus, we must condition on the groups determined by the other decisions,
    # which means we want to group by the other dimensions and calculate the
    # variance within each group and the mean within each group.
    for target_dim in dimension_names:

        # get s_j where i!=j (i.e., all dimensions except the target dimension)
        other_dims = [d for d in dimension_names if d != target_dim]
        other_dim_cols = [(d, "dimension") for d in other_dims]

        # assert that the number of unique combinations of the other dimensions
        # is equal to the product of the number of unique values
        # for each of the other dimensions.
        expected_num_groups = np.prod([num_unique_values_by_dimension[d] for d in other_dims])
        unique_other_combos = multiverse_results[other_dim_cols].drop_duplicates()
        assert unique_other_combos.shape[0] == expected_num_groups, \
            f"Expected {expected_num_groups} unique groups, but found {unique_other_combos.shape[0]} groups."

        expected_num_observations = num_unique_values_by_dimension[target_dim]

        if other_dim_cols:
            # replace the row-by-row mask loop with a vectorized groupby;
            # select the perf column as a Series first to avoid pandas tuple-key ambiguity
            grouped = multiverse_results[perf_col].groupby(
                [multiverse_results[col] for col in other_dim_cols]
            )

            group_sizes = grouped.size()
            assert (group_sizes == expected_num_observations).all(), \
                f"Expected {expected_num_observations} observations in each group, but found otherwise."

            group_vars  = grouped.var(ddof=0)  # use population variance for within-group variance
            group_means = grouped.mean()
        else:
            # only one dimension: the single group is the full dataset
            assert len(multiverse_results) == expected_num_observations, \
                f"Expected {expected_num_observations} observations in subset, but found {len(multiverse_results)} observations."
            group_vars  = pd.Series([multiverse_results[perf_col].var(ddof=0)])  # use population variance for within-group variance
            group_means = pd.Series([multiverse_results[perf_col].mean()])

        # main effect Var(E[Y|X_target]): group by target_dim itself (rather
        # than the other dims) and take the variance of those group means.
        # Note this is NOT the same as var_of_expected_values_across_groups
        # above, which groups by the other dims and therefore equals the main
        # effect of the *complement* of target_dim, not of target_dim itself.
        target_group_means = multiverse_results[perf_col].groupby(
            multiverse_results[(target_dim, "dimension")]
        ).mean()
        main_effect = np.var(target_group_means, ddof=0)

        variance_decomposition[target_dim] = {
            "var_total": var_total,
            # E[Var(Y|X)]: mean of within-group variances = total effect of target_dim
            "expected_var_within_groups": np.mean(group_vars),
            # Var(E[Y|X]): population variance (ddof=0) of group means, matching np.var default
            "var_of_expected_values_across_groups": np.var(group_means),
            # Var(E[Y|X_target]): true main effect of target_dim
            "main_effect": main_effect,
        }

    return variance_decomposition

def total_variance_decomposition_with_interactions(
    multiverse_results: pd.MultiIndex,
    performance_metric: str
) -> dict:
    """
    Applies the law of total variance, which tells us that for random variables
    $X$ and $Y$, $Var(Y) = E[Var(Y | X)] + Var(E[Y | X])$.

    The given `multiverse_results` object contains the final results for each
    universe, such that each universe is one row, with the columns representing
    the judgment calls made and the performance of that universe according to
    various user-selected metrics (e.g. accuracy, MSE, etc.).

    Consider one judgment call which we would like to examine to determine how
    much variation in the final result stems from this decision. In this case,
    the "groups" that we are conditioning on are determined by the other
    decisions made, such that each group consists of the universes where the
    set of decisions made for the other decisions are identical. If we have $d$
    decisions, each one having $c_1, ..., c_d$ options, and we are interested in
    the $i$th decision, that means that there are $c_1 * ... * c_{i-1} * c_{i+1}
    * c_d$ groups of size $c_i$.

    For each decision $i$ in {1, ..., $d$}, we want to calculate the following
    three quantities:
    1. $Var(Y)$: the variance of the performance metric across all universes in
        the multiverse.
    2. $E[Var(Y | X)]$: the expected variance of the performance metric
        within each group.
    3. $Var(E[Y | X])$: the variance of the expected performance metric
        across groups.

    Furthermore, instead of just treating X as one single decision, we can also
    consider the interaction effects between decisions by potentially
    treating X as multiple decisions. For example, if we have three decisions
    X_1, X_2, and X_3, we could consider the interaction effects between X_1 and
    X_2 by getting $Var(Y) = E[Var(Y | X_1, X_2)] + Var(E[Y | X_1, X_2])$. This
    function will also calculate the variance decomposition for all combinations
    of interactions between the decisions, so in this example it would calculate
    the variance decomposition for X_1, X_2, X_3, the interaction between X_1
    and X_2, the interaction between X_1 and X_3, the interaction between X_2
    and X_3, and the interaction between X_1, X_2, and X_3.

    Inputs:
        multiverse_results (pd.DataFrame): A DataFrame containing the results
            of the multiverse analysis, with a MultiIndex for columns where
            the first level indicates the name of the column and the second
            level indicates whether it is a "dimension" (judgment call) or a
            "performance_metric".
        performance_metric (str): The name of the performance metric to analyze.

    Returns:
        dict: A dictionary mapping each judgment call (dimension name) to a
            dictionary containing the three quantities described above.
    """

    # get the list of dimension columns (judgment calls) in order
    dimension_cols = [col for col in multiverse_results.columns
                      if col[1] == "dimension"]
    dimension_names = [col[0] for col in dimension_cols]

    # get the number of unique values for each dimension (judgment call)
    num_unique_values_by_dimension = {
        dimension: multiverse_results[(dimension, "dimension")].nunique()
        for dimension in dimension_names
    }

    perf_col = (performance_metric, "performance_metric")

    # var_total is identical for every subset, so compute it once
    var_total = np.var(multiverse_results[perf_col])

    variance_decomposition = {}

    # iterate over all non-empty subsets of dimensions (size 1 = main effects,
    # size > 1 = interaction terms). for each subset, X is the joint variable
    # formed by those dimensions, and we condition on the remaining dimensions.
    for size in range(1, len(dimension_names) + 1):
        for target_dims in combinations(dimension_names, size):
            target_dims_set = set(target_dims)

            # the "other" dimensions are those not in the current subset
            other_dims = [d for d in dimension_names if d not in target_dims_set]
            other_dim_cols = [(d, "dimension") for d in other_dims]

            # each group contains all combinations of the target dims' values,
            # so the expected group size is the product of their unique counts
            expected_num_observations = np.prod([num_unique_values_by_dimension[d] for d in target_dims])

            if other_dim_cols:
                # assert that the number of unique combinations of the other dimensions
                # is equal to the product of the number of unique values
                # for each of the other dimensions.
                # (skipped when other_dim_cols is empty: df[[]] behaves unexpectedly
                # with MultiIndex columns, and the single-group case is trivially correct)
                expected_num_groups = np.prod([num_unique_values_by_dimension[d] for d in other_dims])
                unique_other_combos = multiverse_results[other_dim_cols].drop_duplicates()
                assert unique_other_combos.shape[0] == expected_num_groups, \
                    f"Expected {expected_num_groups} unique groups, but found {unique_other_combos.shape[0]} groups."

                # group by the other dimensions; select perf column as a Series
                # first to avoid pandas tuple-key ambiguity on MultiIndex columns
                grouped = multiverse_results[perf_col].groupby(
                    [multiverse_results[col] for col in other_dim_cols]
                )

                group_sizes = grouped.size()
                assert (group_sizes == expected_num_observations).all(), \
                    f"Expected {expected_num_observations} observations in each group, but found otherwise."

                group_vars  = grouped.var(ddof=0)  # use population variance for within-group variance
                group_means = grouped.mean()
            else:
                # all dimensions are in the target subset: one group = full dataset
                assert len(multiverse_results) == expected_num_observations, \
                    f"Expected {expected_num_observations} observations, but found {len(multiverse_results)}."
                group_vars  = pd.Series([multiverse_results[perf_col].var(ddof=0)])  # use population variance for within-group variance
                group_means = pd.Series([multiverse_results[perf_col].mean()])

            # main effect Var(E[Y|X_target]): group by the target dims
            # themselves (rather than the other dims) and take the variance
            # of those group means. Note this is NOT the same as
            # var_of_expected_values_across_groups above, which groups by the
            # other dims and therefore equals the main effect of the
            # *complement* of target_dims, not of target_dims itself.
            target_dim_cols = [(d, "dimension") for d in target_dims]
            target_group_means = multiverse_results[perf_col].groupby(
                [multiverse_results[col] for col in target_dim_cols]
            ).mean()
            main_effect = np.var(target_group_means, ddof=0)

            # use a tuple key for all entries so single and multi-dim keys are
            # the same type and interaction keys are unambiguous
            variance_decomposition[target_dims] = {
                "var_total": var_total,
                # E[Var(Y|X)]: mean of within-group variances = total effect of target_dims
                "expected_var_within_groups": np.mean(group_vars),
                # Var(E[Y|X]): population variance (ddof=0) of group means
                "var_of_expected_values_across_groups": np.var(group_means),
                # Var(E[Y|X_target]): true main effect of target_dims
                "main_effect": main_effect,
            }

    return variance_decomposition

def generalized_main_effect(
    multiverse_results: pd.DataFrame,
    performance_metric: str,
    max_order: int = None,
) -> dict:
    """
    Computes GME(S) = Var(E[Y|X_S]) for every non-empty subset S of judgment
    calls, directly from the universes that were actually evaluated.

    Unlike total_variance_decomposition_with_interactions, this makes no
    assumption that the multiverse is a full-factorial (balanced) design.
    Some judgment calls may only unlock certain choices conditional on an
    upstream decision (e.g. s1=2 unlocking an extra choice for s2 that
    s1=1 does not have), so groups formed by conditioning on S can legitimately
    differ in size across the values of S. GME(S) only requires grouping the
    real universes by their realized values of S and taking the variance of
    the resulting group means, so it is well-defined regardless of whether
    those groups are the same size.

    Args:
        multiverse_results (pd.DataFrame): DataFrame with MultiIndex columns
            (name, "dimension"|"performance_metric"), as produced by
            organize_multiverse_results.
        performance_metric (str): Name of the performance metric to analyze.
        max_order (int, optional): Largest subset size to compute GME for.
            Defaults to considering every judgment call (i.e. the full power
            set of dimensions).

    Returns:
        dict: mapping each non-empty tuple of judgment call names to its
            GME (a float).
    """
    dimension_cols = [col for col in multiverse_results.columns
                      if col[1] == "dimension"]
    dimension_names = [col[0] for col in dimension_cols]

    perf_col = (performance_metric, "performance_metric")

    if max_order is None:
        max_order = len(dimension_names)

    gme = {}
    for size in range(1, max_order + 1):
        for target_dims in combinations(dimension_names, size):
            target_dim_cols = [(d, "dimension") for d in target_dims]
            group_means = multiverse_results[perf_col].groupby(
                [multiverse_results[col] for col in target_dim_cols]
            ).mean()
            gme[target_dims] = np.var(group_means, ddof=0)

    return gme

def catchy_name_total_effect(
    multiverse_results: pd.DataFrame,
    performance_metric: str,
    max_order: int = None,
) -> dict:
    """
    Computes CATCHY_NAME(S), the total effect of judgment call subset S, for
    every non-empty S, extended to multiverses where the tree is ragged (some
    judgment calls unlock extra choices only under specific upstream
    decisions, so a background context does not always have a real outcome
    for every possible choice of S).

    For a realized background context p_{-S} (a combination of every
    judgment call not in S), the comparable set should contain one outcome
    for every combination of S's choices that occurs anywhere in the
    multiverse. When a particular combination was never actually evaluated
    under that specific background context, it is replaced by the
    average-case counterfactual: the plain, unconditioned mean of Y over
    every real universe that does take that combination of S's choices,
    regardless of anything else. This never fabricates a specific matched
    universe; it only ever imputes with a directly-computable marginal mean,
    so every comparable set ends up the same size and every context is
    aggregated with equal weight.

    Args:
        multiverse_results (pd.DataFrame): DataFrame with MultiIndex columns
            (name, "dimension"|"performance_metric"), as produced by
            organize_multiverse_results.
        performance_metric (str): Name of the performance metric to analyze.
        max_order (int, optional): Largest subset size to compute
            CATCHY_NAME for. Defaults to considering every judgment call
            (the full power set of dimensions).

    Returns:
        dict: mapping each non-empty tuple of judgment call names to its
            CATCHY_NAME total effect (a float).
    """
    dimension_cols = [col for col in multiverse_results.columns
                      if col[1] == "dimension"]
    dimension_names = [col[0] for col in dimension_cols]

    perf_col = (performance_metric, "performance_metric")

    if max_order is None:
        max_order = len(dimension_names)

    catchy_name = {}
    for size in range(1, max_order + 1):
        for target_dims in combinations(dimension_names, size):
            target_dim_cols = [(d, "dimension") for d in target_dims]
            other_dims = [d for d in dimension_names if d not in target_dims]
            other_dim_cols = [(d, "dimension") for d in other_dims]

            if not other_dim_cols:
                # target_dims covers every decision: there is only one
                # background context (the whole dataset), and every
                # combination of target_dims is real by construction.
                catchy_name[target_dims] = float(
                    multiverse_results[perf_col].var(ddof=0)
                )
                continue

            # average-case counterfactual for every combination of
            # target_dims' choices that occurs anywhere in the multiverse:
            # E[Y | X_target = combo], unconditioned on anything else.
            # This also defines the full comparable-set space -- combinations
            # of target_dims that never occur anywhere are not considered,
            # since there is no data to ground them in.
            grouped_means = multiverse_results[perf_col].groupby(
                [multiverse_results[col] for col in target_dim_cols]
            ).mean()
            # normalize keys to tuples explicitly: groupby collapses a
            # single-column key to a bare scalar Index rather than a
            # 1-element-tuple MultiIndex, which would otherwise silently
            # mismatch against the tuple keys built from itertuples() below
            if len(target_dim_cols) == 1:
                imputed_means = {(k,): v for k, v in grouped_means.items()}
            else:
                imputed_means = grouped_means.to_dict()
            full_combo_space = list(imputed_means.keys())

            phi_values = []
            for context, context_rows in multiverse_results.groupby(
                [multiverse_results[col] for col in other_dim_cols]
            ):
                real_by_combo = dict(zip(
                    context_rows[target_dim_cols].itertuples(index=False, name=None),
                    context_rows[perf_col],
                ))
                comparable_set = [
                    real_by_combo[combo] if combo in real_by_combo
                    else imputed_means[combo]
                    for combo in full_combo_space
                ]
                phi_values.append(np.var(comparable_set, ddof=0))

            # equal weight per background context (default aggregation)
            catchy_name[target_dims] = float(np.mean(phi_values))

    return catchy_name
