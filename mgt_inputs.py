import os
import pandas as pd
import numpy as np
import shutil
import re
from distutils.dir_util import copy_tree
import datetime as dt
from datetime import datetime
from os import getcwd, listdir
from os.path import isfile, join
import csv
from statistics import mean


# SET UP PROJECT STRUCTURE ##
# 1. Create function that generates string matching .mgt file inputs
def generate_string(file, month, day, ops_no, fert_kg, irr_efm, fert_id="", fert_surf="", bio_init="", hi_targ="", bio_targ=""):
    string = str(month).rjust(3)
    string += str(day).rjust(3)
    string += str(ops_no).rjust(12)
    string += str(fert_id).rjust(5)
    string += str('{:.5f}'.format(float(fert_kg)).rjust(20))
    if fert_surf != '' and fert_surf is not None:
        string += str('{:.2f}'.format(float(fert_surf))).rjust(7)
    else:
        string += ''.rjust(7)
    string += str('{:.5f}'.format(float(irr_efm)) if irr_efm != '' else '').rjust(12)
    string += str('{:.2f}'.format(float(bio_init)) if bio_init != '' else '').rjust(5)
    string += str('{:.2f}'.format(float(hi_targ)) if hi_targ != '' else '').rjust(7)
    string += str('{:.2f}'.format(float(bio_targ)) if bio_targ != '' else '').rjust(6)
    # string += str(sub).rjust(12)
    file.write(string + '\n')

# 2. Define function that adds 17 to .mgt file at end of every year
def generate_year_delim(file):
    return file.write("17".rjust(18) + "\n")

# 3. Define function that writes a new line
def insert_break(file):
    return file.write("\n")

# 4. Create directory for mgt files which we will append later
directory = r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Land use correction/landuse_reclassification/input_files/mgt_files"
tmp_directory = os.path.join(directory, "tmp") # defines path of temporary subfolder

if not os.path.exists(tmp_directory):
    print(f"Error: source directory does not exist: {tmp_directory}")
    exit(1)

# Debug: Check what files are in both directories
print(f"Source directory: {directory}")
source_files = [f for f in listdir(directory) if isfile(join(directory, f))]
print(f"Source files: {source_files[:5]}...")  # Show first 5 files

print(f"Tmp directory: {tmp_directory}")
tmp_files = [f for f in listdir(tmp_directory) if isfile(join(tmp_directory, f))]
print(f"Tmp files: {tmp_files[:5]}...")  # Show first 5 files

mgt_files = [f for f in listdir(tmp_directory) if isfile(join(tmp_directory, f)) and f.endswith('.mgt')] # Only get .mgt files
print(f"Found {len(mgt_files)} .mgt files in tmp directory")

shutil.rmtree(tmp_directory, ignore_errors = True) #deletes subbfolder if already exists, bypasses errors if it doesn't
os.mkdir(tmp_directory)  #Recreates tmp directory
copy_tree(directory, tmp_directory) #Copies mgt files to tmp directory.
mgt_files = [f for f in listdir(tmp_directory) if isfile(join(tmp_directory, f))] # reads each mgt file in tmp directory

# 5. MAKE DATA FRAME FOR IRR EVENTS and everything I need to write to .mgt files.
mgt_rows = []
columns = ["month", "day", "mgt_op", "fert_kg", "irr_efm", "fert_id", "fert_surf", "bio_init", "hi_targ", "bio_targ"]
print("done pt1")

## IMPORT DATA ##

#Swine manure data from fert.dat. total n = org-n + min-n
swine_manure = {
    'tot_n_ratio': 0.047,
    'tot_p_ratio': 0.016
}


#Import fertilizer and manure application data
n_fertilizer = pd.read_csv('grouped_N_fert_kgha.csv',keep_default_na=False)
n_manure = pd.read_csv('grouped_N_manure_kgha.csv',keep_default_na=False)
#p_manure = pd.read_csv('grouped_P_manure_kgha.csv',keep_default_na=False)
print("imported")

# 3. Define date ranges per crop, define subbasins
crops = {
    "CORN": {
        "start mon": 5,
        "start day": 7,
        "end mon": 10,
        "end day": 25,
    },
    "SOYB": {        
        "start mon": 5,
        "start day": 17,
        "end mon": 10,
        "end day": 15,
    },
    "TOBC": {        
        "start mon": 5,
        "start day": 17,
        "end mon": 10,
        "end day": 1,
    }
}
# subbasins = {1:30}


def get_applications(soil_id, crop_key, year):
    applications = []

    application_timing = {
        'CORN': {
            'n_fertilizer': {'month': 5, 'day': 1},
            'n_manure': {'month': 5, 'day': 1},
            # 'p_manure': {'month': 5, 'day': 1}
        },
        'SOYB': {
            'n_fertilizer': {'month': 5, 'day': 15},
            'n_manure': {'month': 5, 'day': 15},
            # 'p_manure': {'month': 5, 'day': 15}
                },
        'TOBC': {
            'n_fertilizer': {'month': 5, 'day': 17},
            'n_manure': {'month': 5, 'day': 17},
            # 'p_manure': {'month': 5, 'day': 17}
        }
                
    }
    timing = application_timing.get(crop_key, application_timing['CORN'])

    n_fert_data = n_fertilizer.query(f'YEAR == {year} and SOILID == "{soil_id}"')
    if not n_fert_data.empty and crop_key in n_fert_data.columns:
        n_fert_amount = n_fert_data[crop_key].iloc[0] #limit decimal places
        if pd.notna(n_fert_amount) and n_fert_amount > 0:
            applications.append({
                'type': 'n_fertilizer',
                'amount': n_fert_amount,
                'ops_no': 3,
                'fert_id': 1,
                'fert_surf': 0,
                'month': timing['n_fertilizer']['month'],
                'day': timing['n_fertilizer']['day']
            })

    n_manure_data = n_manure.query(f'YEAR == {year} and SOILID == "{soil_id}"')
    if not n_manure_data.empty and crop_key in n_manure_data.columns:
        n_manure_amount_raw = n_manure_data[crop_key].iloc[0]
        if pd.notna(n_manure_amount_raw) and n_manure_amount_raw > 0:
            n_manure_amount = n_manure_amount_raw/swine_manure['tot_n_ratio'] #change to int? / limit decimal places
            applications.append({
                'type': 'n_manure',
                'amount': n_manure_amount,
                'ops_no': 3,
                'fert_id': 47,
                'fert_surf': 0,
                'month': timing['n_manure']['month'],
                'day': timing['n_manure']['day']
            })

    # p_manure_data = p_manure.query(f'YEAR == {year} and SOILID == "{soil_id}"')
    # if not p_manure_data.empty:
    #     if crop_key in p_manure_data.columns:
    #         p_manure_amount = p_manure_data[crop_key].iloc[0]
    #         if pd.notna(p_manure_amount) and p_manure_amount > 0:
    #             applications.append({
    #                 'type': 'p_manure',
    #                 'amount': p_manure_amount,
    #                 'ops_no': 3,
    #                 'fert_id': 47,
    #                 'month': timing['p_manure']['month'],
    #                 'day': timing['p_manure']['month']
    #         })

    return applications



# 4. Import crop csvs with baseline mgt ops to be included with grouped fertilizer and manure inputs
corn = pd.read_csv("corn.csv", keep_default_na=False)
soyb = pd.read_csv("SOYB.csv", keep_default_na=False)
tobc = pd.read_csv("TOBC.csv", keep_default_na=False)

print("imported baseline")
print(f"Processing {len(mgt_files)} management files...")

# 1. Define management files and included filters (hru, subbasin, crop_key, soil)
for file_count, mgt_file in enumerate(mgt_files):
    print(f"Processing file {file_count + 1}/{len(mgt_files)}: {mgt_file}")

    mgt_file_path  = os.path.join(tmp_directory, mgt_file) #loops through selecting mgt files in tmp_directory.
    
    # Initialize variables with default values
    hru = hruno = crop_key = soil = None
    try:
        with open(mgt_file_path, "r") as file:
            data = file.read() #reads file

            if "Operation Schedule" not in data:
                print(f"Warning: 'Operation Schedule' not found in {mgt_file}")
                continue

            index = data.index("Operation Schedule") + 50
            file.seek(index)

            hru_match = re.search(r"(?<=HRU\:)\d+", data)
            hruno_match = re.search(r"(?<=Watershed HRU\:)\d+", data) #regex; looking for HRU: and digits after, in data file. returns a list of every match in file. This searches for HRU number in each mgt file. [0] means we just want the first result
            # subbasin_match = re.search(r"(?<=Subbasin\:)\d+", data)#same as above but for subbasin
            crop_key_match = re.search(r"(?<=Luse\:)[A-Z]+", data) #same as above but for luse
            soil_match = re.search(r"(?<=Soil\: )[A-Z0-9_~]+", data)
            
            if not all([hru_match, hruno_match, crop_key_match, soil_match]):
                print(f"Warning: Could not extract all metadata from {mgt_file}")
                print(f"  HRU: {hru_match}, Watershed HRU: {hruno_match}")
                print(f"  Crop: {crop_key_match}, Soil: {soil_match}")
                continue

            hru = int(hru_match[0])
            hruno = int(hruno_match[0])
            # subbasin = int(subbasin_match[0])
            crop_key = crop_key_match[0]
            soil = soil_match[0]

            print(f"  HRU: {hru}, Crop: {crop_key}, Soil: {soil}")


  
# 2. Define crops and dates   
        if crop_key in crops.keys(): # only run if crop is in list (tobc, corn, soyb)
            crop = crops[crop_key]
            extra_ops = globals()[crop_key.lower()]
            dates = pd.date_range(start = "2011-01-01", end = "2016-12-31")

            all_mgt_operations = []


            year_break = 2007

            print(f"  Processing {len(dates)} dates for {crop_key}")
            
            for date in dates:
                year = date.year
                month = date.month
                day = date.day
                start_date = dt.datetime(year, crop["start mon"], crop["start day"])
                end_date = dt.datetime(year, crop["end mon"], crop["end day"])
                

                if day == 1 and month ==1:
                    mgt_rows = []

                    nutrient_apps = get_applications(soil, crop_key, year)

                    for app in nutrient_apps:
                        mgt_rows.append([app['month'], app['day'], app['ops_no'], app['amount'], "", app['fert_id'], app['fert_surf'], "", "", ""])

#  3. Structure extra operations and when to break year in mgt files
                filtered_extra_ops = extra_ops.query(f'Month == {month} and Day == {day} and Year == {year}')
                for index, extra_op in filtered_extra_ops.iterrows():
                    mgt_rows.append([month, day, extra_op.get("ops_no", ""), extra_op.get("fert_kg", ""), extra_op.get("irr_efm", ""), extra_op.get("fert_id", ""), extra_op.get("fert_surf", ""), extra_op.get("bio_init", ""), extra_op.get("hi_targ", ""), extra_op.get("bio_targ", "")])


                if day == 31 and month == 12:
                    mgt_df = pd.DataFrame(mgt_rows, columns=columns)
                    mgt_df = mgt_df.sort_values(['month', 'day'])
                    all_mgt_operations.append(mgt_df)

            with open(mgt_file_path, "r+") as file:
                    file_content = file.read()
                    index = file_content.index("Operation Schedule") + 50
                    file.seek(index)

                    for year_df in all_mgt_operations:
                        for index, row in year_df.iterrows():
                            generate_string(file, row["month"], row["day"], row["mgt_op"], row["fert_kg"], row["irr_efm"], row["fert_id"], row["fert_surf"], row["bio_init"], row["hi_targ"], row["bio_targ"])
                        generate_year_delim(file)
# # 7. Write ops to mgt files     
                    # for index, row in mgt_df.iterrows():    
                    #     generate_string(file, row["month"], row["day"], row["mgt_op"], row["fert_kg"], subbasin, row["irr_efm"], row["fert_id"], row["fert_surf"], row["bio_init"], row["hi_targ"], row["bio_targ"])
                    # generate_year_delim(file)
                    
            print(f"  Completed processing {mgt_file}")
        else:
                print(f"  Skipping {mgt_file} - crop {crop_key} not in defined crops")
    except Exception as e:
        print(f"Error processing {mgt_file}: {str(e)}")
        import traceback
        traceback.print_exc()  # This will show the full error traceback
        continue

