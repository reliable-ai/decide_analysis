*cap log close
*log using ${folderLog}\05_educ_imputation.log, replace


/*
	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
	
	SIAB Preparation
	
	Imputation of the education variable 'ausbildung'
	Based on Fitzenberger, Osikominu & Voelter (2008) (Imputation Procedure 1): http://doku.iab.de/fdz/reporte/2005/MR_3.pdf
	
	Generates the variables:
		- ausbildung_imp: Education imputed based on Fitzenberger, Osikominu & Voelter (2008)
		- educ: Education (university and university of applied science combined), imputed based on Fitzenberger, Osikominu & Voelter (2008)
	
	
	Author(s): Wolfgang Dauth, Johann Eppelsheimer
	
	Version: 1.0
	Last Update: 2018-04-03
	Created: 2018-04-03
	
	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~




********************************************************************************
* Education before imputation
********************************************************************************
tab ausbildung quelle, m


********************************************************************************
* Generate new education variable (ausbildung_imp)
********************************************************************************
gen ausbildung_imp = ausbildung


********************************************************************************
* Translate ASU, XASU and MTH Ausbildung into BeH Ausbildung
********************************************************************************
replace ausbildung_imp = 11 if ausbildung_imp == 5			// FH --> FH
replace ausbildung_imp = 12 if ausbildung_imp == 6			// Uni --> Uni
replace ausbildung_imp = 2  if inlist(ausbildung_imp, 3, 4)	// Berufsfachschule, Fachschule --> betr./außerbetr. Ausbildung
replace ausbildung_imp = 1  if inlist(ausbildung_imp, 7, 8)	// nicht anerkannt ausl. Ausb./Uni --> ohne Ausbildung

tab ausbildung ausbildung_imp, m
tab ausbildung_imp quelle, m


********************************************************************************
* Replace missings by 0 (lowest value of ausbildung_imp)
********************************************************************************
* warum? 
replace ausbildung_imp = 0 if missing(ausbildung_imp)


********************************************************************************
* Take the highest value of ausbildung if there are parallel spells
********************************************************************************
bysort persnr begepi: egen ausbildung_max = max(ausbildung_imp)
replace ausbildung_imp = ausbildung_max if ausbildung_imp < ausbildung_max
drop ausbildung_max


********************************************************************************
* Step 1: no educational degree if age < 18
********************************************************************************
replace ausbildung_imp = 1 if age < 18
* wirklich?


********************************************************************************
* Step 2: forward extrapolation
********************************************************************************

* sort spells
gsort persnr begepi quelle 
*-tage_job

* actual forward extrapolation
* selbes Vorgehen wie Hans?
by persnr : replace ausbildung_imp = ausbildung_imp[_n-1] if ausbildung_imp[_n-1] > ausbildung_imp & _n > 1

* education after forward extrapolation
* soll ich diese Altersgrenze verwenden?
tab ausbildung_imp ausbildung, m
count if ausbildung == 2  & ausbildung_imp == 1 & age < 18		// downgrades are due to age
count if ausbildung == 11 & ausbildung_imp == 1 & age < 18		// downgrades are due to age
count if ausbildung == 12 & ausbildung_imp == 1 & age < 18		// downgrades are due to age

tab ausbildung_imp quelle, m



********************************************************************************
* Step 3: backward extrapolation
********************************************************************************

/*
	Comment:
	
	Fitzenberger, Osikominu & Voelter (2005) suggest the following age limits for the backward extrapolation:
	
		- vocational training (Ausbildung): 20
		- degree from university of applied science (FH): 27
		- university degree: 29
		
*/


* reversed sorting
gsort persnr -begepi -quelle 
*tage_job

* actual backward extrapolation (commands have to be sorted by age limits for each level of education!)
by persnr: replace ausbildung_imp = 1  if ausbildung_imp[_n-1] == 1  & ausbildung_imp == 0 & _n > 1
by persnr: replace ausbildung_imp = 2  if ausbildung_imp[_n-1] == 2  & ausbildung_imp == 0 & age >= 20 & !inlist(erwstat, 102, 121, 122, 141) & _n > 1	// exclude workers in vocational training
by persnr: replace ausbildung_imp = 11 if ausbildung_imp[_n-1] == 11 & ausbildung_imp == 0 & age >= 27 & _n > 1
by persnr: replace ausbildung_imp = 12 if ausbildung_imp[_n-1] == 12 & ausbildung_imp == 0 & age >= 29 & _n > 1

* set missings (0) as missings
replace ausbildung_imp = . if ausbildung_imp == 0

* return to standard sorting
gsort persnr begepi quelle -tage_job

* Education after backward extrapolation
tab ausbildung_imp ausbildung, m
tab ausbildung_imp quelle, m


********************************************************************************
* Step 4: additional adjustments
********************************************************************************

/*
	Comment:
	
	Fitzenberger, Osikominu & Voelter (2005) suggest some additional adjustments.
	In particular they replace "no education" by "vocational training" if workers 
	are in certain employment status.

	Because the necessary variable "stib" does no longer exist in the current SIAB 
	this additional adjustment is ommited.
	
	A workaround could be to use the variable "nievau" instead. However depending
	on the research question this might be problematic. Hence, it is left to the
	user to implement (or not implement) such a workaround.
	
*/




********************************************************************************
* Generate a more general education variable (educ)
********************************************************************************
gen educ = .
replace educ = 3 if ausbildung_imp == 11 | ausbildung_imp == 12	// degree from an university or university of applied science (Uni or FH)
replace educ = 2 if ausbildung_imp == 2							// vocational training (Ausbildung)
replace educ = 1 if ausbildung_imp == 1							// neither vocational training or degree from universtiy (of applied science)


********************************************************************************
* Labels
********************************************************************************
label variable ausbildung_imp "Ausbildung, imputed based on Fitzenberger, Osikominu & Voelter (2008)"
label variable educ "Education, imputed based on Fitzenberger, Osikominu & Voelter (2008)"

label values ausbildung_imp ausbildung_en

label define lblValEduc 1 "1 no vocational training" 2 "2 vocational training" 3 "3 university or university of applied science"
label values educ lblValEduc



********************************************************************************
* Comparision: original education & imputed education
********************************************************************************
tab ausbildung_imp ausbildung, m
tab educ ausbildung, m
tab educ ausbildung_imp, m
tab ausbildung_imp
tab educ
*/
tab ausbildung_imp


*log close
