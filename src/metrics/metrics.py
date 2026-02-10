"""
This file defines intra-bucket (between universe) and inter-bucket (within
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
                           performance_metric: str) -> pd.DataFrame:
    """
    Calculate the within-bucket variation for a given performance metric. This
    measures how much the performance metric varies within each bucket (i.e., 
    within each combination of judgment calls).

    Args:
        multiverse_results (pd.DataFrame): A DataFrame containing the results
            of the multiverse analysis.
        performance_metric (str): The name of the performance metric to analyze.
    Returns:
        pd.DataFrame: A DataFrame containing the within-bucket variation for the
            specified performance metric.
    """
        
    # because the judgment calls are organized chronologically, we can calculate
    # the within-bucket variation by going column-by-column
    # and calculating the variance of the performance metric across the
    # different forks of the multiverse.
    
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
        range_of_decreases_in_variance_by_depth[depth] = \
            np.max(decreases_in_variance) - np.min(decreases_in_variance)
    
    return range_of_decreases_in_variance_by_depth