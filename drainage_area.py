#Import libraries
import pandas as pd
import arcpy
from arcpy.sa import *

#Allow overwrite 
arcpy.env.overwriteOutput = True

#Set workspace
arcpy.env.workspace = r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/Wetland_analysis.gdb/"

#Enable Spatial Analyst 
arcpy.CheckOutExtension("Spatial")

#Read project boundary file and DEM
subs = r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/GIS data/BCWS/subs1.shp"
DEM = r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/Wetland_analysis.gdb/DEM_utm"

#Set extent of project
arcpy.env.extent = subs

#List input extracted wetland class tifs
input_disconnected_rasters = arcpy.ListRasters("disconnected_*")
print(f"Found {len(input_disconnected_rasters)} disconnected rasters:")
for r in input_disconnected_rasters:
    print(f"  - {r}")

#Create list to store resulting drainage areas
drainage_area_list = []

#1. Run flow direction on DEM
Flow_Direction = FlowDirection(DEM)
print("Flow direction completed")

#2. Loop through wetland rasters to run watershed. Watershed defines area around each wetland that drains into the wetland.
print("Starting loop through wetland rasters...")
for raster in input_disconnected_rasters:
    print(f"Processing {raster}...")

    try:
        if arcpy.Exists(raster):
            print(f"  ✓ Raster {raster} exists")

            print(f"  Running watershed analysis...")
            watershed_area = Watershed(Flow_Direction,raster)
            output_name = f"watershed_{raster}"
            watershed_area.save(output_name)
            print(f"  ✓ Saved watershed: {output_name}")


            #6. Run zonal statistics as table to compute the total area of classified wetlands per subbasin
            print(f"  Running zonal statistics...")
            output_table = f"zonalstats_{raster}"
            zonal_stats = ZonalStatisticsAsTable(subs, "Subbasin", watershed_area, output_table, "DATA", "ALL" )
            print(f" completed zonal stats for {output_table}")

            if arcpy.Exists(output_table):
                print(f"  ✓ Zonal stats table created successfully")

            #7. Convert output table to pandas DataFrame for easier data analysis
                print(f"  Converting table to DataFrame...")
                field_names = [field.name for field in arcpy.ListFields(output_table)]
                print(f"  Found fields: {field_names}")
                
                data = []
                with arcpy.da.SearchCursor(output_table, field_names) as cursor:
                    for row in cursor:
                        data.append(row)
                print(f"  Found {len(data)} rows in table")        
                df = pd.DataFrame(data, columns = field_names)

            #Use pandas to calculate average drainage area per subbasin
            for _, row in df.iterrows():
                area_km2 = row['AREA'] / 1000000 #convert sqm to sqkm
                
                #append averaged areas into list created at beginning:
                drainage_area_list.append({
                    'wetland_class': raster,
                    'Subbasin': row['Subbasin'],
                    'area_km2': area_km2
                })
               
            print(f"  ✓ Added {len(df)} entries to drainage_area_list")
        else:
            print(f"  ✗ Zonal stats table was not created")
                    
    except Exception as e:
        print(f"  ✗ ERROR processing {raster}: {str(e)}")
        import traceback
        traceback.print_exc()  # This shows the full error details
else:
    print(f"  ✗ Raster {raster} does not exist - skipping")        


print(f"\n=== LOOP COMPLETED ===")
print(f"Final drainage_area_list has {len(drainage_area_list)} entries")


#Create output dataframe
drainage_df = pd.DataFrame(drainage_area_list)

#Extract wetland type
drainage_df['wetland_type'] = drainage_df['wetland_class'].str.extract(r'(low|high)')
print("Unique wetland types found:")
print(drainage_df['wetland_type'].unique())
print(f"Total rows in drainage_df: {len(drainage_df)}")

averaged_by_subbasin = drainage_df.groupby(['wetland_type', 'Subbasin'])['area_km2'].mean().reset_index()
print(f"\nRows in averaged_by_subbasin: {len(averaged_by_subbasin)}")
print("Wetland type counts in grouped data:")
print(averaged_by_subbasin['wetland_type'].value_counts())

# Check a sample of the grouped data
print("\nSample of averaged_by_subbasin:")
print(averaged_by_subbasin.head(10))


#Convert subs into a pandas df.
fields = ['Subbasin', 'Area']
data = []
with arcpy.da.SearchCursor(subs, fields) as cursor:
    for row in cursor:
        data.append(row)

subs_df = pd.DataFrame(data, columns=fields)
print("Columns in averaged_by_subbasin:")
print(averaged_by_subbasin.columns.tolist())

print("\nColumns in subs_df:")
print(subs_df.columns.tolist())

#merge drainage area and subbasin area dataframes into one
merged_df = averaged_by_subbasin.merge(subs_df, on="Subbasin", how='left')
# After merge
print(f"\nRows in merged_df: {len(merged_df)}")
print("Wetland type counts in merged data:")
print(merged_df['wetland_type'].value_counts())

#Calculate percentage of subbasin area that is drained (WET_FR)
merged_df['WET_FR'] = (merged_df['area_km2']/merged_df['Area'])
print("Drainage areas as percentage of subbasin areas:")
print(merged_df[['wetland_type', 'Subbasin', 'Area', 'WET_FR']])

#Save as excel spreadsheet
merged_df.to_excel('WET_FR.xlsx', index=False)

# average_wetland_df = average_drainage_df.pivot(index='subbasin', columns = 'raster_type', values = 'area_km2') #Pivot dataframe so it's indexed by subbasin
# average_wetland_df = average_drainage_df.reset_index() #Resets the index to include subbasin column
# """