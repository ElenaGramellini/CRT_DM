#!/bin/bash

# Check if at least an argument is supplied
# to this script
if [ -z "$1" ]
  then
    echo "No argument supplied"
    exit 1
fi

if [ "$1" == "" ]; then
  echo "$0: Please provide filename"
  exit 1
fi

if [ ! -f "$1" ]; then
  echo "$0: $1 is not a file name"
  exit 1
fi

# Make sure the file ends in .root
filename=$(basename "$1")
extension="${filename##*.}"
if [ !  $extension == "root" ]
  then 
    echo "Not a root file"
    exit 1
fi


echo "sourcing a bunch of usefull stuff:"
echo "- CRTdaq source and samweb setup" 
source /artdaq_products/setup
setup bernfebdaq v00_03_00 -qe10:s41:eth:prof
setup sam_web_client


# Define here the directory where bad files go to die
badFilesDirectoryPath='/home/elenag/aFarmUpstate/'
#badFilesDirectoryPath='/raid/failedFiles'

# Define here the directory where bad files go to die
badFilesLogsDirectoryPath='/home/elenag/aFarmUpstate/'
#badFilesLogsDirectoryPath='/raid/failedFilesLog'

# The variables CRT_FILE* specify the file location of:
# - the artroot file
# - its metadata (CRT_FILE_JSON)
# - the python program stdout (CRT_FILE_OUT)
# - the python program stderr (CRT_FILE_ERR)
CRT_FILE=$1
CRT_FILE_JSON=$1.json
CRT_FILE_OUT=$1.out
CRT_FILE_ERR=$1.err

echo $CRT_FILE_JSON

echo "launching python get_CRT_metadata.py for file $1"
python get_CRT_metadata.py $1
if [ $? == 0 ]; then
	echo "copying artroot file from CRT EVB to dropbox"
#	ifdh cp $CRT_FILE_JSON /pnfs/uboone/scratch/uboonepro/dropbox/data/uboone/crt
	# Check if artroot file has been copied over to the dropbox	
	if [ $? == 0 ]; then
	    echo "copying json file from CRT EVB to dropbox"
#	ifdh cp $CRT_FILE_JSON /pnfs/uboone/scratch/uboonepro/dropbox/data/uboone/crt
	    # Check if json file has been copied over to the dropbox	
	    if [ $? == 0 ]; then
                # if everything goes smoothly here, you can safely remove the .out and .err
		echo "removing stdout and stderr for shipped file"
		rm $CRT_FILE_OUT
		rm $CRT_FILE_ERR
	    else
		# Ooops, something went wrong, keep the logs!
		echo "$1.json was not shipped to Dropbox">>$CRT_FILE_ERR
		echo "Move files in a farm upstate"
		mv $CRT_FILE     $badFilesDirectoryPath
		mv $CRT_FILE_OUT $badFilesLogsDirectoryPath
		mv $CRT_FILE_ERR $badFilesLogsDirectoryPath
		echo "Send email to the farmer"
		echo $badFilesDirectoryPath | mail -s "CRT Error -- $1.json was not shipped to Dropbox " elenag@fnal.gov
	    fi
	else	       
	    # Ooops, something went wrong, keep the logs!
	    echo "$1 was not shipped to Dropbox">>$CRT_FILE_ERR
	    echo "Move files in a farm upstate"
	    mv $CRT_FILE     $badFilesDirectoryPath
	    mv $CRT_FILE_OUT $badFilesLogsDirectoryPath
	    mv $CRT_FILE_ERR $badFilesLogsDirectoryPath
	    echo "Send email to the farmer"
	    echo $badFilesDirectoryPath | mail -s "CRT Error -- $1 was not shipped to Dropbox " elenag@fnal.gov
	fi
else
    echo "Problems $1 metadata generation"
    echo "Move files in a farm upstate"
    mv $CRT_FILE     $badFilesDirectoryPath
    mv $CRT_FILE_OUT $badFilesLogsDirectoryPath
    mv $CRT_FILE_ERR $badFilesLogsDirectoryPath
    echo "Send email to the farmer"
    echo $badFilesLogsDirectoryPath | mail -s "CRT Error -- Problems with $1 metadata generation " elenag@fnal.gov
fi