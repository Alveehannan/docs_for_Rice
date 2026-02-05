import sys,os
from netCDF4 import Dataset
import pylab as pl
from cartopy import crs as ccrs
import numpy as np
import pandas as pd
import geopandas as gpd
from inundation_fill2_V2 import inundation_4cf as inundation_4cf_v2
import geojsoncontour
import json
from matplotlib.colors import ListedColormap as lcmp
# from shapely import geometry

# date='20230901'
districts = [ 'Jamalpur','Bogra','Kurigram', 'Gaibandha']


def inun(date, district, raster_dem):
    
    # read dem
    raster = Dataset(raster_dem,'r')

    elev_all = raster.variables['elev'][:] # + 0.22
    lon_all = raster.variables['lon'][:]
    lat_all = raster.variables['lat'][:]


    SUFAL_unions = './SUFAL_unions/SUFAL_unions.shp'
    water_levels = f'./water_levels/water_levels_{date}.csv'
    inun_plot_output = f'./inundation_plot_output/inundation_{date}_{district}.png'
    


    gdf=gpd.read_file(SUFAL_unions)

    unions = gdf[(gdf['ADM2_EN'] == district)]
    bbox_1 = unions.total_bounds

    # print(bbox_1)
    # print(round(max(lat_all)))

    df_wl = pd.read_csv(water_levels)
    df_wl.sort_values(by=['lat'], ascending=False, inplace=True)
    df_wl['WL'] = df_wl.set_index('bed_elev')['WL'].interpolate('index').values

    # select region of interest
    up = min(bbox_1[3] + 0.05 , max(lat_all))
    bot = max(bbox_1[1] - 0.05 , min(lat_all))


    # select propagation points
    points = df_wl[(df_wl['lat'] <= up) & (df_wl['lat'] >= bot)]
    points.reset_index(drop=True, inplace =True)

    print (f'propagation points: ', points)

    lat_select = lat_all[(lat_all >= bbox_1[1]) & (lat_all <= up)]



    # return

    # df = pd.DataFrame()
    fig = pl.figure(dpi=600)
    ax = pl.axes(projection = ccrs.PlateCarree())
    bbox = unions.total_bounds

    cnt_list = []


    for idx,row in points.iterrows():
        LLATT = row.lat
        LLONN = row.lon
        WL = row.WL
        if idx < max(points.index):
            next_lat = points['lat'][idx+1]
        
        elif idx == max(points.index):
            next_lat = bot


        #getting lat, lon and elev for current strip for regular case

        lat = lat_all[(lat_all <= (LLATT)) & (lat_all > (next_lat))]
        lon = lon_all[(lon_all > (LLONN-0.1)) & (lon_all < (LLONN+0.2))]

        lat_in = [i for i, x in enumerate(lat_all) if x in lat]
        lon_in = [i for i, x in enumerate(lon_all) if x in lon]

        elev = elev_all[np.ix_(lat_in,lon_in)]

        x_euclid = (lon - LLONN)**2
        y_euclid = (lat - LLATT)**2

        x_pos = np.where(x_euclid == x_euclid.min())
        y_pos = np.where(y_euclid == y_euclid.min())

        x_id = x_pos[0][0]
        y_id = y_pos[0][0]

        print (f'calculating inun depth for ${LLATT}, ${LLONN} for a WL of ${WL}')


        # calculate inundation for current strip

        inun=inundation_4cf_v2(elev, (y_id, x_id))

        inun_depth=inun.depth(WL)

        # create boolean mask with conditions:

        # new mask (4/9/23):
        rivercourse = (inun_depth > 3)
        high = (inun_depth > 1) & (inun_depth <= 3)
        medium = (inun_depth <= 1) & (inun_depth > 0.5)
        low = (inun_depth <= 0.5) & (inun_depth > 0)
        none = (inun_depth == 0)
    

        bmask = np.zeros(inun_depth.shape, dtype=int)
        bmask[high] = 3
        bmask[medium] = 2
        bmask[low] = 1
        bmask[rivercourse] = 4
        bmask[none] = 0

        colors = ['#FFFFFF', '#FFFF00', '#FF7F50', '#FF0000', '#00008B']

        cmap = lcmp(colors)

        levels = np.linspace(0,4,5)

        cnt = pl.contourf(lon, lat, bmask, levels=5, cmap = cmap)

        gj_file = geojsoncontour.contourf_to_geojson(contourf=cnt, ndigits=5, unit='m')

        cnt_list.append(gj_file)

        print (f'${idx} done')



    colorbar = fig.colorbar(cnt, orientation='horizontal')
    colorbar.set_ticks(levels)
    colorbar.set_label('Inundation')
    unions.plot(ax=ax, color='none', edgecolor='black')

    pl.xlim(bbox[0], bbox[2])
    pl.ylim(bbox[1], bbox[3])


    for idx, row in unions.iterrows():
        pl.annotate(row['ADM4_EN'], (row.geometry.centroid.x, row.geometry.centroid.y), color='black', fontsize=4)


    gl = ax.gridlines(draw_labels=True, linewidth = 0.01)
    sv = pl.savefig(inun_plot_output)


    #save plot as geojson

    json_file = json.loads(cnt_list[0])

    

    for idx, item in enumerate(cnt_list[1:]):

        # print (idx)


        json1 = json.loads(item)

        for i in range(len(json1['features'])):

            # print (len(json_file['features'][i]['geometry']['coordinates']))

            new = json1['features'][i]['geometry']['coordinates']
            # print (i)
            json_file['features'][i]['geometry']['coordinates'].extend(new)

    return json_file


def main(date):

    for district in districts:

        print(f'calculating inundation for {district} with WL forecast of {date} ....')

        raster_dem = f'./dem/{district}.nc'

        inundation_path = f'./inundation_output/{date}'

        if not os.path.exists(inundation_path):
            # Create the directory
            os.mkdir(inundation_path)

        inun_geojson_output = f"{inundation_path}/inundation_{date}_{district}.geojson"

        json_file = inun(date,district,raster_dem)

        print(f'saving geojson ...')
        with open(inun_geojson_output, "w") as geojson_file:
            json.dump(json_file, geojson_file, indent=4)
            print(inun_geojson_output)

        break
    return
        


if __name__ == '__main__':

    date=sys.argv[1]
    main(date)