*------------------------------------------------------------------------------------------------*
 *                                MASTER DO-FILE SIAB DATA PREPARATION
*------------------------------------------------------------------------------------------------*


/***********************************************************************\
|    Authors:         Hannah Mautner             						|
|    Date:            20180507                                       	|
|    SIAB version:    7514 v1                                           |
|                                                                       |
\***********************************************************************/

*------------------------------------*
* STATA VERSION

version 15
clear
set more off
set linesize 157


*------------------------------------*
* MACROS FOR PATHS 

global log  "/Users/ruben/Downloads/FinaleVersionUnterlagen/log"     					/// folder of the log-files
global orig "/Users/ruben/Downloads/FinaleVersionUnterlagen/orig/siab_r_7517_v1_stata/"    	/// folder of the basic data
global data "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/"    				/// folder of the generated data
global prog "/Users/ruben/Downloads/FinaleVersionUnterlagen/prog Stata/"    				/// folder of the do-files

*------------------------------------*
* MACROS FOR DATE
global date "20180706_samp"

*------------------------------------*
* MACROS FOR FILENAMES         

global dataname "siab_r_7517_v1"
global logname "siab_7514_v1_prep"

* Read in SIAB data
clear
use "/Users/ruben/Downloads/FinaleVersionUnterlagen/orig/siab_r_7517_v1_stata/siab_r_7517_v1.dta", replace

* use 5-percent sample of SIAB data
*use ${data}siab_7514_v1_5percent_sample.dta, clear
cap drop _merge


*------------------------------------------------------------------------------------------------
* 1 Identification of job seeking episodes and long-term unemployment/ job seeking
* Author: Hannah Mautner
*------------------------------------------------------------------------------------------------

do "/Users/ruben/Downloads/FinaleVersionUnterlagen/prog Stata/01_Identify_unemployment_Mautner.do"

*------------------------------------------------------------------------------------------------
* 2 CREATION OF BIOGRPAHICAL VARIABLES 
* Authors: Hannah Mautner, some variables are based on Eberle & Schmucker 2017
*------------------------------------------------------------------------------------------------    

do  "/Users/ruben/Downloads/FinaleVersionUnterlagen/prog Stata/02_SIAB_bio_Mautner.do"

*------------------------------------------------------------------------------------------------*
* 3 FURTHER DATA PREPARATION 
* Authors: Modified versions of Dauth & Eppelsheimer, forthcoming
*------------------------------------------------------------------------------------------------*

*use ${data}/${dataname}_sample_bio_HM_${date}.dta, clear

* merge BHP data
 do  "/Users/ruben/Downloads/FinaleVersionUnterlagen/prog Stata/03a_Establishment_info_20180515_Mautner.do" // Note: Establishments that could not be merged are dropped in Do-file

* Generate 1-digit industry variable based on 3-digit industries (w93_3_gen): destatis and IAB approach
 do "/Users/ruben/Downloads/FinaleVersionUnterlagen/prog Stata/03b_industries_1digit_destatis_Mautner.do"
 do "/Users/ruben/Downloads/FinaleVersionUnterlagen/prog Stata/03c_industries_1digit_iab_Mautner.do"
 
 * Blossfeld occupation
 do "/Users/ruben/Downloads/FinaleVersionUnterlagen/prog Stata/03d_occ_blossfeld_Mautner.do"
 

* Imputation of education
 do "/Users/ruben/Downloads/FinaleVersionUnterlagen/prog Stata/03e_educ_imputation_HM_Mautner.do"

 the 
* Wages deflation
 do "/Users/ruben/Downloads/FinaleVersionUnterlagen/prog Stata/03f_wages_deflation_Mautner.do"
 
 
save "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/beforereshaping.dta", replace

*------------------------------------------------------------------------------------------------
* 04 CREATION OF VARIABLES FOR SUPERVISED LEARNING MODELS
* Authors: Hannah Mautner
*------------------------------------------------------------------------------------------------    

use "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/beforereshaping.dta", replace

*------------------------------------*
* 	Index entries into unemployment 
do "/Users/ruben/Downloads/FinaleVersionUnterlagen/prog Stata/04_Index_entries_Mautner.do"

*------------------------------------*
*	Save data
save "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/beforeloop.dta", replace
use "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/beforeloop.dta", replace
*------------------------------------*
* 	Loop over entries into unemployment and generate variables for employment history
	foreach i of numlist 1/15{
		display `i'
		 
		if `i' !=1{
			use "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/beforeloop.dta", clear // Get raw data
		}
		
		* Tag unemployment entry relevant for this iteration
		gen relevant_ue =. 
		replace relevant_ue =1 if nrEntry ==`i'
		bysort persnr: egen ue_pop=max(relevant_ue) // Tag all inividuals with relevant entry
		drop if ue_pop !=1 // Keep only individuals with (at least) one entry into unemployment
		
		* Generate employment history for relevant entry
		do "/Users/ruben/Downloads/FinaleVersionUnterlagen/prog Stata/05_Employment_history_Mautner.do"
			
		* Save before reshaping data for entry i
		compress
		save "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/beforedropping`i'.dta", replace
		
		do "/Users/ruben/Downloads/FinaleVersionUnterlagen/prog Stata/06_Reshape_data_Mautner.do" // Reshape data: Drop variables and spells not necessary for models
			
		* Save reshaped data for entry i
		compress 
		save "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/ready_entry`i'.dta", replace
}

*------------------------------------*
* 	Append data for all entries
	
use "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/ready_entry1.dta", clear

foreach i of numlist 2/15{
	append using "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/ready_entry`i'.dta"
	}


*------------------------------------------------------------------------------------------------*
* 06 RESHAPE DATA AND DROP VARIABLES NOT NEEDED FOR SUPERVISED LEARNING MODELS
* Author: Hannah Mautner
*------------------------------------------------------------------------------------------------*
/*
use ${data}/${dataname}_forR_${date}.dta, clear
do ${prog}06_Reshape_data_Mautner.do
*/
*------------------------------------------------------------------------------------------------*
* Save final data set
*------------------------------------------------------------------------------------------------*

compress
save "/Users/ruben/Downloads/FinaleVersionUnterlagen/data/_forR.dta", replace




log close
exit
