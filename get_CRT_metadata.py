#! /usr/bin/env python
"""@package docstring
Scope of this python script: create metadata from a list of CRT raw files
Author: Elena Gramellini
Creation Date: 2016-11-07 
Version 0 
-----------------------------------------------------------------------
TO DO:
[   ] Understand how to setups without root permission
[ x ] Run the dump command
[ x ] Read the dump output
[   ] Fill variables:
      [ x ]  run           
      [ x ]  subrun        
      [ x ]  sevt          
      [ x ]  stime         
      [ x ]  etime         
      [ x ]  eevt           
      [ x ]  num_events         
      [   ]  ver      
      [   ]  file_format
      [ x ]  ub_project_version 
      [   ]  gps_stime_usec     
      [   ]  gps_etime_usec     
[ x ] undestand output format


Functions:
x dumpEvent(input_file, skipEvents):
   This function runs the shell command 
   $ art -c RunTimeCoincidence.fcl -s input_file  -n 1  --nskip skipEvents
   and returns its stdout. 
   This art command dumps information about the event which are used to fill the metadata

x fileEventCount(input_file):
   This function runs the shell command 
   $ count_events input_file
   and returns the 4th world of its stdout, which is the number of art events in the file

-  createMetadata(input_file):
   1) Aquires the metadata from  file name and location
   2) calls dumpEvent(input_file, 0) to get info on first event
   3) calls fileEventCount(input_file) to get number of events to skip
   4) calls dumpEvent(input_file, nskip) to get info on last event
   5) writes out metadata

x main:
  parses the input file list and calls createMetadata(input_file) for each file in such list

"""   

my_little_python_script_version = "CRT_Metadata_1.0"
# python include
import time, os, shutil, sys, gc
import pprint
import subprocess
import datetime, json
import argparse

# samweb include
import samweb_cli
import samweb_client.utility
#import extractor_dict


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
    
    run            = "Bogus" #run of first event
    subrun         = "Bogus" #subrun of first event
    sevt           = "Bogus"  # first event (in uboone 0)
    eevt           = "Bogus"  # last event (in uboone 49)
    stime = etime = '1970-01-01:T00:00:00'
    gps_etime = gps_etime_usec = gps_etime_secs = -1
    gps_stime = gps_stime_usec = gps_stime_usec = -1

    num_events     = fileEventCount(in_file)  # CRT events are not sequential...
    events_to_skip = int(num_events) - 1

    # TO DO
    ver                = -1 # daq version

  

    ##################  Read the dump file for first event ##################   
    nsTimeStampsFirst = [] 
    flagFirstEvent = True
    first_evt_dump = eventdump(in_file,0).split('\n') 
    for line in  first_evt_dump:
        if "run:" in line:
            w   = line.split()
            run    = int(w[w.index("run:")+1])           
            subrun = int(w[w.index("subRun:")+1])
            sevt   = int(w[w.index("event:")+1])
        if "time" in line:
            w   = line.split()
            if (flagFirstEvent):
                stime_secs_tmp = int(w[w.index("s,")-1])
                stime = datetime.datetime.fromtimestamp(stime_secs_tmp).replace(microsecond=0).isoformat()
                flagFirstEvent = False
            if "Event 0" in line:
                nsTimeStampsFirst.append(float(w[w.index("ns.")-1]))

    nsTimeStampsFirst.sort()
    print nsTimeStampsFirst[0], nsTimeStampsFirst[len(nsTimeStampsFirst)-1]


    
    ##################  Read the dump file for last event ##################   
    prevLine = ""
    nsTimeStampsLast = []
    flagLastEvent = True
    last_evt_dump = eventdump(in_file,events_to_skip).split('\n') 
    for line in  last_evt_dump:
        if "run:" in line:
            w   = line.split()
            eevt   = int(w[w.index("event:")+1])
        if "time" in line:
            w   = line.split()
            if (flagLastEvent):
                etime_secs_tmp = int(w[w.index("s,")-1])
                etime = datetime.datetime.fromtimestamp(etime_secs_tmp).replace(microsecond=0).isoformat()
                flagLastEvent = False        
            if "Event 0" in line:
                wo = prevLine.split()
                if "ns." in wo:
                    nsTimeStampsLast.append(float(wo[wo.index("ns.")-1]))
        prevLine = line

    nsTimeStampsLast.sort()
    #You're still missing one event
    print nsTimeStampsLast[0], nsTimeStampsLast[len(nsTimeStampsLast)-1]
            

    ##################  Define file_format as Wes said ##################   
    file_format = "artroot"

    ##################  Fill the metadata ##################   
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
    
    ################## Create the json file containing the metadata ##################   
    jsonFileName = os.path.basename(in_file) + ".json"
    with open(jsonFileName, 'w') as outfile:
        json.dump(jsonData, outfile)


# Dump DAQ file content for 1 event given:
# - the DAQ file name
# - the number of events we want to skip
def eventdump(infile,skipEvents):
    cmd = "art -c RunTimeCoincidence.fcl -s "+infile + " -n 1 "+ "--nskip "+str(skipEvents)
    p = subprocess.Popen(cmd,shell=True,
                         stdout=subprocess.PIPE)
    out, err = p.communicate()
    return out

# Count events in DAQ file given:
# - the DAQ file name
def fileEventCount(infile):
    cmd = "count_events "+infile
    p = subprocess.Popen(cmd,shell=True,
                         stdout=subprocess.PIPE)
    out, err = p.communicate()
    return out.split()[3]

if __name__ == '__main__':
    # This code takes as an argument the list of file 
    # we need to generate metadata for
    parser = argparse.ArgumentParser()
    parser.add_argument("file_list", help="this is the list of files you want to generate metadata for")
    args = parser.parse_args()

    # Read filelist
    in_file_v = []
    with open(args.file_list) as inputlist:
        for line in inputlist:
            in_file_v.append(line.rstrip('\n'))
            
    # Create metadata for each file in the filelist
    for in_file in in_file_v:
        createMetadata(in_file)
