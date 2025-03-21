********************************************************************************
*	4 V2. Reshape data looking at all entries into unemployment per individual
*
*	Author: Hannah Mautner
*	Goal: 	Do reshaping for all entries into unemployment, no matter of duplicate persnr
*
********************************************************************************


********************************************************************************
*
* 	Approach: 
*	- Index entries into UE for each person

********************************************************************************


*use ${data}_beforereshaping_20180614.dta, clear

********************************************************************************
* 	Index entries into unemployment for each individual

preserve

	keep if beg_ue ==1 // keep only entries into unemployment
	keep if inlist(year, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017) // keep only 2010-2013

	by persnr: gen nrEntry = _n // generate index for unemployment entries

	keep persnr spell nrEntry
	tempfile  entry
	save `entry'
restore

merge 1:1 persnr spell using `entry'
drop _merge

