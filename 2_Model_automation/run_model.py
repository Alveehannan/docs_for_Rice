#!/usr/bin/env python3
'''
Model Operation Script for CPC + ECMWF ENS + ENS-Extended-data
Project: SUFAL-II
'''

import os,sys

from pathlib import Path
import fiona
import pickle

from tank_core import io_helpers as ioh
from tank_core import computation_helpers as ch
from automated_tank.base_config import *
import automated_tank.cpc_processor as cpc_
import automated_tank.ecmwf_processor as ecmf_
from tank_core.global_config import DATE_FMT
from automated_tank.plotter import plot_output_box
from automated_tank.states_pkl2csv import pkl2csv
'''
STEPS:
------
- download data
- create csv for cpc+ens+ensext
- simulate for each ensemble
- error correction
- plot data 
'''

import pandas as pd
from datetime import datetime as dt


def main(date):
    '''Computes tank model for ensemble data'''
    # get project root directory

    print(f'\n### SIMULATING MODEL FOR DATE {date} ###\n')

    date_obj = dt.strptime(date+'+0000', '%Y%m%d%z')
    cut_timestamp = pd.Timestamp(date_obj.strftime(DATE_FMT))

    project_dir = Path(PROJECT_FILE).resolve().parent
    print(project_dir)
    print(OUTPUT_DATA_PATH)
    
    project = ioh.read_project_file(PROJECT_FILE)
    basin_file = project_dir / project['basin']
    precipitation_file = project_dir / project['precipitation']
    evapotranspiration_file = project_dir / project['evapotranspiration']
    discharge_file = project_dir / project['discharge']
    statistics_file = project_dir / project['statistics']
    result_file =project_dir / project['result'] 
    #states_file =project_dir / project['states']
    basin = ioh.read_basin_file(basin_file)

    basin_shapefile = fiona.open(BASIN_SHAPEFILE,'r')

    # create dirs
    if not os.path.exists(INPUT_DATA_PATH.format(date=date)):
        os.makedirs(INPUT_DATA_PATH.format(date=date))

    if not os.path.exists(OUTPUT_DATA_PATH.format(date=date)):
        os.makedirs(OUTPUT_DATA_PATH.format(date=date))

    if not os.path.exists(OUTPUT_PLOT_PATH.format(date=date)):
        os.makedirs(OUTPUT_PLOT_PATH.format(date=date))
    
    if not os.path.exists(OUTPUT_STATES_PATH_PKL.format(date=date)):
        os.makedirs(OUTPUT_STATES_PATH_PKL.format(date=date))

    if not os.path.exists(OUTPUT_STATES_PATH_CSV.format(date=date)):
        os.makedirs(OUTPUT_STATES_PATH_CSV.format(date=date))        

    # update precipitation and evapotranspiration base files
    cpc_pr_data =  cpc_.process_cpc_pr(date, precipitation_file, basin_shapefile)
    
    cpc_pr_date_filtered = cpc_pr_data[cpc_pr_data.index <= cut_timestamp ]

    cpc_et_data = cpc_.process_cpc_et(date, evapotranspiration_file, basin_shapefile)

    cpc_et_date_filtered = cpc_et_data[cpc_et_data.index <= cut_timestamp]
    
    discharge, _ = ioh.read_ts_file(discharge_file,check_time_diff=False)

    root_node_data = pd.DataFrame()

    for i_ens in range(NUM_ENS):
        
        print(f' ----\n ---- processing ensemble #{i_ens:02d}\n ---- ')
        
        ens_pr, ens_et, pr_data_360hr = ecmf_.process_ec_ens_pr_et(date, i_ens, basin_shapefile)
        ensext_pr, ensext_et = ecmf_.process_ec_ensext_pr_et(date, i_ens, basin_shapefile, pr_data_360hr)
        
        precipitation = pd.concat( [cpc_pr_date_filtered, ens_pr, ensext_pr] )

        evapotranspiration = pd.concat( [cpc_et_date_filtered, ens_et, ensext_et] )
        
        # save pr and et data for future diagnostic
        ioh.write_ts_file(precipitation, INPUT_DATA.format(date=date, type='pr',ens_no=i_ens))
        ioh.write_ts_file(evapotranspiration, INPUT_DATA.format(date=date, type='et',ens_no=i_ens))

        #  compute model
        computation_result, basin_states = ch.compute_project(basin, precipitation, evapotranspiration, 24)

        # write output data
        ioh.write_ts_file(computation_result, OUTPUT_DATA.format(date=date, ens_no=i_ens))
        
        # states_dir = OUTPUT_DATA_PATH.format(date=date)

        with open( OUTPUT_STATES_PKL.format(date=date, ens_no=i_ens), 'wb') as pkl_handler:
            pickle.dump(basin_states, pkl_handler, protocol=pickle.HIGHEST_PROTOCOL)
        
        pkl2csv(OUTPUT_STATES_PKL.format(date=date, ens_no=i_ens), OUTPUT_STATES_CSV.format(date=date, ens_no=i_ens))
        
	    
        if 'Time' not in root_node_data.keys():
            root_node_data['Time'] = computation_result.index
        
        
        root_node_data[f'EN#{i_ens:02d}'] = computation_result['BAHADURABAD'].to_numpy()
        statistics = ch.compute_statistics(basin=basin, result=computation_result, discharge=discharge)

        ioh.write_ts_file(computation_result,result_file)
     
#         print( 
#             tabulate(
#                 [
#                     ('NSE', statistics['BAHADURABAD']['NSE']),
#                     ('RMSE', statistics['BAHADURABAD']['RMSE']),
#                     ('R2', statistics['BAHADURABAD']['R2']),
#                     ('PBIAS', statistics['BAHADURABAD']['PBIAS']),
#                 ],
#                 headers=['Statistics', 'BAHADURABAD'], tablefmt='psql'
#             ) 
#         )

#         with open(statistics_file,'w') as stat_file_write_buffer:
#             json.dump(statistics, stat_file_write_buffer, indent=2)

    root_node_data.set_index('Time', inplace=True)

    plot_output_box(root_node_data, date_obj)

    root_node_data_path = OUTPUT_DATA_PATH.format(date=date)
    ioh.write_ts_file(root_node_data,f'{root_node_data_path}/all_en_bahadurabad.csv')



if __name__ == '__main__':
    date=sys.argv[1]
    main(date)
