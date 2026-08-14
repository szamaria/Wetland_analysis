import os
import re
import pandas as pd
from pathlib import Path

"""
This code updates the SWAT input .chm files by soil type with initial soil soluble P and NO3 from Group_initial_soilnutrients.py (Initial_soilnutrients.csv)

Parameters:
input_data (dict): Dictionary with soil types as keys and 'labile_P': value, 'NO3': value} as values
chm_directory (str): Path to directory containing .chm files
create_backup: creates backups of the original .chm files

"""

def update_chm_files(input_data, chm_directory, create_backup=True):
    chm_dir = Path(chm_directory)
    chm_files = list(chm_dir.glob("*.chm")) # Finds all .chm files
    print(chm_dir)

    if not chm_files:
        print(f"No .chm files found in {chm_dir}")
        return
    print(f"Found {len(chm_files)} .chm files to process")

    #set updated and skipped files to 0, for keeping track of how many .chm files were updated or skipped later in the code
    updated_files = 0
    skipped_files = 0

    for chm_file in chm_files:
        try:
            #read the .chm file
            with open(chm_file, 'r', encoding='utf-8') as f:
                content = f.read()

                #creates .chm backup if create_backup=True
                if create_backup:
                    backup_file = chm_file.with_suffix('.chm.bak')
                    with open(backup_file, 'w', encoding='utf-8') as f:
                        f.write(content)

                #Extract soil type from .chm header line
                lines = content.split('\n')
                header_line = lines[0] if lines else "No content found"

                #Use regex to find "Soil: SOILNAME" followed by a space in the header line
                soil_match = re.search(r'Soil:\s*([^\s]+)', header_line)

                if not soil_match:
                    print(f"Warning: Could not extract soil type from {chm_file.name}")
                    skipped_files +=1
                    continue

                soil_type = soil_match.group(1) # Only retains the first grouping of text in header of what soil_match found , ie. isolates soil type from rest of line
                print(f"Processing {chm_file.name}: found soil type '{soil_type}")

                if soil_type not in input_data:
                    print(f"Warning: No data found for soil type '{soil_type}' in {chm_file.name}")
                    skipped_files +=1
                    continue

                #Get new P and NO3 values from input_data (defined in later def). Essentially we are getting labile P and NO3 values matching the soil type from Input_soilnutrients.csv
                new_labile_p = input_data[soil_type]['labile_P']
                new_NO3 = input_data[soil_type]['NO3']

                #Update .chm content - update_soil_values function DEFINED in next def block
                updated_content = update_soil_values(content, new_labile_p, new_NO3)

                #Write back to .chm file
                with open(chm_file, 'w', encoding = 'utf-8') as f:
                    f.write(updated_content)
                
                print(f"Updated {chm_file.name}: Soil={soil_type}, Labile P={new_labile_p}, NO3 = {new_NO3}")
                updated_files += 1

        except Exception as e:
            print(f"Error processing {chm_file.name}: {str(e)}")
            skipped_files +=1

    print(f"\nSummary: {updated_files} files updated, {skipped_files} files skipped")
    
    
def update_soil_values(content, new_labile_p, new_NO3):
    """
    A function to update the soil labile P and NO3 values in the .chm file while preserving formatting for SWAT
    """
    lines = content.split('\n')
    updated_lines = []

    for line in lines:
        #Check for Soil NO3 line
        if 'Soil NO3 [mg/kg]' in line and ':' in line:
            #Parse the original line to preserve formatting
            parts = line.split(':',1) #split line only after first colon
            prefix = parts[0] + ':' #SOIL NO3 [mg/kg]:
            values_part = parts[1] #SOIL NO3 vaklue (after ':')

            #Extract values while preserving the spacing
            values = values_part.split()
            if values:
                #replace first value with new N value,  keeping formatting
                values[0] = f"{new_NO3:.2f}"
                
                #Reconstruct entire line with proper spacing, matching the original formatting
                updated_line = prefix
                
                for i, val in enumerate(values):
                    updated_line += f"{float(val):12.2f}"
                
                updated_lines.append(updated_line)
            else:
                updated_lines.append(line)
        
        #Follow the same for above but for Soil labile P
        elif 'Soil labile P [mg/kg]' in line and ':' in line:
            parts = line.split(':',1)
            prefix = parts[0] + ':'
            values_part = parts[1]
            
            values = values_part.split()
            if values:
                values[0] = f"{new_labile_p:.2f}"
                updated_line = prefix
                
                for i, val in enumerate(values):
                    if i == 0:
                        updated_line += f"{float(val):12.2f}"
                    else:
                        updated_line += f"{float(val):12.2f}"
                updated_lines.append(updated_line)
            else:
                updated_lines.append(line)

        else:
            updated_lines.append(line)

    return '\n'.join(updated_lines)



def load_soil_data(csv_file):
    """
    This function loads soil and input nutrient data from Input_soilnutrients.csv
    """
    try:
        df = pd.read_csv(csv_file)
        soil_data = {} #becomes input_data that is input into the update_chm_files function

        for _, row in df.iterrows(): #_ means we don't care about the index number; otherwise, we would put the number here
            soil_type = row['SOILID']
            soil_data[soil_type] = {
                'labile_P': float(row['SOILPSOURCE_VAL']),
                'NO3': float(row['RSN_VAL']) }
        return soil_data
    
    except Exception as e:
        print(f"Error loading CSV file: {str(e)}")
        return None


#Run code:
if __name__ == "__main__": #Only run within script
    soil_data = load_soil_data(r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Nutrient_calibration/Initial soil nutrients/Initial_soilnutrients.csv")
    chm_directory = r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Land use correction/landuse_reclassification/input_files/chm_files"
    update_chm_files(soil_data, chm_directory)

    print("Script ready!")
    print("1. Update the 'chm_directory' variable with actual path (line 164)")
    print("2. Define your soil data (line 163)")
    print("3. Run the script")