"""
This file is copied from fairness_multiverse/analysis.py at https://github.com/reliable-ai/fairml-multiverse
"""

from typing import Optional
import pandas as pd
import numpy as np

from pathlib import Path
from ConfigSpace import ConfigurationSpace, CategoricalHyperparameter
from sklearn.preprocessing import OrdinalEncoder

# fanova uses np.float, removed in NumPy 2.0
if not hasattr(np, 'float'):
    np.float = np.float64
from fanova import fANOVA


class MultiverseFanova:
    def __init__(self, features: pd.DataFrame, outcome: pd.Series, **fanova_kwargs) -> None:
        """
        Initializes a new MultiverseFanova instance.

        MiltiverseFanova is a helper class to perform a fANOVA analysis on
        data from a multiverse analysis.

        Args:
        - features: A pandas DataFrame containing the features / decisions to
            be used in the fANOVA analysis.
        - outcome: A pandas Series containing the outcome variable to be
            used in the fANOVA analysis.
        """
        self.fanova_features = self.process_features(features)
        self.fanova_outcome = outcome
        self.fanova_kwargs = fanova_kwargs
        self.configuration_space = self.generate_configuration_space()
        self.fanova = self.init_fanova()

    def process_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocesses a set of features for a fANOVA analysis.

        Args:
        - features: A pandas DataFrame containing the features to be encoded.

        Returns:
        - A pandas DataFrame containing the encoded features.
        """
        # float conversionsilences warning since fanova expects float values
        # int conversion needed first since its categorical
        encoded = OrdinalEncoder().fit(features).transform(features).astype(int).astype(float)
        return pd.DataFrame(encoded, columns=features.columns)

    def generate_configuration_space(self) -> ConfigurationSpace:
        """
        Generates a ConfigurationSpace object based on the instance features.

        Returns:
        - A ConfigurationSpace object.
        """
        cs = ConfigurationSpace()
        for colname in self.fanova_features.columns:
            col = self.fanova_features[colname]
            cs.add(
                CategoricalHyperparameter(name=colname, choices=list(col.unique()))
            )
        return cs

    def init_fanova(self):
        """
        Initializes a fanova.fANOVA object.

        This will not yet run the analysis to compute importance measures.

        Returns:
        - An fANOVA object.
        """
        return fANOVA(
            self.fanova_features,
            self.fanova_outcome,
            config_space=self.configuration_space,
            **self.fanova_kwargs
        )

    def quantify_importance(self, save_to: Optional[Path] = None):
        """
        Quantifies the joint importance of features in the MultiverseFanova.

        Args:
        - save_to: A Path specifying where to save the results. (optional)

        Returns:
        - A pandas DataFrame containing the importance of each feature.
        """
        param_list = list(self.configuration_space.keys())
        fanova_all_effects = self.fanova.quantify_importance(param_list)
        df_importance_interactions = (
            pd.DataFrame(fanova_all_effects).transpose().reset_index(drop=False)
        )
        df_importance_interactions.sort_values(
            by="individual importance", ascending=False, inplace=True
        )

        if save_to is not None:
            df_importance_interactions.to_csv(save_to)

        return df_importance_interactions

    def quantify_individual_importance(self, save_to: Optional[Path] = None):
        """
        Quantifies the individual importance of each feature in the MultiverseFanova.

        Args:
        - save_to: A Path specifying where to save the results. (optional)

        Returns:
        - A pandas DataFrame containing the individual importance of each feature.
        """
        param_list = list(self.configuration_space.keys())

        main_effects = {}
        for param in param_list:
            param_fanova = (param,)
            main_effects[param] = self.fanova.quantify_importance(param_fanova)[
                param_fanova
            ]

        df_main_effects = pd.DataFrame(main_effects).transpose()
        df_main_effects.sort_values(by="individual importance", ascending=False, inplace=True)

        if save_to is not None:
            df_main_effects.to_csv(save_to)

        return df_main_effects