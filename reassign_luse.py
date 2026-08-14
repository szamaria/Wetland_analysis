import os
import re
import pandas as pd
from pathlib import Path

"""
This code reassigns new land uses to the original SWAT HRU land uses in the .chm files. 
Land use reassignment including a readme is available in the following path:
C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Land use correction/landuse_reclassification
"""

def update_luse_values(content, new_luse):
    """
    Replace the land use value in the header line after 'Luse:'
    """
    lines = content.split('\n')
    if not lines:
        return content
    
    header_line = lines[0]
    
    # Use regex to find "Luse:" followed by the land use value
    luse_match = re.search(r'Luse:\s*([^\s]+)', header_line)
    
    if luse_match:
        # Replace the old land use with the new one in the header line
        updated_header = re.sub(r'(Luse:)\s*[^\s]+', rf'\1{new_luse}', header_line)
        lines[0] = updated_header
        updated_content = '\n'.join(lines)
        return updated_content
    else:
        print(f"Warning: 'Luse:' not found in header")
        return content


def update_chm_files(hrucode_to_lulc, chm_directory, create_backup=True):
    """
    Update .chm files with new land use values based on HRUCODE mapping
    """
    chm_dir = Path(chm_directory)
    chm_files = list(chm_dir.glob("*.chm"))
    
    if not chm_files:
        print(f"No .chm files found in {chm_dir}")
        return
    
    print(f"Found {len(chm_files)} .chm files to process")
    
    updated_files = 0
    skipped_files = 0

    for chm_file in chm_files:
        try:
            # Extract HRUCODE from filename
            HRUCODE = chm_file.stem
            
            # Check if this HRUCODE has a new land use value
            if HRUCODE not in hrucode_to_lulc:
                print(f"{chm_file.name}: Skipping (no NewLULC value or not in CSV)")
                skipped_files += 1
                continue
            
            new_luse = hrucode_to_lulc[HRUCODE]
            print(f"{chm_file.name}: HRUCODE {HRUCODE} -> {new_luse}")
            
            # Read the .chm file
            with open(chm_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create backup if requested
            if create_backup:
                backup_file = chm_file.with_suffix('.chm.bak')
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # Update the land use in the content
            updated_content = update_luse_values(content, new_luse)
            
            # Write back to .chm file
            with open(chm_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            updated_files += 1

        except Exception as e:
            print(f"Error processing {chm_file.name}: {str(e)}")
            skipped_files += 1
    
    print(f"\nProcessing complete!")
    print(f"Updated files: {updated_files}")
    print(f"Skipped files: {skipped_files}")


def load_data(csv_file):
    """
    Load data from SWAT_newluse_input.csv and create HRUCODE to NewLULC mapping
    """
    try:
        # Read CSV with both columns as strings
        df = pd.read_csv(csv_file, dtype={'HRUCODE': str, 'NewLULC': str})
        
        # Filter out rows where NewLULC is empty/NaN
        df = df[df['NewLULC'].notna()]
        
        # Create mapping dictionary: HRUCODE (9 digits with leading zeros) -> NewLULC
        hrucode_to_lulc = dict(zip(df['HRUCODE'].str.zfill(9), df['NewLULC']))
        
        print(f"Loaded {len(hrucode_to_lulc)} HRUCODE mappings from CSV")
        return hrucode_to_lulc
    
    except Exception as e:
        print(f"Error loading CSV file: {str(e)}")
        return None


# Run code:
if __name__ == "__main__":
    # Load the HRUCODE to land use mapping
    csv_file = r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Land use correction/landuse_reclassification/SWAT_newluse_input.csv"
    hrucode_to_lulc = load_data(csv_file)
    
    if hrucode_to_lulc is None:
        print("Failed to load data. Exiting.")
        exit()
    
    # Update the .chm files
    chm_directory = r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Land use correction/landuse_reclassification/input_files/chm_files"
    update_chm_files(hrucode_to_lulc, chm_directory, create_backup=True)
    
    print("\nScript complete!")