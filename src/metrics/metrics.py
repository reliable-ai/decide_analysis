"""
This file defines inter-bucket (between universe) and intra-bucket (within
universe) metrics for assessing the downstream impact of judgment calls in
the multiverse. These metrics can be used to determine which judgment calls have
the largest impact on downstream results and to what extent the results are
robust to different judgment calls.
"""

# imports
import pandas as pd
import numpy as np
from copy import deepcopy
from collections import defaultdict

def organize_multiverse_results(multiverse_results: pd.DataFrame,
                                dimension_order: list,
                                performance_metrics: list) -> pd.DataFrame:
    """
    The multiverse results come as a DataFrame with columns for each judgment
    call and performance metric of interest. Here, we properly order the
    judgment calls & get the subset of the results that apply for our analysis.

    Args:
        multiverse_results (pd.DataFrame): A DataFrame containing the results of
            the multiverse analysis.
        dimension_order (list): A list specifying the order of dimensions (judgment calls).
        performance_metrics (list): A list of performance metrics to consider.
    """
    
    # create copy of the multiverse results to avoid modifying the original
    multiverse_results = deepcopy(multiverse_results)
    
    # get the subset of the results that apply for our analysis
    multiverse_results = multiverse_results[dimension_order + performance_metrics]
    
    # give each column a certain level using multilevel indexing to denote
    # if it is a dimension (judgment call) or a performance metric
    multiverse_results.columns = pd.MultiIndex.from_tuples(
        [(col, "dimension") if col in dimension_order else (col, "performance_metric")
         for col in multiverse_results.columns]
    )

    return multiverse_results

def path_within_bucket_variation(multiverse_results: pd.DataFrame,
                                decision_path: dict,
                                performance_metric: str) -> pd.DataFrame:
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
        multiverse_results = \
            multiverse_results[multiverse_results[(dimension,
                                                   "dimension")] == choice]
            
    # calculate the variance of the performance metric across the remaining
    # universes (i.e., different combinations of the remaining judgment calls)
    variance = multiverse_results[(performance_metric, "performance_metric")].var()
    
    return variance

def within_bucket_variation(multiverse_results: pd.MultiIndex,
                           performance_metric: str) -> dict:
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
            judgment call for the specified performance metric.
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
    decision_paths = [(0, {})] # list of tuples of the form (depth, path) where depth is an int and path is a dict of the form {dimension: choice}
    # loop through number of judgment calls, which is number of columns that are dimensions in the multiindex
    for depth in range(1, multiverse_results.columns.get_level_values(1).tolist().count("dimension")):
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
    # take mean(path_within_bucket_variation(path)) for each path at the depth correspnding to that decision.
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
            paths_with_var[path_tuple] = \
                path_within_bucket_variation(multiverse_results,
                                            path,
                                            performance_metric)
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
    range_of_decreases_in_variance_by_depth = {}
    for depth, paths_with_var in var_by_depth.items():
        decreases_in_variance = []
        for path_tuple, var in paths_with_var.items():
            # get the paths that are one decision away from this path (i.e.,
            # the paths that are the same as this path except for one additional
            # judgment call)
            paths_one_decision_away = [p for p in \
                var_by_depth.get(depth + 1, {}).keys() if \
                    p[:depth] == path_tuple]
            # print(f"At depth {depth}, for path {path_tuple} with variance \
                # {var}, the paths one decision away are: \
                    # {paths_one_decision_away}")
            for path_one_decision_away in paths_one_decision_away:
                var_one_decision_away = \
                    var_by_depth[depth + 1][path_one_decision_away]
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
        range_of_decreases_in_variance_by_depth[depth] = \
            np.max(decreases_in_variance) - np.min(decreases_in_variance)
    
    return range_of_decreases_in_variance_by_depth

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
