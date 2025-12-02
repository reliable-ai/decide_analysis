import numpy as np
import pandas as pd
import os
from datetime import datetime, timedelta
import random
from config import ORIG_DIR, DATANAME, create_directories

# Create required directories
create_directories()

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

# Define constants
n_individuals = 5000  # Number of unique individuals
max_spells_per_person = 20  # Maximum number of spells per person
n_establishments = 500  # Number of unique establishments


# Generate random dates within a realistic range (2000-2020)
def random_date(start_date="2000-01-01", end_date="2020-12-31"):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    delta = (end - start).days
    random_days = random.randint(0, delta)
    return start + timedelta(days=random_days)


# Function to convert datetime to Stata date
def to_stata_date(date_obj):
    return (date_obj - datetime(1960, 1, 1)).days


# Generate individuals with varying number of spells
individuals = []
for persnr in range(1, n_individuals + 1):
    n_spells = random.randint(1, max_spells_per_person)
    birth_year = random.randint(1950, 2000)

    # Generate employment/unemployment spells for this person
    spells = []
    current_date = random_date("2000-01-01", "2005-01-01")

    for spell_idx in range(1, n_spells + 1):
        # Randomly decide if this is an employment or unemployment spell
        is_employment = random.random() > 0.3

        # Duration of spell (30-365 days)
        spell_duration = timedelta(days=random.randint(30, 365))
        beg_date = current_date
        end_date = beg_date + spell_duration
        current_date = end_date + timedelta(
            days=random.randint(0, 30)
        )  # Gap between spells

        # Generate other attributes based on spell type
        if is_employment:
            erwstat = random.choice([1, 2, 3])  # Employment status codes
            betnr = random.randint(1, n_establishments)
            tentgelt = random.uniform(30, 300)  # Daily wage
            teilzeit = random.choice([0, 1])
            quelle = random.choice([1, 2])
            ausbildung = random.choice([1, 2, 5, 8])
        else:
            erwstat = random.choice([4, 5])  # Unemployment status codes
            betnr = None
            tentgelt = 0
            teilzeit = 0
            quelle = random.choice([3, 4])
            ausbildung = random.choice([1, 2, 5, 8])

        # Industry codes
        w93_3 = random.randint(10, 999)
        w93_3_gen = w93_3
        w08_gen_gr = random.randint(1, 10)

        spell = {
            "persnr": persnr,
            "spell": spell_idx,
            "betnr": betnr,
            "begorig": to_stata_date(beg_date),
            "begepi": to_stata_date(beg_date),
            "endorig": to_stata_date(end_date),
            "endepi": to_stata_date(end_date),
            "tentgelt": tentgelt,
            "teilzeit": teilzeit,
            "erwstat": erwstat,
            "ausbildung": ausbildung,
            "gebjahr": birth_year,
            "quelle": quelle,
            "quelle_gr": quelle,
            "w93_3": w93_3,
            "w93_3_gen": w93_3_gen,
            "w08_gen_gr": w08_gen_gr,
            "w08_gen_gr_de": w08_gen_gr,
            "azubi": 1 if random.random() < 0.1 else 0,
            "intern": 1 if random.random() < 0.05 else 0,
        }

        # Add unemployment-specific variables if this is an unemployment spell
        if not is_employment:
            beg_ue_date = beg_date
            end_ue_date = end_date
            ue_duration = (end_ue_date - beg_ue_date).days

            spell.update(
                {
                    "beg_ue": to_stata_date(beg_ue_date),
                    "end_ue": to_stata_date(end_ue_date),
                    "ue_duration": ue_duration,
                    "beg_ue_date": to_stata_date(beg_ue_date),
                    "end_ue_date": to_stata_date(end_ue_date),
                    "t_since_asu": random.randint(0, 365),
                }
            )

        spells.append(spell)

    individuals.extend(spells)

# Create the main SIAB microdata DataFrame
siab_data = pd.DataFrame(individuals)

# Generate auxiliary variables used in scripts
siab_data["level1"] = siab_data.groupby("persnr").cumcount() + 1
siab_data["level2"] = siab_data.groupby(["persnr", "erwstat"]).cumcount() + 1
siab_data["tage_erw1"] = np.random.randint(0, 3000, size=len(siab_data))
siab_data["tage_erw2"] = np.random.randint(0, 3000, size=len(siab_data))
siab_data["tage_erw3"] = np.random.randint(0, 3000, size=len(siab_data))

# Generate establishment data
years = range(2000, 2021)
establishments = []

for betnr in range(1, n_establishments + 1):
    for year in years:
        # Basic establishment characteristics
        az_ges = random.randint(1, 1000)
        az_vz = int(az_ges * random.uniform(0.5, 1.0))
        az_gf = int(az_ges * random.uniform(0.01, 0.1))

        # Generate regional code (ao_kreis) with some in Eastern Germany (>=11000)
        east_region = random.random() < 0.3  # 30% in Eastern Germany
        ao_kreis = (
            random.randint(11000, 20000) if east_region else random.randint(1000, 10999)
        )

        establishment = {
            "betnr": betnr,
            "jahr": year,
            "az_ges": az_ges,
            "az_vz": az_vz,
            "az_gf": az_gf,
            "ao_kreis": ao_kreis,
        }
        establishments.append(establishment)

# Create establishments DataFrame
bhp_data = pd.DataFrame(establishments)

# Save the datasets in Stata format
siab_path = os.path.join(ORIG_DIR, f"{DATANAME}.dta")
bhp_path = os.path.join(ORIG_DIR, "SIAB_7514_v1_bhp_basis_v1.dta")

print(f"Saving SIAB microdata to {siab_path}")
siab_data.to_stata(siab_path, write_index=False)

print(f"Saving establishment data to {bhp_path}")
bhp_data.to_stata(bhp_path, write_index=False)

print("Synthetic data generation complete!")
