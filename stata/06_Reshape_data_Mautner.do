

 
 
********************************************************************************
* 3 Response/ Outcome variable      
********************************************************************************
** Ruben's edits
** impute missing spells with max of non missing spells within same person
tab deutsch, mis
recode deutsch (99999=-1) (.a = -2)
tab deutsch, mis
bysort persnr: egen maxdeutsch = max(deutsch)
tab maxdeutsch, mis

tab ausbildung_imp, mis
recode ausbildung_imp (99999=-1)
tab ausbildung_imp, mis
bysort persnr: egen maxausbildung_imp = max(ausbildung_imp)
tab maxausbildung_imp, mis

tab schule, mis
recode schule (.n=-1) (.z=-2)
tab schule, mis
bysort persnr: egen maxschule = max(schule)
tab maxschule, mis

tab niveau, mis
recode niveau (.n=-1) (.z=-2)
tab niveau, mis
bysort persnr: egen maxniveau = max(niveau)
tab maxniveau, mis

tab ao_re

gen bula = 1 if ao_reg <2000 & !missing(ao_re)
replace bula = 2 if ao_reg >=2000 & ao_reg<3000
replace bula = 3 if ao_reg >=3000 & ao_reg<4000
replace bula = 4 if ao_reg >=4000 & ao_reg<5000
replace bula = 5 if ao_reg >=5000 & ao_reg<6000
replace bula = 6 if ao_reg >=6000 & ao_reg<7000
replace bula = 7 if ao_reg >=7000 & ao_reg<8000
replace bula = 8 if ao_reg >=8000 & ao_reg<9000
replace bula = 9 if ao_reg >=9000 & ao_reg<10000
replace bula = 10 if ao_reg >=10000 & ao_reg<11000
replace bula = 11 if ao_reg >=11000 & ao_reg<12000
replace bula = 12 if ao_reg >=12000 & ao_reg<13000
replace bula = 13 if ao_reg >=13000 & ao_reg<14000
replace bula = 14 if ao_reg >=14000 & ao_reg<15000
replace bula = 15 if ao_reg >=15000 & ao_reg<16000
replace bula = 16 if ao_reg >=16000 & !missing(ao_re)
tab bula, mis

preserve
	keep if !missing(bula)
	sort persnr begepi
	bysort persnr: keep if _n == _N
	rename bula maxbula
	keep persnr maxbula
	tempfile BULA
	save `BULA'
restore

merge m:1 persnr using `BULA'
cap drop _merge
tab maxbula, mis

tab pendler, mis
recode pendler (.n=-1) (.z=-2)
tab pendler, mis
preserve
	keep if pendler>0
	sort persnr begepi
	bysort persnr: keep if _n == _N
	rename pendler maxpendler
	keep persnr maxpendler
	tempfile PEND
	save `PEND'
restore 
merge m:1 persnr using `PEND'
cap drop _merge

tab w08_gen_gr, mis
recode w08_gen_gr (.n=-1) (.z=-2)
tab w08_gen_gr, mis
preserve
	keep if w08_gen_gr>0
	sort persnr begepi
	bysort persnr: keep if _n == _N
	rename w08_gen_gr lastw08_gen_gr
	keep persnr lastw08_gen_gr
	tempfile W08
	save `W08'
restore 
merge m:1 persnr using `W08'
cap drop _merge
tab lastw08_gen_gr, mis



* Drop all spells that are not entry to unemployment spells 
keep if relevant_ue==1

global response "ltue"
label define ltue_label 0"Not_LTUE" 1"LTUE"
label value ltue ltue_label

********************************************************************************
* 7 Label variables        
********************************************************************************

label variable maxdeutsch "most recent nationality, neg.value=mis"
label variable maxausbildung_imp "most recent education, neg.value=mis"
label variable maxschule "most recent school education, neg.value=mis"
label variable maxniveau "most recent niveau of job, neg.value=mis"
label variable maxbula "most recent Bundesland"
label variable maxpendler "most recent commute"
label variable lastw08_gen_gr "most recent sector"

foreach v of varlist maxdeutsch - lastw08_gen_gr {
	tab `v', mis
}


********************************************************************************
* 	Status right before entry into unemployment (ASu spell), during 6 weeks before entry
global status_before "employed_before  receipt_leh_before receipt_lhg_before se_before ASU_notue_seeking_before ASU_other_before break_before"

label var employed_before 					"Any employment in 6 weeks before entry to unemployment"
label var receipt_leh_before 				"LeH receipt in 6 weeks before entry to unemployment"
label var receipt_lhg_before 				"LHG receipt in 6 weeks before entry to unemployment"
label var se_before 						"Any subsidized employment in 6 weeks before entry to unemployment"
label var ASU_notue_seeking_before 			"Registered as job seeking/ not UE in 6 weeks before entry to unemployment"
label var ASU_other_before 					"Registered with ASU register for other reason in 6 weeks before entry to unemployment"
label var break_before 						"No info about 6 weeks prior to entry to unemployment"

********************************************************************************
*	Employment history

*** Last contact to labour market
global lastcontact_lm "tsince_ein_erw1 tsince_ein_erw1_cat tsince_ft_lm_contact tsince_lm_contact tsince_lm_contact_cat tsince_ft_lm_contact_cat"

label var  tsince_ein_erw1 					"Days since employment"
label var  tsince_ein_erw1_cat 				"Days since employment (categorized)"
label var  tsince_lm_contact 				"Days since last labour market contact"
label var  tsince_lm_contact_cat 			"Days since last labour market contact (cat.)"
label var  tsince_ft_lm_contact_cat			"Days since last labour market contact (full-time) (cat.)"
label var  tsince_ft_lm_contact 			"Days since last labour market contact (full-time)"


*** Overall employment history
global emp_total "emp_total est_total emp1_total emp1_total_dur emp2_total_dur emp3_total_dur emp1_m_dur main_industry industry1_destatis_tot_dur_* secjob_tot_dur minijob_tot_dur ft_tot_dur befrist_tot_dur leih_tot_dur"

label var emp_total 						"No. seperate jobsa/employments"
label var est_total 						"No. different establishmets worked in "
label var emp1_total						"No. seperate jobs/employments (w/o voc. training)"			
label var main_industry 					"Industry the person worked in longest" 
*label var industry1_destatis_tot_dur_*		"Duration worked in industry (destatis)"
label var emp1_total_dur 					"Tot. duration in employment (w/o voc. training)"
label var emp2_total_dur 					"Tot. duration in employment (w/o voc. training, ?)"
label var emp3_total_dur 					"Tot. duration in employment (w/o voc. training, ?)"
label var emp1_m_dur						"Mean duration of jobs/employment (w/o voc. training)"

label var minijob_tot_dur					"Tot. duration in marginal employment"
label var secjob_tot_dur 					"Tot. duration more than one job"
label var ft_tot_dur						"Tot. duration  in full-time employment"
label var befrist_tot_dur 					"Tot. duration more than one job"
label var leih_tot_dur						"Tot. duration  in full-time employment"

* Characteristics of last job 
global lastjob "lastjob_none lastjob_tot_dur lastjob_parallel lastjob_type lastjob_pt lastjob_wage_defl lastjob_occblo lastjob_niveau lastjob_leih lastjob_befrist lastjob_educ  lastjob_ao_kreis  lastjob_industry_destatis  "
global lastjob_noinfo "lastjob_type_noinfo lastjob_parallel_noinfo lastjob_pt_noinfo lastjob_occblo_noinfo lastjob_niveau_noinfo lastjob_leih_noinfo lastjob_befrist_noinfo  lastjob_educ_noinfo  lastjob_ao_kreis_noinfo  lastjob_industry_destatis_noinfo " 

label var lastjob_none						"No info about previous jobs available"
label var lastjob_tot_dur					"Duration of last job"
label var lastjob_parallel 					"Parallel job(s) during last job"
label var lastjob_type 						"Type of last job"
label var lastjob_pt 						"Last job was part-time"
label var lastjob_wage_defl 				"Deflated daily wage of last job"
label var lastjob_occblo 					"Occupation in last job"
label var lastjob_niveau 					"Niveau of last job"
label var lastjob_leih 						"Leiharbeit status of last job regarding "
label var lastjob_befrist 					"Short-term status of last job"
* label var lastjob_wo_kreis 					"Residence location during last job"
*label var lastjob_wo_bula 					"Residence state during last job"
label var lastjob_educ 						"Education status during last job"
*label var lastjob_e_east 					"Establishment of last job in Eastern Germany"
label var lastjob_ao_kreis 					"Working location during last job"

*label var lastjob_ao_bula					"Working state during last job"
*label var lastjob_e_size					"No. employees last establishment"
label var lastjob_industry_destatis 		"Industry of last establishment (Destatis)"
*label var lastjob_industry_iab 				"Industry of last establishment (IAB)"
*label var lastjob_e_tsince_start 			"Days the establishment existed (last job)"
*label var lastjob_communting 				"Commuted to last job (different locations WO and AO)"
*label var lastjob_art_kuend					"Reason for termination of last job" 

********************************************************************************
* 	Benefit history
global benefit_hist "LHG_total LHG_tot_dur LHG_m_dur LEH_total LEH_tot_dur LEH_m_dur"

label var LHG_total							"No of times of ALG2 receipt"
label var LHG_tot_dur 						"Total duration of ALG2 receipt"
label var LHG_m_dur							"Mean duration of ALG2 receipt"	

label var LEH_total							"No of times of LEH"
label var LEH_tot_dur 						"Total duration of LEH"
label var LEH_m_dur							"Mean duration of LEH"

********************************************************************************
* 	ALMP history
global almp_hist "almp_total almp_tot_dur almp_m_dur almp_aw_total almp_aw_tot_dur	almp_aw_m_dur se_tot_dur"

label var almp_total 						"No. of participations in ALMPs"
label var almp_tot_dur						"Tot. duration of ALMPs"
label var almp_m_dur						"Mean duration of ALMPs"

label var almp_aw_total 					"No of participations in ALMP (A&W)"
label var almp_aw_tot_dur					"Total duration of ALMP (A&W)"
label var almp_aw_m_dur						"Mean duration of ALMP (A&W)"

label var se_tot_dur						"Tot. duration of subzidized employments"

********************************************************************************
* 	ASU history
global seeking_hist "tsince_lastseeking tsince_lastseeking_cat seeking1_total seeking1_tot_dur seeking1_m_dur"

label var tsince_lastseeking 				"Time since last unemployed/ job seeking-spell"
label var seeking1_total 					"No. seperate unemployed/ job seeking-spells"
label var seeking1_tot_dur					"Total duration of unemployed/ job seeking episodes"
label var seeking1_m_dur					"mean duration of unemployed/ job seeking episodes"


********************************************************************************
* 	Biographical variables
global bio "age frau   german ausbildung_imp togerman moves moves_noinfo relocated wo_east"
global bio_imputed "age frau  ausbildung_imp german togerman moves moves_noinfo relocated wo_east"

label var age								"Age"
*label var child								"Having children (under the age of 15 resp. 16)"
*label var child_imputed						"Having children (under the age of 15 resp. 16) (Imputed)"
label var german							"German nationality"
label var togerman							"Has changed nationality to German"
label var moves								"No. of private relocations between Kreise"
label var relocated							"Changed residence location since last job"
label var wo_east							"Current location residence in eastern Germany"
*label var famst								"Marriage status"
*label var famst_imputed						"Marriage status (imputed)"
label var age								"Age at entry to unemployment"	

/* Add. variables:
frau 
nation_gr
wo_kreis
wo_bula
wo_aa
wo_rd
educ
*/	


********************************************************************************
*	Current unemployment episode: Job seeking characteristics
global current_seeking " niveau"

*label var arbzeit							"(Preferred) Hours of searched job"
*label var traeger							"Träger ASU"
label var niveau							"Niveau of "

* Profiling
global profil "profil"

********************************************************************************
* 8 Drop variables that are no longer needed       
********************************************************************************

* Spell variables
global spell_original "persnr year quelle_gr begepi endepi  alo_dau "
global spell_generated "ue_pop nrEntry beg_ue ue_duration"

keep  ${spell_original} ${spell_generated} ${response} ${status_before} ${lastcontact_lm} ${emp_total} ${lastjob} ${lastjob_noinfo} ${benefit_hist} ${almp_hist} ${seeking_hist} ${bio} ${bio_imputed} ${current_seeking} maxausbildung_imp maxdeutsch maxbula maxniveau maxschule maxpendler lastw08_gen_gr
order ${spell_original} ${spell_generated} ${response}  ${status_before} ${lastcontact_lm} ${emp_total} ${lastjob} ${lastjob_noinfo} ${benefit_hist} ${almp_hist} ${seeking_hist} ${bio} ${bio_imputed} ${current_seeking} 



