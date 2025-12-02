"""
Fair Algorithmic Profiling
Setup
Christoph Kern
"""

# Setup

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split

# 01 Data Checks

siab = pd.read_csv("../data/siab.csv")

siab.describe(include = 'all')
siab.isna().sum()

grouped = siab.groupby('year')
siab_s = grouped.apply(lambda x: x.sample(n = 5000, random_state = 42)) # Sample 5000 obs from each year

siab_s = siab_s.reset_index(drop = True) # Ungroup

siab_s.groupby('year').describe(include = 'all')

# 02 Data Split

# Train with 2010 - 2015 | 2015
# Test with 2016

siab_train = siab_s[siab_s.year <= 2015]
siab_train_s = siab_s[siab_s.year == 2015]
siab_test = siab[siab.year == 2016]

X_train_f = siab_train.iloc[:,4:164]
X_train_fs = siab_train_s.iloc[:,4:164]
X_train_s = X_train_f.drop(columns = ['frau1', 'maxdeutsch1', 'maxdeutsch.Missing.'])
X_train_ss = X_train_fs.drop(columns = ['frau1', 'maxdeutsch1', 'maxdeutsch.Missing.'])
y_train = siab_train.iloc[:, [3]]
y_train_s = siab_train_s.iloc[:, [3]]

X_test_f = siab_test.iloc[:,4:164]
X_test_s = X_test_f.drop(columns = ['frau1', 'maxdeutsch1', 'maxdeutsch.Missing.'])
y_test = siab_test.iloc[:, [3]]

# Train with 2010 - 2014 | 2014
# Test with 2015

siab_train2 = siab_s[siab_s.year <= 2014]
siab_train2_s = siab_s[siab_s.year == 2014]
siab_test2 = siab[siab.year == 2015]

X_train2_f = siab_train2.iloc[:,4:164]
X_train2_fs = siab_train2_s.iloc[:,4:164]
X_train2_s = X_train2_f.drop(columns = ['frau1', 'maxdeutsch1', 'maxdeutsch.Missing.'])
X_train2_ss = X_train2_fs.drop(columns = ['frau1', 'maxdeutsch1', 'maxdeutsch.Missing.'])
y_train2 = siab_train2.iloc[:, [3]]
y_train2_s = siab_train2_s.iloc[:, [3]]

X_test2_f = siab_test2.iloc[:,4:164]
X_test2_s = X_test2_f.drop(columns = ['frau1', 'maxdeutsch1', 'maxdeutsch.Missing.'])
y_test2 = siab_test2.iloc[:, [3]]

# Train with 2010 - 2013 | 2013
# Test with 2014

siab_train3 = siab_s[siab_s.year <= 2013]
siab_train3_s = siab_s[siab_s.year == 2013]
siab_test3 = siab[siab.year == 2014]

X_train3_f = siab_train3.iloc[:,4:164]
X_train3_fs = siab_train3_s.iloc[:,4:164]
X_train3_s = X_train3_f.drop(columns = ['frau1', 'maxdeutsch1', 'maxdeutsch.Missing.'])
X_train3_ss = X_train3_fs.drop(columns = ['frau1', 'maxdeutsch1', 'maxdeutsch.Missing.'])
y_train3 = siab_train3.iloc[:, [3]]
y_train3_s = siab_train3_s.iloc[:, [3]]

X_test3_f = siab_test3.iloc[:,4:164]
X_test3_s = X_test3_f.drop(columns = ['frau1', 'maxdeutsch1', 'maxdeutsch.Missing.'])
y_test3 = siab_test3.iloc[:, [3]]

# 03 Descriptive Stats

siab_t = siab_train.copy(deep = True)
siab_t = siab_t.append(siab_test)

siab_t['nongerman'] = np.where(siab_t['maxdeutsch1'] == 0, 1, 0)
siab_t.loc[siab_t['maxdeutsch.Missing.'] == 1, 'nongerman'] = np.nan
siab_t['nongerman_male'] = np.where((siab_t['nongerman'] == 1) & (siab_t['frau1'] == 0), 1, 0)
siab_t['nongerman_female'] = np.where((siab_t['nongerman'] == 1) & (siab_t['frau1'] == 1), 1, 0)

desc1 = siab_t[['year', 'ltue']].groupby('year').mean()

desc1.to_latex('./output/desc1.tex', float_format = "%.3f") # Mean LTUE over time

desc2a = siab_t[['year', 'frau1', 'nongerman', 'nongerman_male', 'nongerman_female']].groupby(['year']).agg(['sum', 'count'])
desc2b = siab_t[['year', 'frau1', 'nongerman', 'nongerman_male', 'nongerman_female']].groupby(['year']).mean()
desc2c = siab_t[['year', 'ltue', 'frau1', 'nongerman', 'nongerman_male', 'nongerman_female']].groupby(['year', 'ltue']).agg(['mean', 'count'])

desc2a.to_latex('./output/desc2a.tex', float_format = "%.3f") # Number of cases over time
desc2b.to_latex('./output/desc2b.tex', float_format = "%.3f") # Socio-demo over time
desc2c.to_latex('./output/desc2c.tex', float_format = "%.3f") # Socio-demo by LTUE over time

siab_t[['year', 'nongerman', 'ltue', 'frau1', 'age', 'maxschule9']].groupby(['year', 'nongerman']).agg(['mean', 'count']) # Socio-demo and LTU by nationality over time

# Save 

X_train_f.to_csv('./output/X_train_f.csv', index = False)
X_train_fs.to_csv('./output/X_train_fs.csv', index = False)
X_train_s.to_csv('./output/X_train_s.csv', index = False)
X_train_ss.to_csv('./output/X_train_ss.csv', index = False)
y_train.to_csv('./output/y_train.csv', index = False)
y_train_s.to_csv('./output/y_train_s.csv', index = False)

X_test_f.to_csv('./output/X_test_f.csv', index = False)
X_test_s.to_csv('./output/X_test_s.csv', index = False)
y_test.to_csv('./output/y_test.csv', index = False)

X_train2_f.to_csv('./output/X_train2_f.csv', index = False)
X_train2_fs.to_csv('./output/X_train2_fs.csv', index = False)
X_train2_s.to_csv('./output/X_train2_s.csv', index = False)
X_train2_ss.to_csv('./output/X_train2_ss.csv', index = False)
y_train2.to_csv('./output/y_train2.csv', index = False)
y_train2_s.to_csv('./output/y_train2_s.csv', index = False)

X_test2_f.to_csv('./output/X_test2_f.csv', index = False)
X_test2_s.to_csv('./output/X_test2_s.csv', index = False)
y_test2.to_csv('./output/y_test2.csv', index = False)

X_train3_f.to_csv('./output/X_train3_f.csv', index = False)
X_train3_fs.to_csv('./output/X_train3_fs.csv', index = False)
X_train3_s.to_csv('./output/X_train3_s.csv', index = False)
X_train3_ss.to_csv('./output/X_train3_ss.csv', index = False)
y_train3.to_csv('./output/y_train3.csv', index = False)
y_train3_s.to_csv('./output/y_train3_s.csv', index = False)

X_test3_f.to_csv('./output/X_test3_f.csv', index = False)
X_test3_s.to_csv('./output/X_test3_s.csv', index = False)
y_test3.to_csv('./output/y_test3.csv', index = False)
