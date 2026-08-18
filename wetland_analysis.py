 """
This code imports annual sub-pixel water fraction (SWF) rasters to define wetlands within the study area and classify them into connectivity and innundation categories. First, using arcpy, contiguous wetland cells are then grouped into one cohesive wetland for further analysis.
[PART 2] Through GIS analysis using arcpy, wetland units are then classified as connected to the stream network if cells fall within 30m of a stream; otherwise, the wetland cells are designated as disconnected from the stream network.
Next, wetland inundation classes are defined by computing the global SWF average and setting percentile thresholds for each inundation class. Cells that meet the defined criteria are then delineated in each annual SWF raster.
[PART 3] Finally, wetland class rasters are saved to a user-defined path, and the area for wetlands of each wetland class is computed per subbasin and exported as an excel spreadsheet. This area data can then be input into the SWAT project. 

The code requires:
1. Annual SWF rasters spanning the project study period and study area
2. SWAT subbasin boundary file
3. SWAT stream network shapefile


"""
#Import libraries
import pandas as pd
import arcpy
from arcpy.sa import *

#Allow overwrite 
arcpy.env.overwriteOutput = True

#Set workspace
arcpy.env.workspace = r"INSERT PATH TO WORKSPACE HERE"

#Enable Spatial Analyst 
arcpy.CheckOutExtension("Spatial")

#Read project subbasin boundary
subs = r"INSERT PATH TO SUBBASIN BOUNDARY FILE HERE"

#Set extent of project
arcpy.env.extent = subs

#List input SWF tifs that have already been clipped to watershed
input_clipped_rasters = [
r"INSERT PATH TO RASTER HERE" #one raster per year
]

## PART 1: CREATE BUFFER AROUND STREAM NETWORK WITHIN WHICH WETLANDS ARE CONSIDERED CONNECTED ##
#1. Read stream network in UTM projection
streams_utm = r"INSERT PATH TO STREAM SHAPEFILE HERE"
#2. Determine Euclidean distance between stream and all cells in the watershed -- input your raster cell size for cell_size
streams_30m = EucDistance(streams_utm, cell_size= 30, distance_method='PLANAR')

#3. Determine which watershed cells fall within 30m (USER can change buffer distance here)
streams_30m_reclass = Reclassify(streams_30m, 'Value', RemapRange([[0,30,1], [30.001,99999999,0]]))
streams_30m_reclass.save(r"INSERT SAVE PATH HERE")

## PART 2: IDENTIFY GROUPED WETLANDS ##

#Create list to store resulting total areas/wetland class/year at end
wetland_area_list = []

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

    # Contiguous wetland cells are now grouped as one wetland

    ## PART 2: GIS ANALYSIS TO RECLASSIFY WETLAND TYPES AND COMPUTE AREAS TO INPUT INTO SWAT ##
    #1. Run zonal statistics to determine which wetlands are connected (MAX = 1) and disconnected (MAX = 0)
    zonal_stats_table_1 = ZonalStatisticsAsTable(region_group_int,"Value",streams_30m_reclass,f"SWF{year}_conn.dbf","DATA","MAXIMUM")
   
    #2. Join connectivity flag back to the wetland raster
    wetlands = arcpy.management.JoinField(region_group_int, "OID", zonal_stats_table_1,"OID")

    #3. SWF values in wetland raster cells are averaged among corresponding wetland groups so that every wetland has 1 SWF
    zonal_stats_table_2 = ZonalStatisticsAsTable(wetlands, "Value",int_focal_stats, f"SWC{year}_innundation.dbf","DATA", "MEAN")

    #4. Join wetland raster with connectivity info to wetland raster with SWF info
    wetlands_2 = arcpy.management.JoinField(wetlands, "OID",zonal_stats_table_2,"OID")

    #5. Collect all MEAN values from this year's zonal stats table for threshold computation
    with arcpy.da.SearchCursor(zonal_stats_table_2, ["MEAN"]) as cursor:
        for row in cursor:
            if row[0] is not None and row[0] > 0:
                all_mean_values.append(row[0])

    print(f"Pass 1 complete for {year}")

# Compute global absolute SWF thresholds from wetlands_2 MEAN values across all years
#NOTE: the user can change percentiles and thresholds to suit their project. Users can also define more inundation classes here.
all_mean_values = np.array(all_mean_values)
p5 = np.percentile(all_mean_values, 5)
p95 = np.percentile(all_mean_values, 95)
low = float(np.mean(all_mean_values[all_mean_values <= p5]))
high = float(np.mean(all_mean_values[all_mean_values >= p95]))
print(f"Global SWF thresholds - Low (mean of bottom 5%): {low:.2f}, High (mean of top 5%): {high:.2f}")

## PASS 2: Classify wetlands using global thresholds and compute subbasin areas ##
low_binary_rasters = []
high_binary_rasters = []

for i, input_raster in enumerate(input_clipped_rasters):
    year = i + 2011
    print(f"Pass 2 - Processing dataset {year}")

    # Reload the saved raster which already has MAX and MEAN fields joined from Pass 1
    wetlands_2 = arcpy.Raster(f"SWF{year}_rg_int.tif")

    #5. Extract rasters representing connectivity and degree of inundation
    print(f"Thresholds - Low: {low:.2f}, High: {high:.2f}")

    connected_low = ExtractByAttributes(wetlands_2, f"MAX = 1 AND MEAN > 0 AND MEAN <= {low}")
    connected_high = ExtractByAttributes(wetlands_2, f"MAX = 1 AND MEAN >= {high}")

    disconnected_low = ExtractByAttributes(wetlands_2, f"MAX = 0 AND MEAN > 0 AND MEAN <= {low}")
    disconnected_low.save(rf"INSERT SAVE PATH HERE")
    print("saved")
    
    disconnected_high = ExtractByAttributes(wetlands_2, f"MAX = 0 AND MEAN >= {high}")
    disconnected_high.save(rf"INSERT SAVE PATH HERE")

    # Clean rasters to just include data for cells defined as low or high inundation wetlands: 1 where low/high inundation SWF (connected or disconnected), NoData elsewhere
    low_binary = SetNull(IsNull(connected_low) & IsNull(disconnected_low), 1)
    high_binary = SetNull(IsNull(connected_high) & IsNull(disconnected_high), 1)
    low_binary_rasters.append(low_binary)
    high_binary_rasters.append(high_binary)

    #6. Run zonal statistics as table to compute the total area of classified wetlands per subbasin
    # Create list of extracted rasters from previous step
    extracted_rasters = [
        (connected_low, "connected_low"),
        (connected_high, "connected_high"),
        (disconnected_low, "disconnected_low"),
        (disconnected_high, "disconnected_high")
    ]

    #loop through extracted rasters
    for raster_obj, raster_type in extracted_rasters:
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
            df = pd.DataFrame(data, columns=field_names)

            #Use pandas to calculate average wetland area per class per subbasin
            for _, row in df.iterrows():
                area_km2 = row['AREA'] / 1000000  #convert sq m to sqkm

                #append averaged areas into list created at beginning:
                wetland_area_list.append({
                    'year': year,
                    'raster_type': raster_type,
                    'subbasin': row['Subbasin'],
                    'area_km2': area_km2
                })

        except Exception as e:
            print(f" Error processing {raster_type}: {str(e)}")

## PART 3: SAVE AVERAGE LOW AND HIGH INUNDATION SWF RASTERS ##
# Cell value = number of years (out of 9) each cell was classified as that inundation type
# NoData where a cell was never classified; 1-9 where it was present at least once
gdb = r"INSERT GEODATABASE PATH HERE"

avg_low_swf = CellStatistics(low_binary_rasters, "SUM", "DATA")
avg_low_swf.save(rf"{gdb}/avg_low_inundation_swf")
print("Saved avg_low_inundation_swf")

avg_high_swf = CellStatistics(high_binary_rasters, "SUM", "DATA")
avg_high_swf.save(rf"{gdb}/avg_high_inundation_swf")
print("Saved avg_high_inundation_swf")

#Create output dataframe
wetland_df = pd.DataFrame(wetland_area_list)

#Average output areas by subbasin and raster type across all years in time series
average_wetland_df = wetland_df.groupby(['raster_type','subbasin'])['area_km2'].mean().reset_index()

average_wetland_df = average_wetland_df.pivot(index='subbasin', columns = 'raster_type', values = 'area_km2') #Pivot dataframe so it's indexed by subbasin
average_wetland_df = average_wetland_df.reset_index() #Resets the index to include subbasin column

#Save as excel spreadsheet
average_wetland_df.to_excel('wetland_areas.xlsx', index=False)

print("all done!")




