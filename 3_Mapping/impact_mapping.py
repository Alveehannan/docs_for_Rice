import os,sys,glob
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import geopandas as gpd
from shapely.geometry import Point
from cartopy import crs as ccrs
# import json
# import dask_geopandas as dask_gpd

districts = [ 'Jamalpur','Bogra','Kurigram', 'Gaibandha']

element_nos = 2
# district = 'Gaibandha'
# union = f'Fulchhari'
# date = '20230901'
# SUFAL_unions_shapefile = './SUFAL_unions/SUFAL_unions.shp'
# roads_shapefile = './raods/SUFAL_lged_roads.shp'
# vulnerability_indices = './Vulnerability_indices.csv' 
# plot_output = './plots'
# geojson_output = './geojson/'
# inundation_path = f'./inundation_output/inundation_{date}_{district}.geojson'

def get_district(union,shapefile):
    
    union_shp = shapefile[shapefile['ADM4_EN'] == union]
    district = union_shp['ADM2_EN'][0]

    return district

def element_exposure(ratio):

    if ratio < 0.3:
        return 1
    elif (ratio >= 0.3) & (ratio < 0.6):
        return 2
    else:
        return 3 


def exposure(val, element_nos):
    idx = val/element_nos

    if idx <= 1.0:
        return 1
    elif (idx > 1.0) & (idx <=2.0):
        return 2
    else:
        return 3


def combined_score(inun,exp):

    if inun not in [1,2,3]:
        print ('invalid inundation score')

        return

    if exp not in [1,2,3]:
        print('invalid exposure score')

        return

    score = inun*exp

    if score < 3 :
        idx = 1
    
    elif score == 3 :   
        if exp == 1:
            idx = 1
        else:
            idx = 2
    
    elif (score > 3) & (score < 9):
        idx = 2

    else:
        idx = 3 

    return idx

        

def impact_score(exposure,vulnerability):

    if exposure not in [1,2,3]:
        print ('invalid exposure score')

        return

    if vulnerability not in [1,2,3]:
        print('invalid vulnerability score')

        return

    score = exposure*vulnerability

    if score <= 3 :
        idx = 1
    
    # elif score == 3 :   
    #     if exposure == 1:
    #         idx = 1
    #     else:
    #         idx = 2
    
    elif (score > 3) & (score <= 6):
        idx = 2

    else:
        idx = 3 
    
    return idx


def impact_color(val):

    colors = ['#FFFF00', '#FF7F50', '#FF0000']

    color = colors[int(val) - 1]
    
    return color

def inun_color(val):

    #colors = ['#FFFFFF', '#FFFF00', '#FF7F50', '#FF0000', '#00008B']
    colors = ['#FFFFFF', '#b3cde0', '#6497b1', '#005b96', '#011f4b']
    color = colors[int(val)]
    
    return color

def level(value):

    levels = {3: "High", 2: "Medium", 1: "Low"}

    if value not in levels.keys():
        print('invalid level value')

        return

    else: 
        return levels[value]


def impact_inundation(date, district, union, vulnerability_indices, roads_shapefile, plot_output, gdf):

    # inun_geojson_path = f"./inundation_output/{date}/inundation_{date}_{district}.geojson"

    # gdf = gpd.read_file(inun_geojson_path)
    gdf['inun_lvl'] = np.arange(0,len(gdf))
    gdf_in = gdf.loc[1:, ['inun_lvl', 'geometry']]

    gdf_in.reset_index(drop=True, inplace=True)

    wards = gpd.read_file(f'./ward_shp/{union}.shp')

    if 'Ward' in wards.columns:
        wards.rename(columns={'Ward': 'WARD'}, inplace=True)
    elif 'ward' in wards.columns:
        wards.rename(columns={'ward': 'WARD'}, inplace=True)
    elif 'ward_no' in wards.columns:
        wards.rename(columns={'ward_no': 'WARD'}, inplace=True)
    elif 'Ward_no' in wards.columns:
        wards.rename(columns={'Ward_no': 'WARD'}, inplace=True)
    elif 'Ward_No' in wards.columns:
        wards.rename(columns={'Ward_no': 'WARD'}, inplace=True)
    else:
        print ('invalid ward name header')       
    
    wards.WARD = wards['WARD'].astype(int).to_numpy()
    wards.sort_values(by='WARD', ascending=True, inplace=True)

    vulnerability = pd.read_csv(vulnerability_indices).drop(['District', 'Upazila'], axis=1).set_index(['Union']).T

    wards['vulnerability']=vulnerability[union].astype(int).to_numpy()

    houses = pd.read_csv(f'./Houses/{union}-household.csv')
    geom = [Point(xy) for xy in zip(houses['Lon'], houses['Lat'])]
    houses_gdf = gpd.GeoDataFrame(houses, crs='EPSG:4326', geometry=geom)

    roads = gpd.read_file(roads_shapefile)

    ## code to prepare inundation and impact data 

    projection = ccrs.PlateCarree()
    fig, axs = plt.subplots(1, 3, dpi = 300 , subplot_kw={'projection': projection})
    # ax = plt.axes(projection = ccrs.PlateCarree())

    inun_gdf=gpd.GeoDataFrame()
    impact_gdf=gpd.GeoDataFrame()

    for id1,id2 in enumerate(gdf_in['inun_lvl']):

        inun = gdf_in[id1:id2]

        # inun.plot(ax=axs[1], color = 'green')


        for idw,ward_no in enumerate(wards.WARD):

            print(f'inundation level {id2}, ward {ward_no}')


            ward = wards[idw:int(ward_no)]
            houses_in_ward = houses_gdf[houses_gdf['ward'] == int(ward_no)]
            houses_in_ward = gpd.overlay(houses_in_ward, ward, how='intersection')

            roads_in_ward = ward.geometry.intersection(roads.unary_union)
            roads_in_ward_len = sum([segment.length for segment in roads_in_ward if segment.is_empty is False])

            #plot exposure elements
            if len(houses_in_ward) != 0:
                houses_in_ward.plot(ax=axs[2], marker = 'o', color='red', transform=projection)
                

            if roads_in_ward_len != 0:
                roads_in_ward.plot(ax=axs[2], facecolor='none', edgecolor='black', transform=projection)

            inun_in_ward = inun.overlay(ward, how='intersection')

            if len(inun_in_ward) == 0:

                print ('found no inundation')
                continue


            #plot inundation
            inun_in_ward['inun_color'] = inun_color(inun_in_ward['inun_lvl'][0])
            inun_in_ward.plot(ax=axs[1], alpha=1, facecolor=inun_in_ward['inun_color'][0],edgecolor='none', transform=projection , label=level(inun_in_ward['inun_lvl'][0]))
            # ward.plot(ax=axs[1], color='none', edgecolor='black')

            #update inundation gdf
            inun_gdf = pd.concat([inun_gdf,inun_in_ward])

            


            if inun_in_ward['inun_lvl'][0] == 4:

                #plot inundation in impact subplot
                inun_in_ward.plot(ax=axs[0], alpha=1, facecolor=inun_in_ward['inun_color'][0],edgecolor='none', transform=projection, label='river')
                continue

            
            
            inun_houses = gpd.sjoin(houses_in_ward, inun_in_ward, how='inner', predicate='intersects')

            inun_roads = inun_in_ward.geometry.intersection(roads.unary_union)
            inun_roads_length = sum([segment.length for segment in inun_roads if segment.is_empty is False])

            ratio_roads = inun_roads_length/(roads_in_ward_len+0.001)

            ratio_houses = len(inun_houses)/(len(houses_in_ward)+1)

            total_exposure = element_exposure(ratio_houses) + element_exposure(ratio_roads)

            inun_in_ward['exposure'] = exposure(total_exposure, element_nos)

            if inun_in_ward['exposure'][0] == 0 :

                print ('found no exposure')
                
                continue

            inun_in_ward['combined_idx'] = combined_score(inun_in_ward['inun_lvl'][0], inun_in_ward['exposure'][0])

        
            # plot impact
            
            inun_in_ward['impact_class'] = impact_score(inun_in_ward['exposure'][0], inun_in_ward['vulnerability'][0])
            inun_in_ward['impact_color'] = impact_color(inun_in_ward['impact_class'][0])
            inun_in_ward.plot(ax=axs[0], facecolor=inun_in_ward['impact_color'][0], edgecolor='none', transform=projection, label = level(inun_in_ward['impact_class'][0]))
            

            #update impact gdf
            impact_gdf=pd.concat([impact_gdf, inun_in_ward])


            del inun_in_ward



    axs[0].set_title(f'impact of {union} union for date {date}', fontsize = 5)
    # axs[0].legend()
    axs[1].set_title(f'inundation of {union} union for date {date}', fontsize = 5)
    # axs[1].legend()
    axs[2].set_title(f'exposure elements of {union} union for date {date}', fontsize = 5)
    # axs[2].legend()

    wards.plot(ax=axs[0], color='none', edgecolor='black')
    for idx, row in wards.iterrows():
        axs[0].annotate(row['WARD'], (row.geometry.centroid.x, row.geometry.centroid.y), color='black', fontsize=5)
    wards.plot(ax=axs[1], color='none', edgecolor='black')
    for idx, row in wards.iterrows():
        axs[1].annotate(row['WARD'], (row.geometry.centroid.x, row.geometry.centroid.y), color='black', fontsize=5)
    wards.plot(ax=axs[2], color='none', edgecolor='black')
    for idx, row in wards.iterrows():
        axs[2].annotate(row['WARD'], (row.geometry.centroid.x, row.geometry.centroid.y), color='black', fontsize=5)



    plt.tight_layout()

    #save plots
    plot_path = f'{plot_output}/{district}_{union}_{date}.png'
    print(plot_path)
    plt.savefig(plot_path)

    # save geodataframes

    inundation_data = inun_gdf.to_json()
    impact_data = impact_gdf.to_json()
    

    return inundation_data, impact_data


def main(date):

    SUFAL_unions_shapefile = './SUFAL_unions/SUFAL_unions.shp'
    roads_shapefile = './raods/SUFAL_lged_roads.shp'
    vulnerability_indices = './Vulnerability_indices.csv' 
    plot_output = './plots'
    geojson_output = './geojson'


    sufal_unions = gpd.read_file(SUFAL_unions_shapefile)
    
    # get a list of houses available
    houses_dir = './Houses/'
    ext_h = '.csv' 
    ext_h2 = '-household'

    print(os.path.join(houses_dir, f"*{ext_h}"))
    houses_files = glob.glob(os.path.join(houses_dir, f"*{ext_h}"))
    houses_available = [os.path.splitext(os.path.basename(x))[0].replace(ext_h2, '') for x in houses_files]
    

    print ('houses available: ', houses_available)

    # get a list of ward shp available
    wards_dir = './ward_shp/'
    ext_w = '.shp'  
    wards_files = glob.glob(os.path.join(wards_dir, f"*{ext_w}"))
    wards_available = [os.path.splitext(os.path.basename(x))[0] for x in wards_files]

    print ('wards available: ', wards_available)

    selected_unions = [x for x in sufal_unions['ADM4_EN'].to_list() if ((x in houses_available) & (x in wards_available))]

    # print (selected_unions)

    available_sufal_unions = sufal_unions[sufal_unions['ADM4_EN'].isin(selected_unions)]

    print ('available unions for impact mapping: ', available_sufal_unions['ADM4_EN'])



    for district in districts:

        print(f'reading inundation geojson for {district} district')

        inun_geojson_path = f"./inundation_output/{date}/inundation_{date}_{district}.geojson"

        gdf = gpd.read_file(inun_geojson_path)

        unions_shp = available_sufal_unions[available_sufal_unions['ADM2_EN']==district]

        for idx,union in enumerate(unions_shp['ADM4_EN']):

            print(f'calculating impact for {union} as of {date} .....')

            inundation_dir=f'{geojson_output}/inundation/{date}/{district}'
            inundation_file_path = f'{inundation_dir}/{union}_{date}_inundation.json'
            impact_dir=f'{geojson_output}/{date}/{district}'
            impact_file_path = f'{inundation_dir}/{union}_{date}_impact.json'

            if not os.path.exists(inundation_dir):
                os.makedirs(inundation_dir)          
            if not os.path.exists(impact_dir):
                os.makedirs(impact_dir)            


            inundation_data, impact_data = impact_inundation(date,district,union, vulnerability_indices=vulnerability_indices, roads_shapefile=roads_shapefile, plot_output=plot_output, gdf=gdf)

            with open(inundation_file_path, 'w') as geojson_file:
                geojson_file.write(inundation_data)

            with open(impact_file_path, 'w') as geojson_file:
                geojson_file.write(impact_data)
        

    return


if __name__=="__main__":

    date = sys.argv[1]
    main(date)

# plt.show()




