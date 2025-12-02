********************************************************************************
*	RESHAPHING THE DATA
*
*	Author: Hannah Mautner
*	Goal: 	Reshape data for machine learning models

*	Approach:
*		- 1 Restricting data to population of (unemployed) job seekers 8with unemployment begin during 2010-2013)
*		- 2 Predictors: Generate variables on person level 
*				- 2.1 Employment history (BeH)
*				- 2.2 ASU history
*				- 2.3 Benefit history (LeH, LHG)
*				- 2.4 Measures history (MTH)
*		 		- 2.5 Biographical variables
*				- 2.6 Current job seeking characteristics 
*		- 3 Response/ outcome variable 
*		- 4 Label and order variables 
*		- 5 Delete irrelevant information
*
*	
 /* 	Poposed variables:
		Historic employment data
				- Status right before relevant unemployment episode DONE
				
				- 2.1.1 Time since first employment (3 versions) DONE
				- 2.1.2 Cumulated time in employment (3 versions) DONE
					
				□ Number of different jobs overall
					- In same/different establishments 
					- Number of establishments worked
					- mean duration of previous jobs
					
				□ Last job before entering unemployement
					® Duration of the last job DONE
					® Duration since the last jobs/ last contact to labour market DONE
						- for all jobs DONE
						- only for full-time position DONE
					® Niveau of last job DONE
					® Type of job(Part-time, marginal employment) DONE
					® More than one job?
					- Home location during last job
						- Bundesland DONE
						- Kreis DONE
					- Estalishment info of last job
						- Location of last job:
							- east vs. west DONE
							- Bundesland DONE
							- Kreis DONE
						- Size of establishment DONE
						- Industry of last estabilshment (2 versions) DONE
					- commuted to last job (wo_kreis != ao_kreis) DONE		
					
				□ All previous jobs
					® Number of seperate jobs DONE
					® Total of days in employment 
						- 3 versions DONE					
					□  Secondary jobs
						- total duration when having at least one secondary job DONE
					® Cumulated duration in
						- full-time employment DONE
						- marginal employment DONE
					® Duration since first being employed (vs. Age?)
						- Ruben fragen
				□ Establishments: East/west, size, industry
				- Industry in which person has worked most of the time
				- size
					
		- Job search/ unemployment history
				- Time since last job search/ unemployment DONE
					- Number of seperate job search episodes DONE
					- Cumulated duration in job searching DONE
					- mean time in job searching DONE
					
		- Benefit receipt history
			- LeH receipt DONE
				- Cum. duration, number of seperate receipts, mean duration
			- LHG receipt DONE
				- Cum. duration, number of seperate receipts, mean duration

	 Note: 	Some cumulated variables have been generated before (see );
			Now, right values, i.e. values cumulated till the start of the unemploymen tob sekking period have tobe slected			

*/
*
*
*
*
*
********************************************************************************


********************************************************************************
* Choose version of short-term unemployment to work with   
********************************************************************************

*use ${data}_beforereshaping_20180607.dta, clear
*use ${data}_beforereshaping_20180614.dta, clear



********************************************************************************
* 1 Restricting data to population of jobseekers (in 2010-2014)    
********************************************************************************


*** Delete all spells that are after relevant unemployment/ job seeking period
gen date_help = beg_ue_date if relevant_ue==1 
bysort persnr: egen beg_relevant_ue_date = max(date_help)
		format beg_relevant_ue_date %tdDD_Mon_CCYY
	
*** Store spells in case they are needed later
/*
preserve
drop if begepi <= beg_relevant_ue_date
save ${data}/${dataname}_deleted_spells_uepop${version}_${date}.dta, replace
restore
*/

drop if begepi > beg_relevant_ue_date


********************************************************************************
* 2 Predictors          
********************************************************************************

gen lhgspell  								= (quelle_gr==3) 
gen behspell  								= (quelle_gr==1)
gen lehspell  								= (quelle_gr==2)
gen asuspell  								= (quelle_gr==5)
gen mthspell  								= (quelle_gr==4)


********************************************************************************
* 2.1 Employment history data           
********************************************************************************

********************************************************************************
*** 3.1.1 Status before job seeking/ unemployed episode (6 weeks prior)

/* 	Create binary variable for following incidences: 
	- Being employed  
	- Receiving benefits (LeH)
	- Receiving benefits (LHG) 
	- Being in subsidized employment
	- Registered as not unemployed and job seeking in ASU register
	- Begistered for any other reason in ASU register 
	- Having a break in employment history (when distance to nearest spell > 6 weeks/ 42 days)

To do: Look at individual which have missings for all before-variables
-> Did I miss something?	
	*/
 
preserve
	* Drop "current" spells
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP==1 
	
	sort persnr spell
	bysort persnr: egen status_beg_date = max(begepi)					// begin date of spell closest to unemployment episode
	format status_beg_date %tdDD_Mon_CCYY
	drop if begepi != status_beg_date									// drop all other spells
	
	* Check whether observations
	quietly count if !missing(persnr)
	if `r(N)' > 0 {
	
		* Time passed since ending of previous spells
		gen t_since_spell = beg_relevant_ue_date - endepi +1
		
		* Binary variables for status before UE/ job seeking episode
		bysort persnr: egen employed = max(behspell) 						if t_since_spell <=42
		bysort persnr: egen receipt_leh = max(lehspell) 					if t_since_spell <=42
		bysort persnr: egen receipt_lhg = max(lhgspell) 					if t_since_spell <=42
		bysort persnr: egen se = max(se_ep) 								if t_since_spell <=42
		gen ASU_notue_seeking_help= inlist(erwstat, 23) 			// not unemployed but seeking
		bysort persnr: egen ASU_notue_seeking = max(ASU_notue_seeking_help)	if t_since_spell <=42 
		bysort persnr: egen ASU_other_help = max(asuspell) 					if t_since_spell <=42 
		gen ASU_other = 1 if ASU_other_help==1 & ASU_notue_seeking !=1 			// all other ASU spells
		bysort persnr: gen break = 1 if t_since_spell >42					// break if spell 
		
		bysort persnr: gen id =_n
		keep if id ==1
		keep persnr employed receipt_leh receipt_lhg se ASU_notue_seeking ASU_other break
		
		foreach v of varlist employed receipt_leh receipt_lhg se ASU_notue_seeking ASU_other break {
			recode `v' (.=0)
			rename `v' `v'_before
		}
	}
	
	tempfile status
	save `status'
restore

merge m:1 persnr using `status'
drop _merge

* Adjust missings; Note: For individuals with missings, there are no previous spells available, i.e. UE spell is first spell
	foreach v of varlist employed_before receipt_leh_before receipt_lhg_before se_before ASU_notue_seeking_before ASU_other{
		recode `v' (.=0)
}

replace break_before =1 if missing(break_before)


********************************************************************************
*** Employment status before relevant job seeking period (acc. to ASU) (estatvor)

/* 	1: In Beschäftigung
	2: In Ausbildung
	3: Selbstständige, Mithelfende
	4: Nicht Erwerbstätige 
	5: Erneute Meldung nach Meldeversäumnis
	6: Arbeitsunfähigkeit
	7: ALMP
	8: Vermittlungssperre
	9: unbekannt


recode estatvor(1/4 13 14 15 60 70 74 75  =1) (5/10 16/25 62 63 64 70 71 76 77 85 = 2) (11 12 61= 3) (26/39 69 72 =4) (66 67 78= 5) (65 = 6) (79 80 90 92 = 7) (91 = 8) (.z 81 68 82 100 = 9) , gen(status_before)
tab status_before
label define status_before_label 1"Employment" 2"Voc. training" 3"Self-employed" 4"Not employed" 5"Repeated registration" 6"Not able to work" 7"ALMP" 8"Ban" 9"Unknown"
label value status_before status_before_label
*/
********************************************************************************
*** 3.1.1 Number of different jobs a person had

/* 	Generated variable(s): emp_total
	Definition of total employment: Number of seperate jobs; 
	when employed in same establishment, only counted as new job when break between employments
	when different establishments, then seperate employments
*/

preserve
	* Drop "current" episode and only keep BeH spells
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP==1	
	keep if inlist(quelle_gr,1)
	
	* Check whether observations
	quietly count if !missing(persnr) 
	if `r(N)' > 0 {
	
		bysort persnr ein_job bnn (begepi): gen nrE = _n if !missing(ein_job) // tag first spell of seperate jobs
		keep if nrE ==1 // keep only one spell per continuous job
		
		bysort persnr: gen emp_total = _N // Total number of jobs a person had
				

		bysort persnr bnn: gen nrEst = _n
		bysort persnr: gen est_total = _N  if nrEst==1 // Total number of establishments a person worked in
		
		* Same without vocational training
		drop if azubi  ==1
		
		bysort persnr ein_job bnn (begepi): gen nrE1 = _n if !missing(ein_job) // tag first spell of seperate jobs
		keep if nrE1 ==1 // keep only one spell per continuous job
		
		bysort persnr: gen emp1_total = _N
		
		bysort persnr: gen id = _n
		keep if id==1
		keep persnr est_total emp_total emp1_total
	}
		
	tempfile nrjobs
	save `nrjobs'
restore

merge m:1 persnr using `nrjobs'
drop _merge


foreach v of varlist est_total emp_total emp1_total{
recode  `v' (.=0)
}

********************************************************************************
*** 3.1. Industries a person worked in

/*  Generated variable(s): 
	- main_industry: The industry a person has worked in longest (destatis)
	- industry1_destatis_tot_dur_*: Tot. duration worked in all industries
	
To do:
	- Explore why there are so many missing for main_industry
*/

* Create aux. variable (job_duration_help): To each start of a new job (ein_job), write how long person had the job
bysort persnr indust ein_job: egen job_duration_help = max(tage_job_kum) if !missing(ein_job) // for every entry date: 
 
preserve
	* Drop "current" episode, keep only spells indicating start of new job
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP==1	
	keep if beg_job_sp ==1 // keep only start spells for jobs
	
		* Check whether observations
	quietly count if !missing(persnr)
	if `r(N)' > 0 {
	
		bysort persnr indust: egen job_duration_help2 = sum(job_duration_help) // total duration in each industry
		bysort persnr indust: egen industry_tot_dur = max(job_duration_help2) // 
		bysort persnr: egen main_industry_help = max(industry_tot_dur)
		bysort persnr: gen main_industry_help2 = indust if main_industry_help == industry_tot_dur
		bysort persnr: egen main_industry = max(main_industry_help2)
		
		forvalues i = 1/14 {
			 by persnr: egen industry1_destatis_help_`i' = max(industry_tot_dur) if indust == `i'
			 by persnr: egen industry1_destatis_tot_dur_`i' = max(industry1_destatis_help_`i') 
		}
			
		bysort persnr: gen id = _n
		keep if id==1
		keep persnr main_industry industry1_destatis_tot_dur_*
	}
	
	tempfile main_industry
	save `main_industry'
restore

merge m:1 persnr using `main_industry'
drop _merge

* Modify missing values
foreach v of varlist industry1_destatis_tot_dur_* {
recode  `v' (.=0)
}



* Adjust missings; people who have not worked before 
tab main_industry if relevant_ue==1, m
tab main_industry if relevant_ue==1, m
tab persnr if missing(main_industry) & relevant_ue==1 & ltue==1
replace main_industry = 99999 if main_industry ==. 

/* Label variable main_industry
label define industry 1 "1 Land- u. Forstwirtschaft" 2 "2 Fischerei etc." 3"3 Bergbau etc." 4"4 Verarbeitendes Gewerbe" 5"5 Energie- und Wasserversorgung" 6"6 Baugewerbe" 7"7 Handel" 8"G8 Gastgewerbe" 9"9 Verkehr, Post et." 10"10 Finanzbranche" 11"11 Grund- Wohnwesen" 12"12 Verwaltung etc." 13"13 Erziehung" 14"14 Gesundheits- udn Sozialwesen" 15"15 Sonstige DL" 16"16 Private Haushalte" 99999"Unknown" 
*/
label value main_industry INDUST


* Drop auxiliary variables, establish standard sorting	
sort persnr spell job_duration_help

********************************************************************************
*** 3.1.1 Cumulated time in employment (tage_erw1, tage_erw2, tage_erw3)	

/* Generated variable(s): 
	- emp1_total_dur 
	- emp2_total_dur 
	- emp3_total_dur 
	- emp1_m_dur
*/	

preserve	
	* Drop "current" episode
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP==1	
		
	* Check whether observations
	quietly count if !missing(persnr)
	if `r(N)' > 0 {
	
		* Cumulate all durations before current episode
		foreach v of varlist tage_erw1_kum tage_erw2_kum tage_erw3_kum{
			bysort persnr: egen `v'_help = max(`v') 
			rename `v' `v'_d
			rename `v'_help `v'
		}
		
		bysort persnr: gen id=_n
		keep if id==1
		keep persnr tage_erw1_kum tage_erw2_kum tage_erw3_kum
		
		rename tage_erw1_kum emp1_total_dur
		rename tage_erw2_kum emp2_total_dur
		rename tage_erw3_kum emp3_total_dur
	}
	
	tempfile ehist_var
	save `ehist_var'
restore

merge m:1 persnr using `ehist_var'
drop _merge 

* Calculate mean duration of employments
gen emp1_m_dur =  emp1_total_dur/ emp1_total 

* Drop variables that are no longer needed
drop tage_erw1_kum tage_erw2_kum tage_erw3_kum
sort persnr spell

foreach v of varlist emp1_total_dur emp2_total_dur emp3_total_dur emp1_m_dur {
recode  `v' (.=0)
}

********************************************************************************
*** 3.1.1 Time since first employment (ein_erw1, ein_erw2, ein_erw3)
* Note: Voc. training is not consideed here 

/* generated variable(s).
	- tsince_ein_erw1

*/

gen tsince_ein_erw1 = beg_ue_date - ein_erw1 if relevant_ue ==1

gen tsince_ein_erw1_cat = 99999
replace tsince_ein_erw1_cat = 1 if tsince_ein_erw1 > 0 		& tsince_ein_erw1 <= 365
replace tsince_ein_erw1_cat = 2 if tsince_ein_erw1 > 365 	& tsince_ein_erw1 <= 1825
replace tsince_ein_erw1_cat = 3 if tsince_ein_erw1 > 1825 	& tsince_ein_erw1 <= 3650
replace tsince_ein_erw1_cat = 3 if tsince_ein_erw1 > 3650 	& !missing(tsince_ein_erw1)

* Drop irrelevant spell info and all variables that are no longer needed, standard sorting
drop ein_erw1 ein_erw2 ein_erw3
sort persnr spell


********************************************************************************
*** 3.1. Time since last contact to labour market

/* Generated variable(s):
	- tsince_lm_contact_cat
	- tsince_ft_lm_contact_cat
*/

 
*save ${data}test.dta, replace
 *use ${data}test.dta, clear

preserve	
	* Drop "current" episode and keep only BeH spells
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP == 1
	keep if behspell ==1 // only BeH spells
	
	* Check whether observations
	quietly count if !missing(persnr) 
	if `r(N)' > 0 {
	
	* for all jobs
	bysort persnr: egen lm_contact_date = max(endepi)  	
	format lm_contact_date %tdDD_Mon_CCYY
	
	* for full-time jobs	
	bysort persnr teilzeit: egen ft_lm_contact_date = max(endepi) if teilzeit !=1
	format ft_lm_contact_date %tdDD_Mon_CCYY
	
	bysort persnr: gen id = _n
	keep if id==1
	keep persnr lm_contact_date ft_lm_contact_date 
	}
	
	tempfile tslastjob
	save `tslastjob'
restore

merge m:1 persnr using `tslastjob'
drop _merge

sum persnr if lm_contact_date > beg_relevant_ue_date & !missing(lm_contact_date), d
gen tsince_lm_contact = beg_relevant_ue_date - lm_contact_date if relevant_ue ==1
gen tsince_ft_lm_contact = beg_relevant_ue_date - ft_lm_contact_date if relevant_ue ==1
gen last_job_end = 1 if lm_contact_date == endepi & behspell==1

* Create categorical variables: last 3 monht, last 6 month, last year, longer 

foreach v of varlist tsince_lm_contact tsince_ft_lm_contact {
gen `v'_cat =1 if `v' <= 92
replace `v'_cat =2 if `v' <= 184 & missing(`v'_cat)
replace `v'_cat =3 if `v' <= 365 & missing(`v'_cat)
replace `v'_cat =4 if `v' > 365 & missing(`v'_cat) & !missing(`v')
replace `v'_cat =5 if `v' ==.  & missing(`v'_cat)
}

* Lavel variables
label define lastcontact 1"In last 3 month" 2"In last 6 month" 3"In last year" 4"Longer than 1 year" 5"No previous contact" 

foreach v of varlist tsince_lm_contact_cat tsince_ft_lm_contact_cat{
label value `v' lastcontact
}

*Adjust missings; no missings

* Drop irrelevant spell info and all variables that are no longer needed, standrad sorting
drop lm_contact_date ft_lm_contact_date 


********************************************************************************
*** Characteristics of last job 
		
/* Generated variables: 
	- lastjob_tot_dur
	- lastjob_parallel
	- lastjob_type: Employment group
	- lastjob_pt: Bin. variable indicating part-time employment
	- lastjob_wage_defl : Daily pay of last job(s) (deflated)
	- lastjob_occ_blo
	- lastjob_niveau 
	- lastjob_leih 
	- lastjob_befrist
	- lastjob_wo_kreis
	- lastjob_wo_bula 
	- lastjob_educ 	
	- lastjob_e_size
	- lastjob_e_bl: Bundesland of establishement 
	- lastjob_e_east: East vs. Wast
	- lastjob_occblo: Blossfeld occupation of last job
	- lastjob_ao_kreis 
	- lastjob_ao_bula 
	- lastjob_industry_destatis
	- lastjob_industry_iab 
	- lastjob_e_tsince_start
	- lastjob_communting
*/

preserve	
	gen DROP =1 if begepi == beg_relevant_ue_date // Drop "current" episode
	drop if DROP == 1
	keep if behspell ==1 // only BeH spells
	
	* Check whether observations
	quietly count if !missing(persnr) 
	if `r(N)' > 0 {
	
		* There are some people with more than one last jobs, i.e. parallel jobs were held			
		gen help = - tage_job_kum
		gen help2 = - tentgelt
		bysort persnr last_job_end (help help2): gen nrLEmp = _n 
		tab nrLEmp
		
		* Was last job parallel job?
		gen parallel = 0
		replace parallel = 1 if nrLEmp >1 & !missing(nrLEmp)
		by persnr: egen lastjob_parallel = max(parallel)
		
		keep if last_job_end  ==1 & nrLEmp ==1 // * keep only last job with longest duration (if more than one, than the one with highest pay)

		* Duration of last job
		gen lastjob_tot_dur 			= tage_job_kum 
		
		* Further characteristics
		gen lastjob_type 				= pg5  
		gen lastjob_pt					= teilzeit 
		gen lastjob_wage_defl 			= wage_defl
		gen lastjob_occblo				= occ_blo
		gen lastjob_niveau 				= niveau
		gen lastjob_leih 				= leih
		gen lastjob_befrist 			= befrist
*		gen lastjob_wo_kreis 			= wo_kreis
*		gen lastjob_wo_bula 			= wo_bula
		gen lastjob_educ 				= ausbildung_imp
*		gen lastjob_e_size 				= az_ges
*		gen lastjob_e_east 				= Ieast
		gen lastjob_ao_kreis 			= ao_region
*		gen lastjob_ao_bula 			= ao_bula
		gen lastjob_industry_destatis 	= indust
*		gen lastjob_industry_iab 		= industry1_estpanel
*		gen lastjob_e_tsince_start 		= endepi - grd_dat	
*		gen lastjob_communting 			= lastjob_ao_kreis != lastjob_wo_kreis

		bysort persnr: gen id = _n
		keep if id==1
		keep persnr lastjob_tot_dur lastjob_parallel lastjob_type lastjob_pt lastjob_wage_defl lastjob_occblo ///
		lastjob_niveau lastjob_leih lastjob_befrist  lastjob_educ 	///
		 lastjob_ao_kreis  ///
		lastjob_industry_destatis   
	
	}
	tempfile lastjob
	save `lastjob'
restore

merge m:1 persnr using `lastjob'
gen lastjob_none = 0
replace lastjob_none =1 if _merge==1 // Tag individuals with no last job
drop _merge
/*

* Convert lastjob_e_size into categorical variable
gen lastjob_e_size_cat  = 0
replace lastjob_e_size  = 1 if lastjob_e_size  ==1  
replace lastjob_e_size  = 1 if lastjob_e_size  > 1  & lastjob_e_size   <= 5 
replace lastjob_e_size  = 2 if lastjob_e_size  > 5  & lastjob_e_size  <= 10 
replace lastjob_e_size  = 3 if lastjob_e_size  > 10 & lastjob_e_size  <= 50 
replace lastjob_e_size  = 3 if lastjob_e_size  > 50 & lastjob_e_size  <= 200 
replace lastjob_e_size  = 3 if lastjob_e_size  > 200 & lastjob_e_size  <= 1000 
replace lastjob_e_size  = 4 if lastjob_e_size  > 1000 & !missing(lastjob_wage_defl)
*/
* Missings for categorical variables
foreach  v of varlist lastjob_type lastjob_parallel lastjob_pt lastjob_occblo lastjob_niveau lastjob_leih lastjob_befrist lastjob_educ  lastjob_ao_kreis  lastjob_industry_destatis  {
		replace `v' = 99999 if lastjob_none ==1	
		gen `v'_noinfo=0
		replace `v'_noinfo =1 if missing(`v') // tag observatiosn for which we have no info
		replace `v' = 99999 if missing(`v')
		}
		
* Missings for numerical variables
foreach  v of varlist lastjob_tot_dur lastjob_wage_defl  {
		replace `v'=0 if lastjob_none ==1		
		}
/*
*** Reason for end of last job/ Reason for end of previous employment:
gen lastjob_art_kuend = art_kuend
replace lastjob_art_kuend = 99999 if missing(lastjob_art_kuend)
*/
********************************************************************************
*** 3.1. Cumulated time in marginal employment(minijobs), part-time employment, Leiharbeit, befristet employment, more than one job

*** Cumulated time in marginal employment
preserve 
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP==1
	keep if behspell == 1 & minijob==1
	
	* Drop duplicates
	bysort persnr begepi: gen nrMJ = _n	
	drop if nrMJ>1 
		* Check whether observations
	quietly count if !missing(persnr) 
	if `r(N)' > 0 {
	
		* Duration in minijobs
		gen duration_m = endepi - begepi + 1
		by persnr: gen tage_minijob = sum(duration_m)
		by persnr: egen minijob_tot_dur = max(tage_minijob)
		
		by persnr: gen id =_n
		keep if id==1
		keep persnr minijob_tot_dur
	}
	
	tempfile minijob
	save `minijob'
restore

merge m:1 persnr using `minijob'
drop _merge

*** Cumulated time in part-time employment
preserve 
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP==1
	keep if behspell == 1 & teilzeit==1
	
	* Drop duplicates
	bysort persnr begepi bnn: gen nrJTZ = _n
	drop if nrJTZ > 1
	
	* Check whether observations
	quietly count if !missing(persnr)
	if `r(N)' > 0 {
	
		* Duration in minijobs
		gen duration_ft = endepi-begepi +1
		by persnr: gen tage_ft=sum(duration_ft)
		by persnr: egen ft_tot_dur = max(tage_ft)
		
		by persnr: gen id =_n
		keep if id==1
		keep persnr ft_tot_dur
	}
	
	tempfile ft
	save `ft'
restore

merge m:1 persnr using `ft'
drop _merge

***  Cumulated time in more than one job: secjob_tot_dur

preserve	
	* Drop "current" episode and keep only BeH spells
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP==1
	keep if behspell==1
	
	* Check whether observations
	quietly count if !missing(persnr)
	if `r(N)' > 0 {
		
		* Cumulated time having more than one job
		bysort persnr: egen secjob_tot_dur = max(tage_pjobs_kum)
		
		bysort persnr: gen id = _n
		keep if id==1
		keep persnr secjob_tot_dur
	}
	
	tempfile secjob 
	save `secjob'
restore

merge m:1 persnr using `secjob'
drop _merge

foreach v of varlist secjob_tot_dur {
recode  `v' (.=0)
}


***  Cumulated time in befristet employment: befrist_tot_dur 	
preserve 
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP==1
	keep if behspell == 1 & befrist==1
	
	* Check whether observations
	quietly count if !missing(persnr)
	if `r(N)' > 0 {
	
		* Drop duplicates
		bysort persnr begepi: gen nrJBe = _n
		drop if nrJBe > 1
	
		* Duration in minijobs
		gen duration_befrist = endepi-begepi +1
		by persnr: gen tage_befrist=sum(duration_befrist)
		by persnr: egen befrist_tot_dur = max(tage_befrist)
		
		by persnr: gen id =_n
		keep if id==1
		keep persnr befrist_tot_dur
	}
	
	tempfile befrist
	save `befrist'
restore

merge m:1 persnr using `befrist'
drop _merge
				
***  Cumulated time in befristet employment: leih_tot_dur
preserve 
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP==1
	keep if behspell == 1 & leih==1
		
	* Check whether observations
	quietly count if !missing(persnr)
	if `r(N)' > 0 {
	
		* Drop duplicates
		bysort persnr begepi: gen nrJLeih = _n
		drop if nrJLeih > 1
	
		* Duration in minijobs
		gen duration_leih = endepi-begepi +1
		by persnr: gen tage_leih=sum(duration_leih)
		by persnr: egen leih_tot_dur = max(tage_leih)
		
		by persnr: gen id =_n
		keep if id==1
		keep persnr leih_tot_dur
	}
	
	tempfile leih
	save `leih'
restore

merge m:1 persnr using `leih'
drop _merge

*** Adjust missings
foreach v of varlist secjob_tot_dur minijob_tot_dur ft_tot_dur befrist_tot_dur leih_tot_dur {
recode  `v' (.=0)
}

********************************************************************************
*	 2.2 Job seeking history data (ASU)         
********************************************************************************

********************************************************************************
*** 3.2.1 Time since last job search/ unemployment

preserve	
	* Drop "current" episode and keep only seeking1 spells
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP==1
	keep if beg_ue==1 // keep only start date of UE/ job seeking episodes
	
	* Check whether observations
	quietly count if !missing(persnr)
	if `r(N)' > 0 {
	
	bysort persnr: egen help_tss = max(begepi) 
	keep if begepi ==help_tss
	
	sort persnr begepi
	by persnr: gen tsince_lastseeking = beg_relevant_ue_date - endepi -1
	
	keep persnr tsince_lastseeking
	}
	
	tempfile lastseeking
	save `lastseeking'
restore

merge m:1 persnr using `lastseeking'
drop _merge

gen tsince_lastseeking_cat = 99999
replace tsince_lastseeking_cat = 1 if tsince_lastseeking <= 31
replace tsince_lastseeking_cat = 2 if tsince_lastseeking > 31  & tsince_lastseeking  <= 93
replace tsince_lastseeking_cat = 3 if tsince_lastseeking > 93  & tsince_lastseeking  <= 186
replace tsince_lastseeking_cat = 4 if tsince_lastseeking > 186 & tsince_lastseeking  <= 365
replace tsince_lastseeking_cat = 5 if tsince_lastseeking > 365 & tsince_lastseeking  <= 730
replace tsince_lastseeking_cat = 6 if tsince_lastseeking > 730 & tsince_lastseeking  <= 1825
replace tsince_lastseeking_cat = 7 if tsince_lastseeking > 1825 & !missing(tsince_lastseeking)  
tab tsince_lastseeking_cat 

********************************************************************************
*** 3.2. Previous job search times (job seeking while being unemployed): Total, cum. duration, mean duration

preserve	
	* Drop "current" episode and keep only seeking1 spells
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP==1
	drop if beg_ue !=1
	
	* Check whether observations
	quietly count if !missing(persnr)
	if `r(N)' > 0 {
		bysort persnr: gen seeking1_total = _N
		bysort persnr: gen tage_seeking1_cum_help = sum(ue_duration)
		bysort persnr: egen seeking1_tot_dur = max(tage_seeking1_cum_help)
		gen seeking1_m_dur= tage_seeking1_cum/ seeking1_total
		
		bysort persnr: gen id = _n
		keep if id==1
		keep persnr seeking1_total seeking1_tot_dur seeking1_m_dur
	}
	
	tempfile seeking1
	save `seeking1'
restore

merge m:1 persnr using `seeking1'
drop _merge

foreach v of varlist seeking1_total seeking1_total seeking1_tot_dur seeking1_m_dur {
recode  `v' (.=0)
}


********************************************************************************
* 	2.3 Benefit history (LeH, LHG)
********************************************************************************


********************************************************************************
*** 2.3.1 LHG benefit receipt (ALG2): Number of receipts and (total/ mean) duration
* überprüfen, for BeH hat es nicht geklappt

preserve
	* Drop "current" spells
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP==1 
	
	keep if lhgspell==1 // keep only LHG/ ALG2 spells
	
	* Check whether observations
	quietly count if !missing(persnr)
	if `r(N)' > 0 {
	
		//LHG/ ALG2 Receipt (ieb_erw_stat further differs between spells: 1voll_erw 2mind_erw 5 rent_erw)
		bysort persnr: egen LHG_total				= max(anz_lst_lhg_kum)
		bysort persnr: egen LHG_tot_dur				= max(tage_lst_lhg_kum)
		bysort persnr: gen LHG_m_dur				= LHG_tot_dur/LHG_total
				
		by persnr: gen id = _n
		keep if id==1			
		keep persnr LHG_total LHG_tot_dur LHG_m_dur
	}
	
	tempfile ALG2_spells
	save `ALG2_spells'
restore

merge m:1 persnr using `ALG2_spells'
drop _merge

foreach v of varlist LHG_total LHG_tot_dur LHG_m_dur {
recode  `v' (.=0)
}

********************************************************************************
*** 2.3.2 LeH benefit receipt (ALG): Number of receipts and (total/ mean) duration
* überprüfen, for BeH hat es nicht geklappt

preserve
	* Drop "current" spells
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP==1 
	
	keep if lehspell==1 	//keep only LEH spells
	
		* Check whether observations
	quietly count if !missing(persnr)
	if `r(N)' > 0 {
	
		//LEH Spells (Ieb_erw_stat further differs between spells: 1ALG1 2ALHI 3UHG 5PFL)
		bysort persnr: egen LEH_total				= max(anz_lst_leh_kum)
		bysort persnr: egen LEH_tot_dur				= max(tage_lst_leh_kum)
		bysort persnr: gen LEH_m_dur				= LEH_tot_dur/LEH_total
						
		by persnr: gen id = _n
		keep if id==1
		keep persnr LEH_total LEH_tot_dur LEH_m_dur
	}

	tempfile LEH_spells
	save `LEH_spells'
restore

merge m:1 persnr using `LEH_spells'
drop _merge

foreach v of varlist LEH_total LEH_tot_dur LEH_m_dur {
recode  `v' (.=0)
}

********************************************************************************
*	 2.4 ALMP history       
********************************************************************************

********************************************************************************
*** 2.4.1 Number and duration of ALMP measures 

preserve
	* Drop "current" spells
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP==1 
	
	keep if mthspell==1 //keep only ALMP spells
	//there are more than one spell with same start and end dates... I only keep one spell that covers the same period of time
	duplicates drop persnr begorig endorig, force
	
	* Check whether observations
	quietly count if !missing(persnr)
	if `r(N)' > 0 {
	
		* ALMP overall 
		bysort persnr: egen almp_total					= total(mthspell)
		gen almp_dur									= endorig - begorig +1 if mthspell==1
		bysort persnr: egen almp_tot_dur				= total(almp_dur)
		bysort persnr: egen almp_m_dur					= mean(almp_dur)
		
		* ALMP (Aktivierung und Weiterbildung)
		gen almp_aw =1 if  inlist(erwstat, 41)   // Aktivierung und Weiterbilung
		bysort persnr almp_aw: egen almp_aw_total		= total(mthspell) if almp_aw
		bysort persnr almp_aw: egen almp_aw_tot_dur	= total(almp_dur) if almp_aw
		bysort persnr almp_aw: egen almp_aw_m_dur		= mean(almp_dur) if almp_aw
		drop almp_dur
		
		by persnr: gen id = _n
		keep if id==1
		keep persnr almp_total almp_tot_dur almp_m_dur almp_aw_total almp_aw_tot_dur almp_aw_m_dur
	}
	
	tempfile almp
	save `almp'
restore

merge m:1 persnr using `almp'
drop _merge

* Modify missing values
foreach v of varlist almp_total almp_tot_dur almp_m_dur almp_aw_total almp_aw_tot_dur almp_aw_m_dur {
recode  `v' (.=0)
}

********************************************************************************
*** 2.4.2 Total duration of subzidized employments

bysort persnr: egen se_tot_dur				= max(tage_se_kum)

* Modify missing values
foreach v of varlist se_tot_dur {
recode  `v' (.=0)
}


********************************************************************************
* 2.5 Biographical variables           
********************************************************************************

********************************************************************************
*** 2.5.1 Nationality
/*
bysort persnr: egen help1 = min(nation) if !missing(nation)
bysort persnr: egen help2 = max(nation) if !missing(nation)

sum persnr if help1!=help2


**dummy if citizenship has changed in the past
bysort prs_id ieb_staat: gen XX=_n if ieb_staat!=.
bysort prs_id: egen YY=total(XX) if ieb_staat!=. & XX==1
bysort prs_id: egen maxYY=max(YY)
gen chan_citiz =1 if maxYY>1 & maxYY<200
recode chan_citiz (.=0) if maxYY==1
drop XX YY maxYY
label var chan_citiz "citizenship has changed in the past"
*/


** Changed citizienship to German
* Welches sidn hier die zuverlässigsten Spells?
* muss noch überprüft werden!!!!!!

* German citizienship
gen german = deutsch
*replace german = 1 if   relevant_ue ==1  // Germans
*replace german = 0 if   relevant_ue ==1   // non-Germans
replace german = 99999 if   relevant_ue ==1 & missing(deutsch) // unknown
	
preserve
	*gen DROP =1 if begepi == beg_relevant_ue_date
	*drop if DROP==1 
*	keep if inlist(quelle, 7, 18) // Drop "current" spells, keep only (X)ASU spells
	
	bysort persnr deutsch: egen first_G = min(begepi) if deutsch ==1 // date first time flagged as german
	bysort persnr: egen first_N = min(begepi) if !missing(deutsch) // date first time with nationality

	*tab persnr if german ==1 & first_G!= first_N
	gen togerman_help = 1 if first_G!= first_N & german ==1 & relevant_ue ==1 
	by persnr: egen togerman = max(togerman_help)
	
	bysort persnr: gen id =_n
	keep if id==1
	keep persnr togerman
	
	tempfile citizien
	save `citizien'
restore

merge m:1 persnr using `citizien'
drop _merge 


* Modify missing values
foreach v of varlist togerman {
recode  `v' (.z .n .=0)
}


* Label variable german
label define german_label 1"German citizien" 0"Non-german citizien" 99999"Unknown"
label value german german_label

* Drop auxiliary variables
cap drop help1 help2

********************************************************************************
*** 4.2 Current place of residence (in Eastern Germany)

/*tab wo_kreis if relevant_ue==1, m
tab wo_kreis if missing(wo_kreis) & relevant_ue==1, m
tab lastjob_wo_kreis if relevant_ue==1, m */

* Identifier for residence being located in Eastern Germany
gen byte wo_east =.
replace wo_east = 1 if ao_region >= 11000
replace wo_east = 0 if ao_region < 11000 & !missing( ao_region)
replace wo_east = . if missing( ao_region)

label var wo_east "Place of residence in Eastern Germany"

*tab wo_east if relevant_ue==1, m 

* Set missings to unkown
replace wo_east = 99999 if missing(wo_east)
label define wo_east_label 1"Formerly East Germany" 0"West Germany" 99999"Unknown"
label value wo_east wo_east_label


* Adjust missings for variables connected to place or residence
foreach v of varlist  wo_* {
recode  `v' (.z=99999)
}

********************************************************************************
*** 4. Relocated since last contact to labour market/ last job
gen relocated = .
replace relocated = 1 if lastjob_ao_kreis != ao_region & relevant_ue==1
replace relocated = 0 if lastjob_ao_kreis == ao_region & relevant_ue==1

tab relocated if relevant_ue==1, m

* Recode missings to "Unknown"
replace relocated =99999 if missing(relocated)

* Label variable child_imputed 
label define relocated_label 1"Relocated" 0"Did not relocate" 99999"Unknown"
label value relocated relocated_label

********************************************************************************
*** 4.3 How often has a person relocated in the past? 
 
/* Definition of relocation:
 Change in wo_kreis
 */
 
preserve
	gen DROP =1 if begepi == beg_relevant_ue_date
	drop if DROP==1
	
	bysort persnr ao_region: gen help_wo=_n
	keep if help_wo==1
	
	bysort persnr: egen nrWO=total(help_wo) if ao_region!=. & help_wo==1
	bysort persnr: egen moves=max(nrWO)

	replace moves = moves - 1
	label var moves "Number of moves in the past (between different wo_kreis"
	tab moves, mis
	drop help_wo nrWO
	
	by persnr: gen id = _n
	
	keep if id==1
	keep persnr moves
	
	tempfile moves
	save `moves'
restore

merge m:1 persnr using `moves'
drop _merge

* Categorical variable
gen moves_noinfo = 0
replace moves_noinfo = 1 if missing(moves)

replace moves = 0 if missing(moves)

 /*
****************************************F****************************************
*** 4.4 Age

tab age if relevant_ue==1

********************************************************************************
*** 4.5 Marriage status
* Imputatition?
tab famst quelle, m
tab famst quelle if relevant_ue ==1,m


tab  famst quelle, m
* Recode quelle: 1 married, 0 not married, . unknown, missing
recode famst (1 12 13 = 1) (0 11 14 15 = 0) (16 .n .z =.), gen (famst_recode)
tab  famst_recode if relevant_ue==1,m

* Imputation from parallel spells
recode quelle (2=1) (1=99) (7 18 =3) (16 =2), gen(quelle_h_famst)
gen famst_imputed = famst_recode
sort persnr begepi quelle_h_famst
replace famst_imputed = famst_imputed[_n-1] if persnr == persnr[_n-1] & begepi == begepi[_n-1] & missing(famst_imputed)
tab  famst_imputed if relevant_ue==1, m

* Recode missings to "Unknown"
replace famst_imputed =99999 if missing(famst_imput)

* Label variable child_imputed 
label define famst_imputed_label 1"Married " 0"Not married" 99999"Unknown"
label value famst_imputed famst_imputed_label

* Drop auxiliray variables
sort persnr spell
drop quelle_h_famst

********************************************************************************
*** 4.6 Children

/* Note: For ASU, MTH holds that if missing, then no children in household*/

* Imputation of child info if info is missing and other source available (not older than 1 year)
gen child_imput= kind
replace child_imput =0 if inlist(quelle, 7, 32) & missing(kind)

forvalues i = 1(1)10 {
bysort persnr: gen t_since_`i' = begepi-endepi[_n-`i'] if relevant_ue ==1
}

forvalues i = 1(1)10 {
replace child_imput = kind[_n-`i'] if missing(child_imput) & t_since_`i' <=365 & relevant_ue ==1
}

** Binary variable for having at least one child (child); age, hh???
gen child=.
replace child =0 if kind == 0 & !missing(kind) & relevant_ue ==1 
replace child =1 if kind > 0 & !missing(kind) & relevant_ue ==1

gen child_imputed= child
replace child_imputed =0 if child_imput == 0 & missing(child) & relevant_ue ==1 
replace child_imputed= 1 if child_imput  > 0 & missing(child)  & !missing(child_imput) & relevant_ue ==1
replace child_imputed= 1 if child_imput==100 

* Recode missings to "Unknown"
replace child_imputed =99999 if missing(child_imput)

* Label variable child_imputed 
label define child_imputed_label 1"Child 1+ " 0"No children" 99999"Unknown"
label value child_imputed child_imputed_label

* Drop auxiliary variables
drop child_imput

forvalues i = 1(1)10 {
drop t_since_`i' 
}
*/
********************************************************************************
*** 4.7 Other biographical variables

* Adjust missings
foreach v of varlist ausbildung_imp relocated deutsch frau {
recode  `v' (.n . .z = 99999) 
}

********************************************************************************
*	2.6 Current unemployment episode: Job seeking characteristics
********************************************************************************

********************************************************************************
* Profil 

* impute?


