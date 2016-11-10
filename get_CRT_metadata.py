#! /usr/bin/env python
"""@package docstring
Scope of this python script: create metadata from a list of CRT raw files
Author: Elena Gramellini
Creation Date: 2016-11-07 
Version 0 
-----------------------------------------------------------------------
TO DO:
[   ] Understand how to setups without root permission
[   ] Run the dump command
[   ] Read the dump output
[   ] Fill variables:
      [   ]  run           
      [   ]  subrun        
      [   ]  sevt          
      [   ]  stime         
      [   ]  etime         
      [   ]  eevt           
      [   ]  num_events         
      [   ]  ver      
      [   ]  file_format
      [   ]  ub_project_version 
      [   ]  gps_stime_usec     
      [   ]  gps_etime_usec     
[   ] undestand output format

functions:
dumpEvent()
readEventDump(string)
createMetadata()
main

"""   

my_little_python_script_version = "CRT_Metadata_1.0"
# python include
import time, os, shutil, sys, gc
import pprint
import subprocess

#os.system("source /grid/fermiapp/products/uboone/setup_uboone.sh")
    #os.system("source /artdaq_products/setup")
    # source setup and setup uboonecode and CRTdaq code 

    #os.system("setup bernfebdaq v00_03_00 -qe10:s41:eth:prof")

    ###########os.system("setup uboonecode v05_08_00 -q e9:prof")


import datetime, json
import argparse

# samweb include
import samweb_cli
import samweb_client.utility
import extractor_dict
import subprocess






def createMetadata(in_file):    
    ################  Retreive the file size ################ 
    fsize          = os.path.getsize(in_file) 
    ##################  Define the run type ##################
    in_file_split = os.path.basename(in_file).split('_')
    if in_file_split[1]=='bernfebdaq':
        run_type='physics'
    else:
        run_type='unknown'
        

    ##################  Define the checksum ##################
    checksum       = -1
    metadata = {}
    try:
        metadata['crc'] = samweb_client.utility.fileEnstoreChecksum( in_file )
        checksum = metadata['crc']['crc_value']
        statusCode = 0
    except Exception:
        errorMessage = traceback.print_exc()
        subject = 'Failed to obtain the checksum of the file %s' % in_file
        text = """File: %sError message: %s""" % ( in_file, errorMessage )
        statusCode = 100

   ##################  Read the dump file ##################
   ##################  WARNING, THIS IS BOGUS ##################
   #     dump_first_evt = []
   #     dump_last_evt = []
   #     with open(args.file_dump) as inputdump:
   #         for line in inputdump:
   #             dump_first_evt.append(line.rstrip('\n'))
   #             dump_last_evt.append(line.rstrip('\n'))
   ##########################################################
        


    eventdump(in_file,0)

    run            = "Wait for Wes" #run of first event
    subrun         = "Wait for Wes" #subrun of first event
    sevt           = -1  # first event (in uboone 0)
    stime          = -1  # first event time stamp --> check the format, up to seconds
    etime          = -1  # last event time stamp --> check the format, up to seconds
    eevt           = -1  # last event (in uboone 49)
    num_events     = -1  # CRT events are not sequential... I need to come up with a way...
    ver                = -1 # daq version
    gps_stime_usec     = -1
    gps_etime_usec     = -1 
    file_format = "not sure, need to talk to Wes"
                

    jsonData = {'file_name': os.path.basename(in_file), 
                'file_type': "data", 
                'file_size': fsize, 
                'file_format': file_format, 
                'runs': [ [run,  subrun, run_type] ], 
                'first_event': sevt, 
                'start_time': stime, 
                'end_time': etime, 
                'last_event':eevt, 
                'group': 'uboone', 
                "crc": { "crc_value":str(checksum),  "crc_type":"adler 32 crc type" }, 
                "application": {  "family": "online",  "name": "crt_assembler", "version": ver }, 
                "data_tier": "raw", "event_count": num_events,
                "ub_project.name": "online", 
                "ub_project.stage": "crt_assembler", 
                "ub_project.version": my_little_python_script_version ,
                'online.start_time_usec': str(gps_stime_usec),
                'online.end_time_usec': str(gps_etime_usec)
                }
    
    
    for i in jsonData:
        print i, jsonData[i]
    print 
    print

    jsonFileName = os.path.basename(in_file) + ".json"
    with open(jsonFileName, 'w') as outfile:
        json.dump(jsonData, outfile)



def eventdump(infile,skipEvents):
    cmd = "art -c RunTimeCoincidence.fcl -s "+infile + " -n 1 "+ "--nskip "+str(skipEvents)
    print cmd
    p = subprocess.Popen([cmd, ''],
                         stdout=subprocess.PIPE,  
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    print out


if __name__ == '__main__':
    # This code takes as an argument the list of file 
    # we need to generate metadata for
    parser = argparse.ArgumentParser()
    parser.add_argument("file_list", help="this is the list of files you want to generate metadata for")
    args = parser.parse_args()


    in_file_v = []
    with open(args.file_list) as inputlist:
        for line in inputlist:
            in_file_v.append(line.rstrip('\n'))
            
    for in_file in in_file_v:
        createMetadata(in_file)
