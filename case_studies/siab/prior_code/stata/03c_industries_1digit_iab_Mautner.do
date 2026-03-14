*cap log close
*log using ${folderLog}\03b_industries_1digit_iab.log, replace


/*
	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
	
	SIAB Preparation
	
	Generate 1-digit industry variable based on 3-digit industries (w93_3_gen)
	Mapping based IAB establishment panel
	w93_3_gen is already coded time-consistent (see Eberle et al. 2014)
	
	Generates the variable:
		- industry1_estpanel: Industry; 1-digit; IAB establishment panel; based on w93_3_gen
	
	Author(s): Wolfgang Dauth, Johann Eppelsheimer
	
	Version: 1.0
	Last Update: 2018-04-03
	Created: 2018-04-03
	
	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
	
	
	Reference:
		
	Eberle et al., 2014:
		Eberle, J., P. Jacobebbinghaus, J. Ludsteck, and J. Witter (2014).
		Generation of timeconsistent industry codes in the face of classification changes
		Institute of Employment Research, Nuremberg. FDZ-Methodenreport 05/2011
	
*/
/*

********************************************************************************
* Map 3-digit industries to 1-digit industries
********************************************************************************
gen industry1_estpanel=.


*** Group 1 ***
* Agriculture, hunting and forestry, fishing
* Land- und Forstwirtschaft, Fischerei
replace industry1_estpanel=1 if w93_3>=11 & w93_3<=50
* Mining and quarrying, electricity, gas and water supply, recycling
* Bergbau und Gewinnung von Steinen und Erden, Energie und Wasserversorgung; Abwasser- und Abfallentsorgung
replace industry1_estpanel=1 if (w93_3>=101 & w93_3<=145) | (w93_3>=371 & w93_3<=410) | w93_3==900

*** Group 2 ***
* Manufacture of food products beverages and tobacco
* Nahrungs- und Genussmittel
replace industry1_estpanel=2 if w93_3>=151 & w93_3<=160

*** Group 3 ***
* Manufacture of consumer products (not including manufacture of wood products)
* Verbrauchsgueter
replace industry1_estpanel=3 if (w93_3>=171 & w93_3<=193) | (w93_3>=221 & w93_3<=223) | (w93_3>=361 & w93_3<=366)

*** Group 4 ***
* Manufacture of industrial goods 
* Produktionsgueter
replace industry1_estpanel=4 if (w93_3>=201 & w93_3<=212) | (w93_3>=231 & w93_3<=287)

*** Group 5 ***
* Manufacture of capital and consumer goods
* Investitions- und Gebrauchsgueter
replace industry1_estpanel=5 if w93_3>=291 & w93_3<=355

*** Group 6 ***
* Construction
* Baugewerbe
replace industry1_estpanel=6 if w93_3>=451 & w93_3<=455
* Hotels and restaurants
* Gastgewerbe
replace industry1_estpanel=7 if w93_3>=551 & w93_3<=555
* Other services
* Sonstige Dienstleistungen - personennah	
replace industry1_estpanel=7 if w93_3>=921 & w93_3<=930

*** Group 7 ***
* Trade, maintenance and repair of motor vehicles, motor
* Handel, Instandhaltung und Reparatur von Kraftfahrzeugen
replace industry1_estpanel=7 if w93_3>=501 & w93_3<=527
* Other services
* Sonstige Dienstleistungen - unternehmensnah
replace industry1_estpanel=8 if w93_3>=745 & w93_3<=748

*** Group 8 ***
* Transport, storage
* Verkehr und Lagerei
replace industry1_estpanel=8 if w93_3>=601 & w93_3<=634
* Information and communication
* Information und Kommunikation
replace industry1_estpanel=8 if w93_3>=641 & w93_3<=642
* Financial intermediation, insurance
* Finanz- und Versicherungsdienstleistungen
replace industry1_estpanel=8 if w93_3>=651 & w93_3<=672
* Real estate
* Grundstücke
replace industry1_estpanel=8 if w93_3>=701 & w93_3<=703
* Renting
* Vermietung
replace industry1_estpanel=8 if w93_3>=711 & w93_3<=714
* IT
replace industry1_estpanel=8 if w93_3>=721 & w93_3<=726
* Liberal professions
* wirtschaftliche, wissenschaftliche und freiberufliche Dienstleistungen
replace industry1_estpanel=8 if w93_3>=731 & w93_3<=744

*** Group 9 ***
* Education
* Erziehung und Unterricht
replace industry1_estpanel=9 if w93_3>=801 & w93_3<=804
* Health and social work
* Gesundheits- und Sozialwesen
replace industry1_estpanel=9 if w93_3>=851 & w93_3<=853
* Non-industrial organizations
* Interessenvertretungen
replace industry1_estpanel=9 if w93_3>=911 & w93_3<=913
* Public administration
* Öffentliche Verwaltung, Verteidigung, Sozialversicherung
replace industry1_estpanel=9 if w93_3>=751 & w93_3<=753



********************************************************************************
* Label
********************************************************************************
label variable industry1_estpanel "Industry; 1-digit; IAB establishment panel; based on w93_3_gen"



********************************************************************************
* Overview of mapping
********************************************************************************
tab w93_3_gen industry1_estpanel


*/
*log close
