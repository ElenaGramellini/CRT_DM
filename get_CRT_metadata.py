#! /usr/bin/env python3
"""@package docstring
Scope of this python script: create metadata one CRT raw file
Author: Elena Gramellini
Creation Date: 2016-11-07 
Version 0 
-----------------------------------------------------------------------
TO DO:
[   ] Understand the stupid email....
[   ] Fill variables:
      [   ]  stime         
      [   ]  etime         
      [   ]  ver --> needs work on the DAQ side!!!!      
      [   ]  gps_stime_usec     
      [   ]  gps_etime_usec     
[   ] implement checks:
      [   ]  did the subprocess command hang ? --> process timeout, check status
      [   ]  is the fcl file right?is the file corrupted? probably in the same part
      [ x ]  write filename.out filename.err to report problems
      [ x ]  handle file not found
      [ x ]  is json format right for sam?
      [   ]  time out for metadata validation

Functions:
x dumpEvent(input_file, skipEvents):
   This function runs the shell command 
   $ art -c SAMMetaDataDump.fcl  -s input_file  -n 1  --nskip skipEvents
   and returns its stdout. 
   This art command dumps information about the event which are used to fill the metadata

x fileEventCount(input_file):
   This function runs the shell command 
   $ count_events input_file
   and returns the 4th world of its stdout, which is the number of art events in the file

- matadataValidation(input_file):
   This function exits with error 
    x if the metadata file doesn't exist
    x if the SAM metadata-validation goes wrong
    - if the SAM metadata-validation takes too much time

-  createMetadata(input_file):
   1) Aquires the metadata from  file name and location
   2) calls dumpEvent(input_file, 0) to get info on first event
   3) calls fileEventCount(input_file) to get number of events to skip
   4) calls dumpEvent(input_file, nskip) to get info on last event
   5) writes out metadata

x main:
  x checks if the argument is a file (if not exit with error)
  x opens the writings of the stdout and stderr for logging purposes
  x calls createMetadata(input_file)
  x calla matadataValidation(in_file,jsonData)
 

"""   

my_little_python_script_version = "CRT_Metadata_1.0"
# python include
import time, os, shutil, sys, gc
import pprint
import subprocess
import datetime, json
import argparse
import warnings
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
    
    run            = "Bogus"   # run of first event
    subrun         = "Bogus"   # subrun of first event
    sevt           = "Bogus"   # first event
    eevt           = "Bogus"   # last event 
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
        if "CRTDAQVersion" in line:
            w   = line.split()
            ver = w[3]+"_"+w[7]+"_"+w[11]
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
    gps_stime_usec = round(nsTimeStampsFirst[0]/1000)
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
    gps_etime_usec = round(nsTimeStampsLast[len(nsTimeStampsLast)-1]/1000)

    ##################  Define file_format as Wes said ##################   
    file_format = "artroot"

    ##################  Fill the metadata ##################   
    jsonData = {'file_name': os.path.basename(in_file), 
                'file_type': "data", 
                'file_size': fsize, 
                'file_format': file_format, 
                'runs': [ [ run, subrun, run_type] ], 
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
    jsonFileName = str(in_file) + ".json"
    with open(jsonFileName, 'w') as outfile:
        json.dump(jsonData, outfile)
    ################## Return metadata object ##################   
    return jsonData



# Dump DAQ file content for 1 event given:
# - the DAQ file name
# - the number of events we want to skip
def eventdump(infile,skipEvents):
    cmd = "art -c SAMMetaDataDump.fcl -s "+infile + " -n 1 "+ "--nskip "+str(skipEvents)
    p = subprocess.Popen(cmd,shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out

# Count events in DAQ file given:
# - the DAQ file name
def fileEventCount(infile):
    cmd = "count_events "+infile
#    seconds=10 # works only in python3
#    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=seconds)
    
    p = subprocess.Popen(cmd,shell=True,
                         stdout=subprocess.PIPE)
    out, err = p.communicate()
    return out.split()[3]


def matadataValidation(infile,jsonData):
    jsonFileName = str(infile)+".json"
    # Check if we actually generated the json file
    # If not, exit with error
    if not  os.path.isfile(jsonFileName): 
         sys.exit(in_file +": Metadata File Not Found")
    # Set up the experiment for the SAM
    samweb = samweb_cli.SAMWebClient(experiment="uboone")
    # Check if metadata is valid, or exit with error
    try:
        samweb.validateFileMetadata(jsonData)       
        return True
    except Exception:
        sys.exit(in_file +" : Invalid/Corrupted Metadata")


if __name__ == '__main__':
    # This code takes as an argument the file 
    # we need to generate metadata for
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="this is the name of the file you want to generate metadata for")
    args = parser.parse_args()
    in_file = args.filename

    # We want to write the stdout and stderr 
    # for logging purposes in case something goes wrong
#    sys.stdout = open(in_file+".out", 'w')
#    sys.stderr = open(in_file+".err", 'w')
    
    print in_file
    # Check if file exists, or exit with error
    if os.path.isfile(in_file): 
        jsonData = createMetadata(in_file)
        matadataValidation(in_file,jsonData)
    else:
        sys.exit(in_file+" : File Not Found")
        

'''
DONE:
[ x ] Re-write launch script with checks
[ x ] Understand how to setups without root permission
[ x ] Run the dump command
[ x ] Read the dump output
[   ] Fill variables:
      [ x ]  run           
      [ x ]  subrun        
      [ x ]  sevt          
      [   ]  stime         
      [   ]  etime         
      [ x ]  eevt           
      [ x ]  num_events         
      [   ]  ver      
      [ x ]  file_format
      [ x ]  ub_project_version 
      [   ]  gps_stime_usec     
      [   ]  gps_etime_usec     
[ x ] undestand output format
[   ] implement checks:
      [   ]  did the subprocess command hang ? --> process timeout, check status
      [   ]  ?????????????????????????????????????????????????????????????????????????is the fcl file right ?
      [ x ]  how can I report the error ?
      [ x ]  handle file not found
      [   ]  is the artroot file corrupted
      [ x ]  are the metadata valid for SAM?
      [   ]  time out for metadata validation

'''
