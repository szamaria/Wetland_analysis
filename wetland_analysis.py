#Import libraries
import pandas as pd
import arcpy
from arcpy.sa import *

#Allow overwrite 
arcpy.env.overwriteOutput = True

#Set workspace
arcpy.env.workspace = r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis"

#Enable Spatial Analyst 
arcpy.CheckOutExtension("Spatial")

#Read project boundary file
subs = r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/GIS data/BCWS/subs1.shp"

#Set extent of project
arcpy.env.extent = subs

#List input SWF tifs that have already been clipped to BCWS
input_clipped_rasters = [
r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/GIS data/GuelphRasters/SWF/clipped/SWF2011_em.tif",
r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/GIS data/GuelphRasters/SWF/clipped/SWF2012_em.tif",
r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/GIS data/GuelphRasters/SWF/clipped/SWF2013_em.tif",
r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/GIS data/GuelphRasters/SWF/clipped/SWF2014_em.tif",
r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/GIS data/GuelphRasters/SWF/clipped/SWF2015_em.tif",
r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/GIS data/GuelphRasters/SWF/clipped/SWF2016_em.tif",
r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/GIS data/GuelphRasters/SWF/clipped/SWF2017_em.tif",
r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/GIS data/GuelphRasters/SWF/clipped/SWF2018_em.tif",
r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/GIS data/GuelphRasters/SWF/clipped/SWF2019_em.tif"
]

#CHECK THIS
## PART 1: CREATE BUFFER AROUND STREAM NETWORK WITHIN WHICH WETLANDS ARE CONSIDERED CONNECTED ##
#1. Read stream network
streams_utm = r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/Wetland_analysis.gdb/streams_utm.shp"

#2. Determine Euclidean distance between stream and all cells in the watershed
streams_30m = EucDistance(streams_utm, cell_size= 30, distance_method='PLANAR')

#3. Determine which watershed cells fall within 30m
streams_30m_reclass = Reclassify(streams_30m, 'Value', RemapRange([[0,30,1], [30.001,99999999,0]]))
streams_30m_reclass.save(r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/Wetland_analysis.gdb/streams_30m_reclass")

## PART 2: IDENTIFY GROUPED WETLANDS ##

#Create list to store resulting total areas/wetland class/year at end
wetland_area_list = []

''' #Run only if previous 2 steps were run outside of arcpy
#Read reclassified stream buffer raster and subbasin polygon
# streams_30m_reclass = r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/Wetland_analysis.gdb/streams_30m_reclass"
# subs = r"C:/Users/sophi/OneDrive/Documents/School/PhD/Thesis/Chapter 3/Wetlands/Wetland_analysis/GIS data/BCWS/subs1.shp"
print("done")
'''

# Process each clipped raster
for i, input_raster in enumerate(input_clipped_rasters):
    year = i + 2011
    print(f"Processing dataset {year}: {input_raster}")

    #1. Run focal statistics
    focal_stats = FocalStatistics(input_raster,NbrRectangle(3,3,"CELL"), 'MEAN', "DATA")

    #2. Run int on focal statistics
    int_focal_stats = Int(focal_stats)

    #3 Run region group on int_focal_Stats
    region_group = RegionGroup(int_focal_stats, "EIGHT", "CROSS")

    #4 Run int on region group
    region_group_int = Int(region_group)
    region_group_int.save(f"SWF{year}_rg_int.tif")

    print("working")

    ## PART 2: GIS ANALYSIS TO RECLASSIFY WETLAND TYPES AND COMPUTE AREAS TO INPUT INTO SWAT ##
    #1. Run zonal statistics to determine which wetlands are connected (MAX = 1) and disconnected (MAX = 0)
    zonal_stats_table_1 = ZonalStatisticsAsTable(region_group_int,"Value",streams_30m_reclass,f"SWF{year}_conn.dbf","DATA","MAXIMUM")
   
    #2. Join connectivity flag back to the wetland raster
    wetlands = arcpy.management.JoinField(region_group_int, "OID", zonal_stats_table_1,"OID")

    #3. SWF values in wetland raster cells are averaged among corresponding wetland groups so that every wetland has 1 SWF
    zonal_stats_table_2 = ZonalStatisticsAsTable(wetlands, "Value",int_focal_stats, f"SWC{year}_innundation.dbf","DATA", "MEAN")

    #4. Join wetland raster with connectivity info to wetland raster with SWF info
    wetlands_2 = arcpy.management.JoinField(wetlands, "OID",zonal_stats_table_2,"OID")

    #5. Extract 6 unique rasters representing connectivity and degree of innundation. NOTE: inundation % classes are calculated from the region_group_int mean SWF
    
    # First, get statistics from original inundation raster to calculate thresholds/classes
    result = arcpy.GetRasterProperties_management(wetlands_2, "MAXIMUM")
    max_value = float(result.getOutput(0))
    low = max_value * 0.33
    medium = max_value * 0.66
    high = max_value  # 100%
    print(f"Thresholds - Low: {low:.2f}, Medium: {medium:.2f}, High: {high:.2f}")

    connected_low = ExtractByAttributes(wetlands_2, f"MAX = 1 AND MEAN > 0 AND MEAN <= {low}")
    connected_med = ExtractByAttributes(wetlands_2, f"MAX = 1 AND MEAN > {low} AND MEAN <= {medium}")
    connected_high = ExtractByAttributes(wetlands_2, f"MAX = 1 AND MEAN > {medium} AND MEAN <= {max_value}")
    
    disconnected_low = ExtractByAttributes(wetlands_2, f"MAX = 0 AND MEAN > 0 AND MEAN <= {low}")
    disconnected_med = ExtractByAttributes(wetlands_2, f"MAX = 1 AND MEAN > {low} AND MEAN <= {medium}")
    disconnected_high = ExtractByAttributes(wetlands_2, f"MAX = 0 AND MEAN > {medium} AND MEAN <= {max_value}")
    
    #6. Run zonal statistics as table to compute the total area of classified wetlands per subbasin
    # Create list of extracted rasters from previous step
    extracted_rasters =[
        (connected_low, "connected_low"),
        (connected_med, "connected_med"),
        (connected_high, "connected_high"),
        (disconnected_low, "disconnected_low"),
        (disconnected_med, "disconnected_med"),
        (disconnected_high, "disconnected_high")
    ]

    #loop through extracted rasters
    for raster_obj, raster_type in extracted_rasters:
        #"try:" handles errors that may arise if any of the extracted rasters are empty
        try:
            output_table = f"SWF{year}_{raster_type}.dbf"
            ZonalStatisticsAsTable(subs, "Subbasin", raster_obj, output_table, "DATA", "ALL")
            print(f" completed zonal stats for {raster_type}")
            
            #Convert output table to pandas DataFrame for easier data analysis
            field_names = [field.name for field in arcpy.ListFields(output_table)]
            data = []
            with arcpy.da.SearchCursor(output_table, field_names) as cursor:
                for row in cursor:
                    data.append(row)
            df = pd.DataFrame(data, columns = field_names)

            #Use pandas to calculate average wetland area per class per subbasin
            for _, row in df.iterrows():
                area_km2 = row['AREA'] / 1000000 #convert sqm to sqkm
                
                #append averaged areas into list created at beginning:
                wetland_area_list.append({
                    'year': year,
                    'raster_type': raster_type,
                    'subbasin': row['Subbasin'],
                    'area_km2': area_km2
                })

        except Exception as e:
            print(f" Error processing {raster_type}: {str(e)}")

#Create output dataframe
wetland_df = pd.DataFrame(wetland_area_list)

#Average output areas by subbasin and raster type across all years in time series
average_wetland_df = wetland_df.groupby(['raster_type','subbasin'])['area_km2'].mean().reset_index()

average_wetland_df = average_wetland_df.pivot(index='subbasin', columns = 'raster_type', values = 'area_km2') #Pivot dataframe so it's indexed by subbasin
average_wetland_df = average_wetland_df.reset_index() #Resets the index to include subbasin column

#Save as excel spreadsheet
average_wetland_df.to_excel('wetland_areas.xlsx', index=False)

print("all done!")


  







