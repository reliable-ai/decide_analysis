*cap log close
*log using ${folderLog}\08_wages_deflation.log, replace



/*
	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
	
	SIAB Preparation
	
	Deflate wages, marginal part-time income threshold and contribution assessment ceiling
	
	Consumer Price Index:
		Statistisches Bundesamt (2016)
		Preise - Verbraucherpreisindizes fuer Deutschland (Lange Reihe ab 1948)
		https://www.destatis.de/DE/Publikationen/Thematisch/Preise/Verbraucherpreise/VerbraucherpreisindexLangeReihen.html

		
	Generates the variables:
		- wage_defl: daily wage, deflated
		- limit_marginal_defl: marginal part-time income threshold, deflated
		- limit_assess_defl: contribution assessment ceiling, deflated
	
	
	Author(s): Wolfgang Dauth, Johann Eppelsheimer
	
	Version: 1.0
	Last Update: 2018-04-03
	Created: 2018-04-03
	
	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
		
*/



********************************************************************************
* Consumer Price Index West Germany 1975 - 1991 (base year 1995)
********************************************************************************
gen cpi=.
label variable cpi "Consumer Price Index"

replace cpi = 54.5 if year == 1975
replace cpi = 56.8 if year == 1976
replace cpi = 58.9 if year == 1977
replace cpi = 60.5 if year == 1978
replace cpi = 63.0 if year == 1979
replace cpi = 66.4 if year == 1980
replace cpi = 70.6 if year == 1981
replace cpi = 74.3 if year == 1982
replace cpi = 76.7 if year == 1983
replace cpi = 78.6 if year == 1984
replace cpi = 80.2 if year == 1985
replace cpi = 80.1 if year == 1986
replace cpi = 80.3 if year == 1987
replace cpi = 81.3 if year == 1988
replace cpi = 83.6 if year == 1989
replace cpi = 85.8 if year == 1990
replace cpi = 89.0 if year == 1991

/*
********************************************************************************
* Set 2010 as base year for the period 1975 - 1991
********************************************************************************
replace cpi = (cpi/89.0)*70.2		// see Statistisches Bundesamt (2016)


********************************************************************************
* Consumer Price Index Germany (West and East, after 1991)
********************************************************************************
replace cpi =  73.8 if year == 1992
replace cpi =  77.1 if year == 1993
replace cpi =  79.1 if year == 1994
replace cpi =  80.5 if year == 1995
replace cpi =  81.6 if year == 1996
replace cpi =  83.2 if year == 1997
replace cpi =  84.0 if year == 1998
replace cpi =  84.5 if year == 1999
replace cpi =  85.7 if year == 2000
replace cpi =  87.4 if year == 2001
replace cpi =  88.6 if year == 2002
replace cpi =  89.6 if year == 2003
replace cpi =  91.0 if year == 2004
replace cpi =  92.5 if year == 2005
replace cpi =  93.9 if year == 2006
replace cpi =  96.1 if year == 2007
replace cpi =  98.6 if year == 2008
replace cpi =  98.9 if year == 2009
replace cpi = 100.0	if year == 2010
replace cpi = 102.1 if year == 2011
replace cpi = 104.1 if year == 2012
replace cpi = 105.7 if year == 2013
replace cpi = 106.6 if year == 2014

*/

********************************************************************************
* Set 2015 as base year for the period 1975 - 1991
********************************************************************************
replace cpi = (cpi/89.0)*65.5		// see Statistisches Bundesamt (2016)


********************************************************************************
* Consumer Price Index Germany (West and East, after 1991)
********************************************************************************
replace cpi =  68.8 if year == 1992
replace cpi =  71.9 if year == 1993
replace cpi =  73.8 if year == 1994
replace cpi =  75.1 if year == 1995
replace cpi =  76.1 if year == 1996
replace cpi =  77.6 if year == 1997
replace cpi =  78.3 if year == 1998
replace cpi =  78.8 if year == 1999
replace cpi =  79.9 if year == 2000
replace cpi =  81.5 if year == 2001
replace cpi =  82.6 if year == 2002
replace cpi =  83.5 if year == 2003
replace cpi =  84.9 if year == 2004
replace cpi =  86.2 if year == 2005
replace cpi =  87.6 if year == 2006
replace cpi =  89.6 if year == 2007
replace cpi =  91.9 if year == 2008
replace cpi =  92.2 if year == 2009
replace cpi = 93.2	if year == 2010
replace cpi = 95.2 if year == 2011
replace cpi = 97.1 if year == 2012
replace cpi = 98.5 if year == 2013
replace cpi = 99.5 if year == 2014
replace cpi = 100.0 if year == 2015
replace cpi = 100.5 if year == 2016
replace cpi = 102.0 if year == 2017



*********************************************************************************************************
* Deflate wages, marginal part-time income threshold and contribution assessment ceiling (base year 2010)
*********************************************************************************************************
gen wage_defl           = 100 * tentgelt / cpi
*gen limit_marginal_defl = 100 * limit_marginal / cpi
*gen limit_assess_defl   = 100 * limit_assess / cpi

label language en
label variable wage_defl "Daily wage, deflated (2010)"
*label variable limit_marginal_defl "Marginal part-time income threshold, deflated (2010)"
*label variable limit_assess_defl "Contribution assessment ceiling, deflated (2010)"




*log close
