"""
SIAB Preparation

Deflate wages using Consumer Price Index
Based on Statistisches Bundesamt (2016) data

Author(s): Wolfgang Dauth, Johann Eppelsheimer
Converted to Python
"""

import pandas as pd
import numpy as np

def deflate_wages(df):
    """Deflate wages using CPI data with 2015 as base year."""

    # Create CPI dictionary (year: index value)
    cpi_values = {
        # West Germany 1975-1991 (adjusted to 2015 base)
        1975: 54.5 * (65.5/89.0), 1976: 56.8 * (65.5/89.0),
        1977: 58.9 * (65.5/89.0), 1978: 60.5 * (65.5/89.0),
        1979: 63.0 * (65.5/89.0), 1980: 66.4 * (65.5/89.0),
        1981: 70.6 * (65.5/89.0), 1982: 74.3 * (65.5/89.0),
        1983: 76.7 * (65.5/89.0), 1984: 78.6 * (65.5/89.0),
        1985: 80.2 * (65.5/89.0), 1986: 80.1 * (65.5/89.0),
        1987: 80.3 * (65.5/89.0), 1988: 81.3 * (65.5/89.0),
        1989: 83.6 * (65.5/89.0), 1990: 85.8 * (65.5/89.0),
        1991: 89.0 * (65.5/89.0),

        # United Germany 1992-2017
        1992: 68.8, 1993: 71.9, 1994: 73.8, 1995: 75.1,
        1996: 76.1, 1997: 77.6, 1998: 78.3, 1999: 78.8,
        2000: 79.9, 2001: 81.5, 2002: 82.6, 2003: 83.5,
        2004: 84.9, 2005: 86.2, 2006: 87.6, 2007: 89.6,
        2008: 91.9, 2009: 92.2, 2010: 93.2, 2011: 95.2,
        2012: 97.1, 2013: 98.5, 2014: 99.5, 2015: 100.0,
        2016: 100.5, 2017: 102.0
    }

    # Create CPI series
    df['cpi'] = df['year'].map(cpi_values)

    # Deflate wages (base year 2015)
    df['wage_defl'] = 100 * df['tentgelt'] / df['cpi']

    # Optional: Deflate other monetary values if needed
    # df['limit_marginal_defl'] = 100 * df['limit_marginal'] / df['cpi']
    # df['limit_assess_defl'] = 100 * df['limit_assess'] / df['cpi']

    # Print summary statistics
    print("\nWage Deflation Summary:")
    print(df.groupby('year')[['tentgelt', 'wage_defl']].describe())

    return df

def process_wages(df):
    """Deflate wages using CPI data with 2015 as base year.

    Args:
        df (pd.DataFrame): Input SIAB data frame

    Returns:
        pd.DataFrame: Data frame with deflated wages
    """
    return deflate_wages(df)

if __name__ == "__main__":
    print("This script should be run as part of the master SIAB processing pipeline")
