
#!/bin/ bash
# -- Tank-Model automation script --
# -- for ecmwf-ens+ensext data --
# -- developed under SUFAL-II project --
# -- Alvee Bin Hannan <alveehannan@gmail.com>

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd $SCRIPT_DIR

source env.sh


#DATE=$1
#YEAR=`date +'%Y' -d "${DATE}"` # doesnt work on macos

DATE=$1
#PASSWORD=$2
YEAR=`date +'%Y' -d "${DATE}"`


CPC_DIR="./nc_data/cpc"
ENS_DIR="./nc_data/ecmwf_ens/${DATE}"
ENSEXT_DIR="./nc_data/ecmwf_ensext/${DATE}"

mkdir -p $ENS_DIR
mkdir -p $ENSEXT_DIR

 # define cpc data url and files
CPC_PRECIP_DOWNLOAD_URL="https://downloads.psl.noaa.gov/Datasets/cpc_global_precip/precip.${YEAR}.nc"
CPC_TMAX_DOWNLOAD_URL="https://downloads.psl.noaa.gov/Datasets/cpc_global_temp/tmax.${YEAR}.nc"
CPC_TMIN_DOWNLOAD_URL="https://downloads.psl.noaa.gov/Datasets/cpc_global_temp/tmin.${YEAR}.nc"

CPC_PRECIP_OUT_FILE="${CPC_DIR}/precip.${DATE}.nc"
CPC_TMAX_OUT_FILE="${CPC_DIR}/tmax.${DATE}.nc"
CPC_TMIN_OUT_FILE="${CPC_DIR}/tmin.${DATE}.nc"
CPC_ET0_OUT_FILE="${CPC_DIR}/et0.${DATE}.nc"

# remove old files if exists
rm -f $CPC_PRECIP_OUT_FILE $CPC_TMIN_OUT_FILE $CPC_TMAX_OUT_FILE

# downloading files
wget -q --show-progress $CPC_PRECIP_DOWNLOAD_URL -O $CPC_PRECIP_OUT_FILE
wget -q --show-progress $CPC_TMAX_DOWNLOAD_URL -O $CPC_TMAX_OUT_FILE
wget -q --show-progress $CPC_TMIN_DOWNLOAD_URL -O $CPC_TMIN_OUT_FILE

echo "CPC data downloaded"

# generate et0 nc file

if [[ ! -f $CPC_TMAX_OUT_FILE ]]; then
    echo "TMAX file not available / downloading ..."
    exit 10 
fi

if [[ ! -f $CPC_TMIN_OUT_FILE ]]; then
    echo "TMIN file not available / downloading ..."
    exit 20
fi 

if [[ ! -f $CPC_PRECIP_OUT_FILE ]]; then
    echo "PRECIP file not available"
    exit 30 
fi 

echo "Generating et0 file.."

cpc_et.py -tn $CPC_TMIN_OUT_FILE -tx $CPC_TMAX_OUT_FILE -o $CPC_ET0_OUT_FILE


echo "et0 file created, copying nc data.. "



# # copy data from server
# rm $ENS_DIR/*

scp -r "mmb@203.159.16.139:/home/mmb/@data/ecmwf_ensext/${DATE}/R1F*" $ENSEXT_DIR

scp -r "nazmul@203.159.16.180:/home/nazmul/@data/ecmwf_ens/${DATE}/R1E*" $ENS_DIR

# data download completed
# now do automation with python

#bash plot_for_bulletin.sh

python3 run_model.py ${DATE}

python3 exceedence_plot.py ${DATE}
exit 100
