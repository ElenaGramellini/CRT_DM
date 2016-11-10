#!/bin/bash

if [ "$1" == "" ]; then
  echo "$0: Please provide file list"
  exit 1
fi

if [ ! -f "$1" ]; then
  echo "$0: $1 is not a file name"
  exit 1
fi

echo "sourcing a bunch of usefull stuff:"
echo "uboone code source and setup"
source /grid/fermiapp/products/uboone/setup_uboone.sh
setup uboonecode v05_08_00 -q e9:prof

echo "launching python get_CRT_metadata.py for file list $1"
python get_CRT_metadata.py $1
