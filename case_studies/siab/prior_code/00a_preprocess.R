##########################################################################################
#   00 Data Preparations
#
#   Authors: Hannah Mautner, Ruben Bach, Christoph Kern
#
##########################################################################################

library(tidyverse)
library(haven)

siab_orig_full <- read_dta("_forR.dta")

##########################################################################################
# 1 Gen data set with all variables relevant for analysis:  siab

# 1.1 Exclude variables only relevant for summary statistics, irrelevant for models
# Note: Identifiers are still in data set: "nrEntry", "persnr"; Exclude when fitting models!
# exclude all last_job-variables exept lastjob_none

drop <- c( "quelle_gr", "begepi", "endepi", "alo_beg", "ue_pop", "beg_ue",
           "tsince_ein_erw1", "tsince_lm_contact", "tsince_ft_lm_contact", "tsince_lastseeking",
           "lastjob_occblo", "lastjob_ao_kreis",
           "lastjob_type_noinfo", "lastjob_occblo_noinfo", "lastjob_leih_noinfo", "lastjob_parallel_noinfo" ,
           "lastjob_industry_iab_noinfo", "lastjob_e_east_noinfo", "lastjob_communting_noinfo",
           "lastjob_ao_bula_noinfo", "lastjob_ao_kreis_noinfo", "lastjob_wo_bula_noinfo",
           "lastjob_educ_noinfo", "lastjob_wo_kreis_noinfo", "lastjob_niveau_noinfo",
           "lastjob_befrist_noinfo", "lastjob_industry_destatis_noinfo", "lastjob_e_tsince_start_noinfo",
           "lastjob_pt_noinfo", "lastjob_type2", "moves_noinfo")
siab<-siab_orig_full[,!(names(siab_orig_full) %in% drop)]

# Drop unused/ duplicates/ zero variance variables

drop <- c("alo_dau", "ue_duration",
          "emp_total", "emp2_total_dur", "emp3_total_dur", # high corrs
          "ausbildung_imp", "togerman", "relocated", "wo_east", "niveau",
          "german", # same as maxdeutsch
          "lastw08_gen_gr", # high corr with lastjob_industry_destatis
          "lastjob_educ") # high corr with maxausbildung_imp
siab <- siab[,!(names(siab) %in% drop)]

glimpse(siab)
rm(drop, siab_orig_full)

##########################################################################################
# 2 Pre-processing the data
##########################################################################################
# 2.1 Convert categorical variables to factors

glimpse(siab$ltue)
table(siab$ltue)

list_factor <- c("main_industry",
                 "tsince_ein_erw1_cat", "tsince_lm_contact_cat", "tsince_ft_lm_contact_cat", "tsince_lastseeking_cat",
                 "lastjob_type", "lastjob_pt", "lastjob_niveau",
                 "lastjob_befrist", "lastjob_leih",
                 "lastjob_industry_destatis",
                 "frau",
                 "maxdeutsch", "maxausbildung_imp", "maxschule",
                 "maxniveau", "maxbula", "maxpendler")
for (i in list_factor) {
  print(summary(siab[i]))
}

siab$maxdeutsch <- ifelse(siab$maxdeutsch < 0, NA, siab$maxdeutsch)
siab$maxausbildung_imp <- ifelse(siab$maxausbildung_imp < 0, NA, siab$maxausbildung_imp)
siab$maxschule <- ifelse(siab$maxschule < 0, NA, siab$maxschule)
siab$maxniveau <- ifelse(siab$maxniveau < 0, NA, siab$maxniveau)

newfactors<-lapply(siab[,list_factor], factor)
newfactors<-data.frame(newfactors)
newfactors<-mutate_all(newfactors, fct_explicit_na)
str(newfactors)

siab<-data.frame(c(siab[,!names(siab) %in% list_factor], newfactors))
glimpse(siab)

#############################################
# 2.2 One-hot encode factors

temp <- model.matrix(ltue ~ main_industry +
                       tsince_ein_erw1_cat + tsince_lm_contact_cat + tsince_ft_lm_contact_cat + tsince_lastseeking_cat +
                       lastjob_type + lastjob_pt + lastjob_niveau +
                       lastjob_befrist + lastjob_leih +
                       lastjob_industry_destatis +
                       frau +
                       maxdeutsch + maxausbildung_imp + maxschule +
                       maxniveau + maxbula + maxpendler,
                     data = siab)[,-1]

temp<-as.data.frame(temp)
siab<-data.frame(c(siab[,!names(siab) %in% list_factor], temp))

glimpse(siab)
rm(newfactors, list_factor, temp)

#############################################
# 2.3 Missings
# Note: previously, all missings have been coded to 99999, now there should be no missings in the data

# Are there still missings in the data set?
for (i in names(siab)){
  print(i)
  missing <- sum(is.na(siab[i]))
  if (missing >0) {
    print(missing)
  }
}

# result: "lastjob_tot_dur" has 12 missings, should be 0 when missing
siab$lastjob_tot_dur <- ifelse(is.na(siab$lastjob_tot_dur) ==TRUE, 0, siab$lastjob_tot_dur)
summary(siab$lastjob_tot_dur)

glimpse(siab)
rm(i, missing)

# Create indicator variables for missingness in numeric variables

# Are there missings in the data set?
for (i in names(siab)){
  print(i)
  missing <- sum(siab[i] == 99999)
  if (missing >0) {
    print(missing)
  }
}

siab$lastjob_parallel99999 <- ifelse(siab$lastjob_parallel == 99999, 1, 0)

# Median imputation for missingness in numeric variables

lastjob_mean <- siab %>%
  filter(year < 2016 & lastjob_parallel != 99999) %>%
  summarise(median(lastjob_parallel))

siab$lastjob_parallel <- ifelse(siab$lastjob_parallel == 99999, lastjob_mean[,], siab$lastjob_parallel)

#############################################
# 2.4 Scale duration variables by age

durations <- c("emp1_total_dur", "secjob_tot_dur",
               "minijob_tot_dur", "ft_tot_dur", "befrist_tot_dur", "leih_tot_dur",
               "LHG_tot_dur", "LEH_tot_dur", "almp_tot_dur", "almp_aw_tot_dur",
               "se_tot_dur", "seeking1_tot_dur")
siab[paste(durations,"_byage",sep="")] <- sapply(siab[durations], function(x){
  x/siab["age"]
}
)

glimpse(siab)
rm(durations)

#############################################
# Drop year 2017 (outcome not defined)

by(siab$ltue, siab$year, table)

siab <- siab %>% filter(year < 2017)

#############################################
# Save data

siab <- siab %>% arrange(persnr, year, nrEntry)

save(siab, file = "out/00a_siab.Rdata")

write_csv(siab, file = "out/00a_siab.csv")
