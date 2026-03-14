* keepusing(az_ges az_vz az_gf ao_kreis)

/*
// add establishment level info
rename year jahr
merge m:1 betnr jahr ///
 using ${orig}SIAB_7514_v1_bhp_basis_v1, ///
 
 
keep if inlist(_merge, 1, 3) | quelle > 1
rename jahr year


* Establishments that could not be merged
drop if _merge ==2

// establishments that could not be merged must have no employment
// at the relevant cutoff data 
replace az_ges = 0 if az_ges >=.
replace az_vz = 0 if az_vz >=.
replace az_gf = 0 if az_gf >=.

* Identifier for establishment being located in Eastern Germany
gen byte Ieast = ao_kreis >= 11000
tabulate Ieast
label var Ieast "Establishment in Eastern Germany"


* change language of labels
label language en

drop _merge 
*/
