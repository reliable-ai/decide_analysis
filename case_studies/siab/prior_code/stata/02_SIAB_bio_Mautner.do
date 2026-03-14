/*************************************************************************\
|    Authors:         Johanna Eberle, Alexandra Schmucker                 |
|    Date:            June 2017                                           |
|    SIAB version:    7514 v1                                             |
|    Purpose:         Generation of cross sectional data and              |
|                     biographical variables                              |
|    Do-file version: v0                                                  |
|                                                                         |
|    List of changes                                                      |
|    --------------------                                                 |
|    -                                                                    |
|                                                                         |
\*************************************************************************/

/*------------------------------------------------------------------------------------------------
  GENERATE ADDITIONAL BIOGRAPHIC VARIABLES FROM LONGITUDINAL DATA

	First day in employment (ein_erw):
		- Date of entry into first employment
		- Periods of vocational training are ignored (erwstat = 102, 121, 122, 141, 144)
		  --> Missing for persons continuously in vocational training in SIAB
		- Entry into first employment can be later than entry in first establishment or job, since the latter variables include periods of vocational training

	Number of days in employment (tage_erw):
		- Total number of days a person was employed until the end of the observation or until cutoff date 
		- Periods of vocational training are ignored (erwstat = 102,121,122,141,144)
		  --> Value 0 for persons who are in vocational training throughout
		  
	First day in establishment (ein_bet):
		- Date of entry into establishment
		- Includes periods of vocational training
		- Not affected by interruptions of employment
		  --> unique for every combination of person and establishment

	Number of days in establishment (tage_bet):
		- Number of days in establishment until the end of the observation or until cutoff date
		- Includes periods of vocational training 
		- Gaps are subtracted

	First day in job (ein_job):
		- Start date of current job
		- Periods of vocational training are considered as separate jobs (even if there is no time lag between training and job)
		- Re-employment after interruptions in the same establishment are considered as new jobs if:
		  a) the reason of notification to social security agency implies end of employment: (grund = 30, 34, 40, 49) 
			 + Time gap > 92 days
		  b) an other reason of notification exists
			 + Time gap > 366 days

	Number of days in job (tage_job):
		- Number of days in current job until the end of the observation or until cutoff date
		- see ein_job

	Number of benefit receipts (anz_lst):
		- Number of benefit receipts accoring to SGB II or SGB III
		- Sources LeH LHG
		- Time gaps are ignored if interruption < 10 days
		- Change of benefit type doesn't count as new benefit receipt

	Number of days with benefit receipt (tage_lst):
		- Duration of benefit receipts until the end of the observation or until cutoff date
		- see anz_lst
		- Gaps are subtracted

*------------------------------------------------------------------------------------------------*/


*use ${data}SIAB_sample_UEidenfidied_${date}.dta, clear

/* 
THE FOLLOWING VARIABLES ARE REQUIRED: 
persnr betnr spell quelle begorig endorig begepi endepi tentgelt teilzeit erwstat grund
*/


  
*---------------------------------------*
* OBSERVATION COUNTER                   *
*---------------------------------------*

* OBSERVATION COUNTER PER EPISODE AND SOURCE
bysort persnr begepi quelle_gr (spell): gen byte level1 = _n-1

* OBSERVATION COUNTER PER EPISODE
bysort persnr begepi (spell): gen byte level2 = _n-1

*assert !missing(level1, level2)

*---------------------------------------*
* FIRST DAY IN EMPLOYMENT  (ein_erw)    *
*---------------------------------------*
* Note: overall employment

sort persnr spell

** TAG VOCATIONAL TRAINING
* HM: Hans nutzt selbe Zuordnung (bis auf 144); allerdings keine Fälle mit erwstat==144
gen byte azubi = inlist(erwstat, 2)
label variable azubi "Vocational training"

** Tag interns and working students
* How do I treat these episodes?
* Note: Students in general are not in SIAB data
gen byte intern = inlist(erwstat, 5)
label variable intern "Interns, working students"

** Tag BeH spells indicating marginal employment
gen byte minijob = inlist(erwstat, 3)
label variable minijob "Marginal emplyoment/ minijob"

** Employed person groups  (BeH only),  5 categories
* see Hans
gen byte pg5 = 1 if inlist(erwstat, 1) // standard (d.h. sozialversicherungspflichtig)
replace pg5 =  2 if inlist(erwstat, 12) //  azubis
replace pg5 = 3 if inlist(erwstat, 14) // altersteilzeit
replace pg5 = 4 if inlist(erwstat, 13) // geringfuegig
replace pg5 = 5 if pg5 >= . // all other
tabulate pg5, missing
label define pg5 1 "standard" 2 "apprentice" ///
	3 "partt-retiree" 4 "mini-job" 5 "other"
label values pg5 pg5


*---------------------------------------*
** Tag employments
* different versions


*********
*** Version 1: Without voc. training
gen byte emp1 = 1 if azubi != 1 & quelle_gr == 1
label variable emp1 "Employment spell (w/o voc. training)"

*  Tag date of first employment
bysort persnr emp1 (begorig): gen int h1 = begorig[1] if emp1 ==1

* Assign date of first obs. to all obs.
bysort persnr: egen int ein_erw1 = max(h1)
replace ein_erw1 = .n if ein_erw1 ==.
format ein_erw1 %tdDD_Mon_CCYY
label variable ein_erw1    "First day in employment (w/o voc. training)"

*********
*** Version 2: Without voc. training, internships, working students
gen byte emp2 = 1 if azubi != 1 & intern != 1 & quelle_gr == 1
label variable emp2 "Employment spell (w/o voc. training, internships etc.)"

* Tag date of first employment
bysort persnr emp2 (begorig): gen int h2 = begorig[1] if emp2 ==1

* Assign date of first obs. to all obs.
bysort persnr: egen int ein_erw2 = max(h2)
replace ein_erw2 = .n if ein_erw2 ==.
format ein_erw2 %tdDD_Mon_CCYY


*********
*** Version 3: Without voc. training, internships etc., minijobs
gen byte emp3 = 1 if azubi != 1 & intern != 1  & minijob != 1 & quelle_gr == 1
label variable emp3 "Employment spell (w/o voc. training, internships, minijobs)"

* Tag date of first employment
bysort persnr emp3 (begorig): gen int h3 = begorig[1] if emp3 ==1

* Assign date of first obs. to all obs.
bysort persnr: egen int ein_erw3 = max(h3)
replace ein_erw3 = .n if ein_erw3 ==.
format ein_erw3 %tdDD_Mon_CCYY
label variable ein_erw3    "First day in employment (w/o voc. training, internships, minijobs)"

* Drop auxiliary variables
drop h1 h2 h3


*-----------------------------------------*
* NUMBER OF DAYS IN EMPLOYMENT (tage_erw) *
*-----------------------------------------*

/* Different versions according to entry into employment;
*/

******
*** Version 1: RUNNING TOTAL OF JOB DURATIONS (at least one job) (without voc. training)

* Counter of employemnt obs. per episode (w/o voc. training)
bysort persnr emp1 begepi (spell): gen byte nrE1 = _n if emp1 == 1

* Aux. variable for employment durations (excl. parallel episodes)
gen int d1 = endepi - begepi +1 if nrE1 == 1
bysort persnr (begepi nrE1): gen int tage_erw1 = sum(d1)

******
*** Version 2: RUNNING TOTAL OF JOB DURATIONS (at least one job) (without voc. training, internships etc) 
bysort persnr emp2 begepi (spell): gen byte nrE2 = _n if emp2 == 1 & intern !=1

gen int d2 = endepi - begepi +1 if nrE2 == 1  
bysort persnr (begepi nrE2): gen int tage_erw2 = sum(d2)

******
*** Version 3: RUNNING TOTAL OF JOB DURATIONS (at least one job) (without voc. training, internships etc) 
bysort persnr emp3 begepi (spell): gen byte nrE3 = _n if emp3 == 1 & intern !=1 & minijob !=1

gen int d3 = endepi - begepi +1 if nrE3 == 1 
bysort persnr (begepi nrE3): gen int tage_erw3 = sum(d3)


* Drop auxiliary variables
drop d1 d2 d3


*-----------------------------------------*
* PARALLEL JOBS (in different establishments)				  *
*-----------------------------------------*

/*
 Note: Duplicates must not be counted as seperate jobs;
 e.g. same establishment, bonus payment (grund == 54)
 -> All secondary BeH spells that are in same establishment are treated as duplicates

 Note: Meldung von einmaligen Arbeitsentgelten führt oft zu parallen Meldungen einer person in einem Betrieb
 grund: 40: Abmeldung Ender einer Beschäftigung, 54: Meldung einm. Entgelts, 49. Abmeldung wegen Tod; 50: Jahresmeldung

 Further considerations: how to classify main employment (income, type)?
*/

** Counter of employment per epidode in one establishment (voc. training seperate)

preserve
	
	* Keep only BeH spells
	keep if quelle_gr==1
	
	gen tentgelt_h = - tentgelt
	bysort persnr begepi bnn tentgelt_h: gen byte nrSE = _n

	* Total number of jobs in different establishments
	bysort persnr emp1 begepi: gen nrE = _n if nrSE ==1
	bysort persnr emp1 begepi: gen nr_jobs = _N if nrSE ==1

	tab nr_jobs quelle_gr if quelle_gr ==1 , m
	tab nr_jobs quelle_gr if quelle_gr ==1 & level2==0, m
	sum nr_jobs if quelle_gr ==1 & level2==0, d

/* Sanity check: Vast majority of people has one job (acc. to definition above) at one time;
In around 5% of episodes, people have more than one job simultaneously
BeH missings are mainly due to voc. training;
*/

* Copy variable to all BeH spells that were ignored so far, to spells in same establishment
* Copy only to BeH spells or all spells?
	*sort persnr spell
*replace nr_jobs = nr_jobs[_n-1] if quelle==1 & emp1==1 & persnr == persnr[_n-1] & begepi == begepi[_n-1]& betnr==betnr[_n-1]

** Tag all BeH episodes in which person has more than one job in different establishments
* (emp1)
gen byte morethanonejob =0.
replace morethanonejob =1 if nr_jobs >1 

* Copy to all other spells in periods with employment
replace morethanonejob = morethanonejob[_n-1] if persnr == persnr[_n-1] & begepi == begepi[_n-1]

/* Now, for all epsiodes in which a person (no matter of the quelle)
- has one job: 0
- has more than one job: 1
- has no job at all: missing (.)
*/

** Tag all people which had a period with more than one job in their employment history 
* does this make sense? no time restrictions
*bysort persnr: egen byte morethanonejob_tag = max(morethanonejob)

	* Runnung total of duration of periods with more than one job
	bysort persnr emp1 begepi: gen d =  endepi - begepi +1 if nrSE == 1 & nrE ==1 & morethanonejob ==1
	bysort persnr (begepi nrE): gen int morethanonejob_tage = sum(d)

	keep persnr spell morethanonejob morethanonejob_tage
	tempfile sec_job
	save `sec_job'
restore

merge 1:1 persnr spell using `sec_job'
drop _merge

* standars sorting
sort persnr spell


*--------------------------------------*
* FIRST DAY IN ESTABLISHMENT (ein_bet) *
*--------------------------------------*

bysort persnr bnn: egen int ein_bet = min(begepi) if !missing(bnn)
format ein_bet %tdDD_Mon_CCYY

*--------------------------------------------*
* NUMBER OF DAYS IN ESTABLISHMENT (tage_bet) *
*--------------------------------------------*

/* Total duration in one establishment, breaks are ignored;
here, all types of unemployment are considered
*/

* AUXILIARY VARIABLE MARKS DUPLICATE OBSERVATIONS PER ESTABLISHMENT AND EPISODE
bysort persnr bnn begepi endepi (spell): gen byte nrB = _n if !missing(bnn)

* CALCULATION OF THE DURATION
gen int dauer = endepi - begepi +1 if nrB == 1

* RUNNING TOTAL OF DAYS IN ESTABLISHMENT
bysort persnr bnn (spell): gen int tage_bet = sum(dauer) if !missing(bnn)


* Drop auxiliary variables
drop nrB dauer

*----------------------------*
* FIRST DAY IN JOB (ein_job) *
*----------------------------*

* SORT OBSERVATIONS BY PERSON, ESTABLISHMENT (VOCATIONAL TRAINING SEPARATE) AND EPISODE
sort persnr azubi bnn spell

* MARK SUBSEQUENT EPISODES OF JOB
* NOTE: FIRST OBSERVATION IS SET TO MISSING!
gen byte job = 1 if persnr == persnr[_n-1] & bnn == bnn[_n-1] & azubi == azubi[_n-1] & !missing(bnn)

* CONSIDER ENDING NOTIFICATION OF PREVIOUS MAIN EMPLOYMENT IN CASE OF GAPS
* 30: Ende Beschäftigung, 34: Ende sozialvpfl. Beschäftigung (?), 40: gleichzeitig An- und Abmeldung (?), 49: Tod
bysort persnr azubi bnn begepi (spell): gen byte end = 1 if inlist(grund[1], 0, 5)

* COUNT AS NEW JOB IF EMPLOYER REPORTED END OF EMPLOYMENT AND GAP > 92 DAYS
* COUNT AS NEW JOB IF GAP > 366 DAYS
gen int gap = begepi - endepi[_n-1] -1 if job == 1 
replace job = . if end[_n-1] == 1 & gap > 92
replace job = . if gap > 366



* GENERATE START DATE OF JOB, THEN COPY IT TO SUBSEQUENT OBSERVATIONS OF SAME JOB
gen int ein_job = begepi if !missing(bnn)
replace ein_job = ein_job[_n-1] if job ==1
format ein_job %tdDD_Mon_CCYY

* Drop auxiliary variables
drop end gap


*----------------------------------*
* NUMBER OF DAYS IN JOB (tage_job) *
*----------------------------------*

* AUXILIARY VARIABLE FOR NUMBER OF PARALLEL EPISODES PER JOB
* VOCATIONAL TRAINING SEPARATE
bysort persnr azubi bnn begepi (spell): gen byte nrA = _n if !missing(bnn)

gen int jobdauer = endepi - begepi +1 if !missing(bnn)
gen int jobdauer_kum = jobdauer
gen int jobdauer_dup = 0

* AUXILIARY VARIABLE FOR DURATION OF PARALLEL EPISODES IN SAME ESTABLISHMENT (VOCATIONAL TRAINING SEPARATE)
replace jobdauer_dup = jobdauer if nrA != 1

* RUNNING TOTAL OF JOB DURATION (MINUS DURATION OF PARALLEL EPISODES)
replace jobdauer_kum = jobdauer_kum[_n-1] + jobdauer - jobdauer_dup if job ==1


* Recode such that variable tags the start of a new job
replace job = 0 if job ==1
replace job =1 if job == . & quelle_gr ==1
rename job job_start

gen int tage_job = jobdauer_kum

drop jobdauer jobdauer_kum jobdauer_dup nrA

sort persnr spell

*--------------------------------------*
* NUMBER OF BENEFIT RECEIPTS LeH (anz_lst_leh) *
*--------------------------------------*

* MARK EPISODE OF BENEFIT RECEIPT (DATA SOURCES LeH, LHG)
gen byte quelleLeH = inlist(quelle_gr, 2)

* COUNTER OF BENEFIT RECEIPTS WITHIN EPISODE 
bysort persnr begepi quelleLeH (quelle_gr spell): gen byte nrLeH  = _n if quelleLeH

* COPY END DATE OF LAST BENEFIT RECEIPT TO SUBSEQUENT OBSERVATIONS
* for all spell sources
sort persnr spell
gen int ende_vor_leh = .
replace ende_vor_leh = endepi[_n-1] if quelleLeH[_n-1] & persnr == persnr[_n-1]
replace ende_vor_leh = ende_vor_leh[_n-1] if missing(ende_vor_leh) & persnr == persnr[_n-1]
format ende_vor_leh %td

* MAark observations that count as (start of) seperate benefit receipts
* Only 1 per episode, separate benefit receipt if gap > 10 days 
gen byte lst_leh = quelleLeH & nrLeH == 1 & (begepi - ende_vor_leh > 10)

* RUNNING TOTAL OF BENEFIT RECEIPTS
gsort persnr begepi -lst_leh
gen int anz_lst_leh = lst_leh
replace anz_lst_leh = anz_lst_leh[_n-1] + lst_leh if persnr == persnr[_n-1]

** Keep variable indicating the start of a new benefit receipt
rename lst benefit_start_leh

** Mark periods with benefit receipts (for all spell sources)
gen breceipt_leh = 1 if quelleLeH==1

gsort persnr begepi -quelleLeH
replace breceipt_leh = breceipt_leh[_n-1] if persnr == persnr[_n-1] & begepi == begepi[_n-1] & inlist(quelle_gr, 1, 3, 4, 5)

* Drop auxiliary variables, standrad sorting
drop ende_vor_leh

sort persnr spell

/*
*/

*------------------------------------------------*
* NUMBER OF DAYS WITH BENEFIT RECEIPT LeH (tage_lst_leh) *
*------------------------------------------------*

* DURATION OF BENEFIT RECEIPT (WITHOUT DURATION OF PARALLEL OBSERVATIONS)
gen int lstdauer_leh = endepi - begepi +1 if quelleLeH ==1 & nrLeH ==1 

* RUNNING TOTAL OF DAYS IN BENEFIT RECEIPT
bysort persnr (spell): gen int tage_lst_leh = sum(lstdauer_leh) if nrLeH ==1	| quelleLeH ==0

* FILL VARIABLE FOR PARALLEL OBSERVATIONS
bysort persnr begepi (nrLeH): replace tage_lst_leh = tage_lst_leh[1]

** Duration of single benefit receipts 
* gaps under 10 days are not counted as start of new benefit (see above)

bysort persnr anz_lst_leh (spell): egen lstdauer_leh_kum = sum(lstdauer_leh) if breceipt_leh==1

* Drop auxiliary variables, reestablish standrad sorting
drop nrE1 nrE2 nrE3 quelleLeH nrLeH
sort persnr spell


*--------------------------------------*
* NUMBER OF BENEFIT RECEIPTS LHG (anz_lst_lhg) *
*--------------------------------------*

* MARK EPISODE OF BENEFIT RECEIPT (DATA SOURCES LeH, LHG)
gen byte quelleLHG = inlist(quelle_gr, 3)

* COUNTER OF BENEFIT RECEIPTS WITHIN EPISODE 
bysort persnr begepi quelleLHG (quelle_gr spell): gen byte nrLHG  = _n if quelleLHG

* COPY END DATE OF LAST BENEFIT RECEIPT TO SUBSEQUENT OBSERVATIONS
* for all spell sources
sort persnr spell
gen int ende_vor_lhg = .
replace ende_vor_lhg = endepi[_n-1] if quelleLHG[_n-1] & persnr == persnr[_n-1]
replace ende_vor_lhg = ende_vor_lhg[_n-1] if missing(ende_vor_lhg) & persnr == persnr[_n-1]
format ende_vor_lhg %td

* MAark observations that count as (start of) seperate benefit receipts
* Only 1 per episode, separate benefit receipt if gap > 10 days 
gen byte lst_lhg = quelleLHG & nrLHG == 1 & (begepi - ende_vor_lhg > 10)

* RUNNING TOTAL OF BENEFIT RECEIPTS
gsort persnr begepi -lst_lhg
gen int anz_lst_lhg = lst_lhg
replace anz_lst_lhg = anz_lst_lhg[_n-1] + lst_lhg if persnr == persnr[_n-1]

** Keep variable indicating the start of a new benefit receipt
rename lst_lhg benefit_start_lhg  

** Mark periods with benefit receipts (for all spell sources)
gen breceipt_lhg = 1 if quelleLHG==1

gsort persnr begepi -quelleLHG
replace breceipt_lhg = breceipt_lhg[_n-1] if persnr == persnr[_n-1] & begepi == begepi[_n-1] & inlist(quelle_gr, 1, 2, 4, 5)

* Drop auxiliary variables, standrad sorting
drop ende_vor_lhg

sort persnr spell

/*
*/

*------------------------------------------------*
* NUMBER OF DAYS WITH BENEFIT RECEIPT (tage_lst_lhg) *
*------------------------------------------------*

* DURATION OF BENEFIT RECEIPT (WITHOUT DURATION OF PARALLEL OBSERVATIONS)
gen int lstdauer_lhg = endepi - begepi +1 if quelleLHG ==1 & nrLHG ==1 

* RUNNING TOTAL OF DAYS IN BENEFIT RECEIPT
bysort persnr (spell): gen int tage_lst_lhg = sum(lstdauer_lhg) if nrLHG ==1 | quelleLHG ==0

* FILL VARIABLE FOR PARALLEL OBSERVATIONS
bysort persnr begepi (nrLHG): replace tage_lst_lhg = tage_lst_lhg[1]

** Duration of single benefit receipts 
* gaps under 10 days are not counted as start of new benefit (see above)

bysort persnr anz_lst_lhg (spell): egen lstdauer_lhg_kum = sum(lstdauer_lhg) if breceipt_lhg==1

* Drop auxiliary variables, reestablish standrad sorting
drop  quelleLHG nrLHG
sort persnr spell



*------------------------------------------------*
* NUMBER OF DAYS IN SUBZIDIZED EMPLOYMENT (tage_se)
*------------------------------------------------*
* subisidized employment if erwstat in ???
gen se =1 if quelle_gr ==4 & inlist(erwstat,41,44)
gsort persnr begepi -quelle_gr
replace se = se[_n-1] if persnr== persnr[_n-1] & begepi ==begepi[_n-1] & missing(se)

*** Duration of subsidized employment
gen quelleMSE = 1 if quelle_gr ==4 & inlist(erwstat, 41, 44)
bysort persnr begepi quelleM: gen nrMSE = _n if quelleMSE==1
tab nrMSE // there are people with multiple parallel measures

gen int sedauer = endepi - begepi +1 if quelleMSE ==1 & nrMSE ==1 
bysort persnr (spell): gen int tage_se = sum(sedauer) if nrMSE ==1	

*** Copy to all spells in same episode
gsort persnr begepi -quelle_gr
replace  tage_se  = tage_se[_n-1] if persnr== persnr[_n-1] & begepi ==begepi[_n-1] & missing(tage_se)

*** Drop aux. variables, re-establish standard sorting
drop quelleMSE nrMSE
sort persnr spell

*drop tage_se_sp tage_se_kum

*------------------------------------------------------------------------------------------------
* Modify and save data

*-----------------------*
* ADJUST MISSING VALUES 
*-----------------------*

foreach var of varlist ein_bet tage_bet ein_job tage_job {
	replace `var' = .n if quelle_gr != 1
	replace `var' = .z if quelle_gr ==1 & missing(`var')
}
replace ein_erw1 = .z if missing(ein_erw1)
replace ein_erw2 = .z if missing(ein_erw2)
replace ein_erw3 = .z if missing(ein_erw3)

*--------------------------------------------------*
* LABEL THE GENERATED VARIABLES                    *
*--------------------------------------------------*
sort persnr spell


label language en
label variable level1 		"Obs. counter per episode and source"
label variable level2 		"Obs. counter per episode"
label variable azubi 		"Vocational training"
label variable intern 		"Interns, working students"
label variable minijob 		"Marginal emplyoment/ minijob"
label variable emp1 		"Employment spell (w/o voc. training)"
label variable emp2 		"Employment spell (w/o voc. training, internships etc.)"
label variable emp3 		"Employment spell (w/o voc. training, internships, minijobs)"
label variable ein_erw1    	"First day in employment (w/o voc. training)"
label variable ein_erw2    	"First day in employment (w/o voc. training, internships)"
label variable ein_erw3    	"First day in employment (w/o voc. training, internships, minijobs)"
label variable tage_erw1   	"Number of days in employment (w/o voc. training)"
label variable tage_erw2   	"Number of days in employment (w/o voc. training, internships)"
label variable tage_erw3   	"Number of days in employment (w/o voc. training, internships, minijobs)"
label var morethanonejob	"BeH spell > 1 job (different establ.)"
*label var morethanonejob_tag "Person had episode > 1 job"
label var morethanonejob_tage  "Number of days with > 1 job"
label variable ein_bet    	"First day in establishment"
label variable tage_bet   	"Number of days in establishment"
label variable ein_job    	"First day in job"
label variable tage_job   	"Number of days in job"
label variable job_start   	"Binary variable indicating start of new job"
label variable anz_lst_leh    	"Number of benefit receipts"
label variable benefit_start_leh "Binary variable indicating start of new benefit receipts"
label variable breceipt_leh	"Binary variable indicating benefit receipt in episode"
label variable tage_lst_leh   	"Number of days with benefit receipt"
label variable lstdauer_leh	"Number of days of benefit receipt (spell)"
label variable lstdauer_leh_kum "Number of days of benefit receipt (cum.)"
label variable anz_lst_lhg   	"Number of benefit receipts"
label variable benefit_start_lhg  "Binary variable indicating start of new benefit receipts"
label variable breceipt_lhg 	"Binary variable indicating benefit receipt in episode"
label variable tage_lst_lhg    	"Number of days with benefit receipt"
label variable lstdauer_lhg 	"Number of days of benefit receipt (spell)"
label variable lstdauer_lhg_kum "Number of days of benefit receipt (cum.)"
*label variable nr_jobs		"Number of parallel jobs"
label variable pg5 			"Employment groups, 5 categories"
label variable se			"Episode with subsidized employment"
label variable sedauer		"Numer of days of sub. employment (spell)"
label variable tage_se		"Number of days in sub. employment (cum.)"


label language de
label variable level1 		"Obs. Counter per Episode und Quelle"
label variable level2 		"Obs. Counter per Episode"
label variable azubi 		"Ausbildung"
label variable intern 		"Praktikum, Werkstudent"
label variable minijob 		"Minijob"
label variable emp1 		"BeH spell (ohne Ausbildung)"
label variable emp2 		"BeH spell (ohne Ausbildung, Praktika etc.)"
label variable emp3 		"BeH spell (ohne Ausbildung, Praktika etc., Minijobs)"
label variable ein_erw1    	"Eintrittsdatum Erwerbsleben (ohne Ausbildung)"
label variable ein_erw2    	"Eintrittsdatum Erwerbsleben (ohne Ausbildung, Praktika etc.)"
label variable ein_erw3    	"Eintrittsdatum Erwerbsleben (ohne Ausbildung, Praktika etc., Minijobs)"
label variable tage_erw1   	"Dauer Erwerbsleben (ohne Ausbildung)"
label variable tage_erw2   	"Dauer Erwerbsleben (ohne Ausbildung, Praktika etc.)"
label variable tage_erw3   	"Dauer Erwerbsleben (ohne Ausbildung, Praktika etc., Minijobs)"
label var morethanonejob	"BeH spell > 1 job (versch. Betriebe)"
label var morethanonejob_tage  "Dauer Tage in > 1 job"
label variable ein_bet    	"Eintrittsdatum Betrieb"
label variable tage_bet   	"Dauer Betrieb"
label variable ein_job    	"Eintrittsdatum Job"
label variable tage_job   	"Dauer Job"
label variable anz_lst_leh   	"Anzahl bisheriger Leistungsbezuege"
label variable tage_lst_leh   	"Dauer bisheriger Leistungsbezuege"
label variable job_start   	"Start eines neuen Jobs (bin. Var)"
label variable breceipt_leh	"Leistungsbezug in Episode (bin. Var)"
label variable lstdauer_leh	"Dauer des Leistungsbezug (aus Spellebene)"
label variable lstdauer_leh_kum "Dauer des Leistungsbezug (der kompletten Episode)"
label variable anz_lst_lhg    	"Anzahl bisheriger Leistungsbezuege"
label variable tage_lst_lhg   	"Dauer bisheriger Leistungsbezuege"
label variable job_start  	"Start eines neuen Jobs (bin. Var)"
label variable breceipt_lhg		"Leistungsbezug in Episode (bin. Var)"
label variable lstdauer_lhg		"Dauer des Leistungsbezug (aus Spellebene)"
label variable lstdauer_lhg_kum "Dauer des Leistungsbezug (der kompletten Episode)"
label variable benefit_start_leh "Start neuer Leistungsbezugs (bin. Var)"
label variable benefit_start_lhg "Start neuer Leistungsbezugs (bin. Var)"
*label variable nr_jobs		"Anzahl paraller Jobs"
label variable se			"Episode mit geförderter Beschäftigungen"
label variable sedauer		"Dauer der geförderten Beschäftigung"
label variable tage_se		"Dauer bisheriger geförderter Beschäftigungen (kum.)"

*--------------------------------------------------*
* ADJUST MISSINGS                   
*--------------------------------------------------*


foreach var of varlist ein_erw1  ein_erw2  ein_erw3  ein_bet tage_bet ein_job tage_job {

	label language en
	lab def `var'_en .n "n/a" .z "no entry", add modify
	lab val `var' `var'_en
	numlabel `var'_en, add mask("#  ")

	label language de
	lab def `var'_de .n "fehlt syst." .z "k. Angabe", add modify
	lab val `var' `var'_de
	numlabel `var'_de, add mask("#  ")

}

*--------------------------------------------------*
* RENAME VARIABLES AND ORDER THE VARIABLES                    
*--------------------------------------------------*

* Systematic
* _sp: Only for single spell
* _ep: For all spells in same episode
* _kum: cumulated 


* Benefit receipts
rename anz_lst_leh anz_lst_leh_kum
rename benefit_start_leh beg_lst_leh_sp
rename breceipt_leh lst_leh
rename tage_lst_leh tage_lst_leh_kum
rename lstdauer_leh tage_lst_leh_sp
rename lstdauer_leh_kum tage_lst_leh_ep

rename anz_lst_lhg anz_lst_lhg_kum
rename benefit_start_lhg beg_lst_lhg_sp
rename breceipt_lhg lst_lhg
rename tage_lst_lhg tage_lst_lhg_kum
rename lstdauer_lhg tage_lst_lhg_sp
rename lstdauer_lhg_kum tage_lst_lhg_ep

* Job
rename tage_job tage_job_kum
rename job_start beg_job_sp
rename ein_job ein_job
rename tage_bet tage_bet_kum
rename ein_bet ein_bet

rename tage_erw1 tage_erw1_kum
rename tage_erw2 tage_erw2_kum
rename tage_erw3 tage_erw3_kum

*rename ein_erw1 ein_erw1_ep
*rename ein_erw2 ein_erw2_ep
*rename ein_erw3 ein_erw3_ep

rename emp1 emp1_sp
rename emp2 emp2_sp
rename emp3 emp3_sp

*rename nr_jobs anz_pjobs_ep
rename morethanonejob pjobs_ep
rename morethanonejob_tage tage_pjobs_kum

rename se se_ep
rename sedauer tage_se_sp
rename tage_se tage_se_kum 


* Reihenfolge
* tage_lst_sp tage_lst_ep tage_lst_kum
*order 


compress
sort persnr spell
*save ${data}/${dataname}_sample_bio_HM.dta, replace
save "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/siab_r_7517_v1_sample_bio_HM.dta", replace

cap log close
exit
