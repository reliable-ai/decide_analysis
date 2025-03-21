********************************************************************************
*	IDENTIFICATION OF (LONG-TERM) UNEMPLOYMENT EPISODES
*
*	Author: Hannah Mautner
*	Goals
*		- Identify population of job seekers/ unemployed
*		- Divide into long-term and short term job seeking/ unemployment episodes

*	Approach:
*		- 1 Identify spells that indicate seeking while seeking being unemployment
*				- also, identify spells that do not pause unemployment episodes:
*					- illness up to 6 weeks
*					- certain ALMP measures
*		- 2 Identify seperate unemployment episodes
*				- 2.1 Find begin of unemployment (ASU spell)
*				- 2.2 Find end of unemployment (ASU spell)
*		- 3 Calculate the length of unemployment 
*		- 4 Identify population of short-term and long-term unemployed/ job seekers in 2010-2013
*				- 4.1 Find exits into employment 
*				- 4.2 Find LTUE and STUE population for supervised learning models
*					- Note: Unemployment episodes that start in 2014 cannot be considered
*		- 5 Data preparations for further steps
*
*	Note: 
*
*
*
********************************************************************************
********************************************************************************
* 	YEAR OF OBSERVATION AND AGE           
********************************************************************************


gen int year = year(begepi)		// year
gen int age = year - gebjahr 	// age

********************************************************************************
* 	Keep only (X)ASU and MTH spells for identification of unemployment
********************************************************************************

preserve
	keep if inlist(quelle_gr, 4, 5)
********************************************************************************
* 	1 Identify spells when seeking for employment while being unemployed 
*	Approach: 
*		- keep only (X)ASU and MTH spells
*		- Identify job seeking while UE, illness up to 6 weeks, ALMPs and other breaks
********************************************************************************
	* Identify job seeking while being unemployed (seeking1)
	gen seeking1 = inlist(quelle_gr, 5) &  inlist(erwstat, 21)
* Identify paricipation in qualified measures 
	gen quelle2=-quelle_gr // Reorder quelle_gr for indexing of measures (MTH: quelle_gr==32)
	bysort persnr begepi(quelle2): gen nrM = _n if quelle_gr==4 & inlist(erwstat, 41)  
	gen almp =. 
	replace almp=1 if nrM >0 & !missing(nrM)
	replace almp= almp[_n-1] if persnr == persnr[_n-1] & begepi == begepi[_n-1] & missing(almp)
	
	* Drop auxiliary variables, establish standard sorting
	drop quelle2 nrM almp
	sort persnr spell
********************************************************************************
* 	Keep only (X)ASU spells that are relavant for determining LTE
********************************************************************************
	keep if seeking1==1
	**** Identify breaks 
	
	* Calculate days in between ASU job seeking while unemployed spells
	bys persnr seeking1(begepi): gen t_since_seeking = begepi - endepi[_n-1] if seeking1==1
	* Calculate time since last ASU spell
	sort persnr spell
	bysort persnr: gen t_since_asu = begepi - endepi[_n-1]
	*** Tag spells that are part of a continuous job seeking episode but not the start spell	
	sort persnr spell
	bysort persnr: gen continuous= 1 if t_since_asu <=42 
********************************************************************************
* 	2 Identify seperate unemployment episodes: Find begin and end of unemployment
********************************************************************************
********************************************************************************
* 	2.1 Begin of unemployment
*	Approach:
*		- every spell that is not a spell that follows another ASU spell is defined as anew start
********************************************************************************
	sort persnr spell // wichtig!
	gen beg_ue =1 if continuous !=1 
	sort persnr seeking1 (spell)
	gen beg_ue_date = begepi if beg_ue ==1
	format beg_ue_date %tdDD_Mon_CCYY

	* Copy date to all the subsequent ASU spell that belong the the same episode of unemployment/ job seeking
	sort persnr spell
	replace beg_ue_date =beg_ue_date[_n-1] if missing(beg_ue_date) & continuous ==1 & persnr==persnr[_n-1]

********************************************************************************
* 2.2 End of unemployment
*	Approach:
*	- every spell that is previous to a new start is defined as end spell
********************************************************************************

	sort persnr spell // wichtig!
	gen end_ue = 1 if beg_ue[_n+1] ==1 & persnr==persnr[_n+1] // End is defined as the spell previous an beginning

	* Correction for last end of unemployment
	by persnr: gen nrASU = _n
	by persnr: gen NrASU = _N
	replace end_ue= 1 if nrASU == NrASU
	
	* Date of end of unemployment
	gen end_ue_date_help = endepi if end_ue == 1
	bysort persnr beg_ue_date: egen end_ue_date = max(end_ue_date_help)
	format end_ue_date %tdDD_Mon_CCYY
	
	
	* Drop auxiliary variables, establish standard sorting 
	drop nrASU NrASU end_ue_date_help 
	sort persnr spell
	
********************************************************************************
* 	3 Calculate the length/ duration of unemployment using ASU spells
********************************************************************************

	* Duration: Calculate for last ASU spell of continuous unemployment & job seeking episode (end_ue ==1)
	gen duration_help =  endepi - beg_ue_date if end_ue == 1

	* Copy UE duration to all spells of an UE episode
	bysort persnr beg_ue_date: egen ue_duration = max(duration_help)  
	
	* Drop auxiliary variables, establish standard sorting 
	drop duration_help 
	sort persnr spell
	
	
	* Begin of unemployment in years 2010-2013
	tab beg_ue
	bysort persnr beg_ue: gen id = _n if beg_ue==1
	tab year beg_ue if inlist(year, 2010, 2011, 2012, 2013) & !missing(id), m // 14.802 // 2114 people get unemployed

	keep persnr spell seeking1 t_since_seeking t_since_asu beg_ue end_ue beg_ue_date end_ue_date ue_duration
	
********************************************************************************
* 	Save as temp file and merge with previously preserved data
********************************************************************************	
	
	tempfile ue_population
	save `ue_population'
restore 	

merge 1:1 persnr spell using `ue_population'
drop _merge
	

********************************************************************************
* 4 Identify STUE and LTUE populations
********************************************************************************

/* 	Entire job seeking population splits into
	- those who exit to employment, 
	- those you exit due to other reasons in the first years
	- those still in register after one year

	Goal: Identify population of job seekers during 2010-2013
	- people that get unemployed during 2010-2013
	- specify whether short-term unemployment or long-term unemployment
	
*/


********************************************************************************
*  4.1 Find exits into employment  
********************************************************************************

/* Issue:
- people may exit job seeking status due to different reasons
- exit into employment vs. exit due to motherhood, illness etc. 

*/


********************************************************************************
*** estatnach: Reason for exiting ASU register

/* Note: estatnach and grund only available for ASU, not XASU
approx. 1/4 of end spells of unemployment episodes are XASU spells



* Recode of estatnach, see FDZ Datenreport, p. 55; 
* How are missings handeled?  (.n .z =6)
recode estatnach (1000/1999 =1 ) (2000/2999 = 2) (3000/3999 = 3) (4000/4999 = 4) (5000/5999 = 5) (6000/6999 = 6) , gen(estatnach_recode)


label define exit 1"Exit into measure" 2"Exit into employment" 3"Exit into vocational training" 4"Exit into self-employment" 5"Exit into ban" 6"Other exit"
label values estatnach_recode exit
tab estatnach_recode if end_ue==1, m

* Tag exit to employment; how do I treat self-employment?
gen exit_emp = 1 if end_ue==1 & estatnach_recode ==2



/* Note: Approx. 1/6 of cases have missing
- For XASU source data, there is no information for estatnach and grund

Approach: 
-> first look into variable "grund"
-> then look into BeH data
*/

********************************************************************************
*** grund: Reason for leaving ASU register

gen estatnach_imput =.
replace estatnach_imput = 2 if inlist(grund, 5030, 5037, 5038, 5060, 5063/5066, 5080, 5082, 5098, 6001/6005, 6007) &end_ue==1
replace estatnach_imput = 4 if inlist(grund, 5046, 6006) &end_ue==1

* 
replace exit_emp= 2 if estatnach_imput ==2 & end_ue==1 & missing(exit_emp) // in sample, approx. 100K changes


tab quelle_gr exit_emp if end_ue==1,m

/*  1: source is estatnach
	2: soruce is grund
	Note: exit_emp: all XASU spells that tag end of unemployment episode are not set to missing 
*/
*/
********************************************************************************
*** BeH: Determine time till reemployment (only standard social-security employment is considered)

/* Work around for XASU spells ans ASU spells for which no info is avialabe

	Note: No possibility to get information on self-employment for XASU spells !!!
*/

preserve
	keep if inlist(quelle_gr,1,5) 				// Keep only BeH and (X)ASU spells
	drop if inlist(quelle_gr,5) & end_ue !=1 	// Drop all (X)ASU spells that do not mark end of unemployment
	
	recode quelle_gr(5=1) (1=2), gen(quelle_gr_help) 

	bysort persnr begepi quelle_gr_help (end_ue): gen nrASU=_n if quelle_gr_help==1
	tab nrASU
	drop if nrASU >1 & !missing(nrASU) 			// drop duplicates
		
	*** Date of next employment (standard social security employment)
	gen next_employed_date =begepi if quelle_gr==1 & inlist(erwstat,1) // only consider standard social security employment
	format next_employed_date %tdDD_Mon_CCYY
	sort persnr spell (quelle_gr)
	by persnr: replace next_employed_date = next_employed_date[_n+1] if missing(next_employed_date) & next_employed_date[_n+1] != begepi

	gen t_till_emp = next_employed_date - endepi -1 if end_ue==1 // time till next employment after end of job seeking episode
	
	keep if end_ue==1
	keep persnr spell next_employed_date t_till_emp

	tempfile t_till
	save `t_till'
restore

merge 1:1 persnr spell using `t_till'
drop _merge

foreach v of varlist next_employed_date t_till_emp{
rename `v' `v'_help
}

* Copy next_employed_date t_till_emp to all spells of same job seeking episode
bysort persn beg_ue_date: egen next_employed_date = max(next_employed_date_help)
format next_employed_date %tdDD_Mon_CCYY
bysort persn beg_ue_date: egen  t_till_emp = max(t_till_emp_help)
sort persnr spell

*** Generate auxiliarx variable to determine exit into employment based on BeH spells
gen exit_emp_help=1 if end_ue==1 & t_till_emp <=61


*** Compare aux. variable with exit_emp
tab exit_emp exit_emp_help, m

/* for approx. 1/5 of those folks that exited into employment acc. to ASU, there is no standard social sec. employment spell
-> marginal employment?
*/


*** Impute information to variable exit_emp
replace exit_emp=3 if exit_emp_help==1 & end_ue==1 & missing(exit_emp)

*hist t_till_emp if end_ue==1 & t_till_emp<=100 & exit_emp != 1  & exit_emp != 2 & exit_emp != 3, freq
*sum t_till_emp if end_ue==1 & t_till_emp<=100 & exit_emp != 1  & exit_emp != 2

tab exit_emp if inlist(year, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017)

* Drop auxiliary variables
drop exit_emp_help t_till_emp_help next_employed_date_help 

********************************************************************************
*  4.2 Flag STUE and LTUE populations
********************************************************************************

*** Flag ASU spells that belong to episode of long-term unemployment
gen ltue = ue_duration >=365 & !missing(ue_duration) 

*** Flag start of long-term unemployment
gen beg_ltue = 1 if beg_ue==1 & ltue==1


*******************************************************************************
* Prepare data for further steps                   
*******************************************************************************

*** Copy start and end  date of unemployment to all parallel spells 
recode quelle_gr (5=0), gen (quelle_gr_help)
bysort persnr begepi (quelle_gr_help): replace beg_ue_date =beg_ue_date[_n-1] if missing(beg_ue_date) 
bysort persnr begepi (quelle_gr_help): replace end_ue_date =end_ue_date[_n-1] if missing(end_ue_date) 

*** Same for duration
bysort persnr begepi (quelle_gr_help): replace ue_duration =ue_duration[_n-1] if missing(ue_duration) 

*** Standard sorting
sort persnr spell

*******************************************************************************
*** Label variables

* EN
label language en
label variable year 				"Year of episode"
label variable age 					"Age"
label variable beg_ue  				"Begin of unemployment (ASU spell)"
label variable beg_ue_date 			"Start date of UE episode"
label variable end_ue 				"End of unemployment (ASU spell)"
label variable seeking1 			"Seeking for employment while unemployed spell"
*label variable break_ill			"Spell indicating illness"
* label variable break_almp			"Spell indicating ALMP"
* label variable almp 				"Spell for ALMP measure (§45 SGBIII)"
label variable t_since_seeking 		"Time since last UE & job seeking episode"
label variable t_since_asu			"Time since last ASU spell (that does not pause UE)"
label variable ue_duration			"Duration of UE/AS-Episode"
label variable ltue					"Long-term unemployment (bin. var)"


* DE
label language de
label variable year 				"Jahr (Episode)"
label variable age 					"Alter"
label variable beg_ue  				"Start Arbeitslosigkeit(ASU spell)"
label variable beg_ue_date 			"Start date of UE episode"
label variable end_ue 				"Ende Arbeitslosigkeit(ASU spell)"
label variable seeking1 			"Arbeitssuchend-Spell (enge Def.)"
*label variable break_ill			"Ktrankheits-spell"
*label variable break_almp			"ALMP-spell"
*label variable almp				"ALMP-Maßnahme-Spell (§45 SGBIII)"	
label variable t_since_seeking 		"Tage seit letzter UE/AS-Episode"
label variable t_since_asu			"Tage seit letztem ASU spell"
label variable ue_duration			"Dauer der UE/AS-Episode"
label variable ltue					"Langzeitsarbeitslosigkeit (bin. Var)"


*******************************************************************************
*** Compress and save data


compress
save  "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/SIAB_sample_UEidenfidied.dta", replace

cap log close 
exit
