#!/usr/bin/python
# -------------------------------------------------------------------------------
# Name:        Isilon Modify Exports to replace IP's with Hostnames
# Purpose:     Backup and restore NFS exports on Isilon using RESTful services.
#
# Author:      John Hartrey
#
# Version:     1.0
#
# Created:     07.03.2019 
#
# Licence:     Open to distribute and modify.  This example code is unsupported
# by both EMC and the author.  IF YOU HAVE PROBLEMS WITH THIS
# SOFTWARE, THERE IS NO ONE PROVIDING TECHNICAL SUPPORT FOR
#              RESOLVING ISSUES. USE CODE AS IS!
#
#              THIS CODE IS NOT AFFILIATED WITH EMC CORPORATION.
#-------------------------------------------------------------------------------
import isilon
import logging.handlers
import logging
import time
import argparse
import json
import os
import socket
from isilon.exceptions import Syntax

formatted_time = time.strftime('%Y-%m-%d_%H-%M')
# Set up a specific logger with our desired output level
my_logger = logging.getLogger('logger_agent')

def change_exports(args):
    count = 0
    try:
        bckfile = open(args.file, 'r')
    except IOError:
        my_logger.critical("Backup file " + args.file + " doesn't exist!\n")
        raise Exception("Backup file " + args.file + " doesn't exist!")
    my_logger.info("Change Exports operation started on Isilon...")
    my_logger.info("Opening backup file " + bckfile.name + "...")
    outfilename = args.file + '.out'
    outfile = open(outfilename, 'w')
    for line in bckfile:
        ip_name = []
        line = line.replace('\n', '')
        obj = json.loads(line)
        clients = obj['clients'] + obj['root_clients']
        for ip in clients:
          try:
            name_ip = socket.gethostbyaddr(ip)[0]
          except :
            name_ip = ip
          ip_name.append(name_ip)
        outfile.write('Export Path {}'.format(json.dumps(obj['paths'])))
        #outfile.write('Clients {}'.format(json.dumps(clients)))
        outfile.write(' Client Names {}\n'.format(ip_name))
        #outfile.write(json.dumps(obj))
        #print('Export Path {}'.format(obj['paths']))
        #print('Clients {}\n'.format(obj['clients']))
        #my_logger.info("Object ID " + obj.id + "\n")
        count += 1
    outfile.close()
    my_logger.info("Total objects: " + str(count))
    my_logger.info("Closing backup file " + bckfile.name + "...")
    my_logger.info("Restore operation to Isilon was finished!")
    return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="detailed logging.", action='store_true', required=False )
    group1 = parser.add_argument_group("Required")
    group1.add_argument("-f", "--file", help="Path to the backup file for restore operation.", action='store', required=True, dest='file')
    args = parser.parse_args()
    
    LOG_FILENAME = 'change_exports' + '.log'

    # Add the log message handler to the logger
    handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=52428800, backupCount=100)

    # create a logging format
    formatter = logging.Formatter('%(levelname)s %(asctime)s --> %(message)s')
    handler.setFormatter(formatter)
    my_logger.addHandler(handler)

    if args.verbose:
        my_logger.setLevel('DEBUG')
    else:
        my_logger.setLevel('INFO')
    my_logger.info('------------------------------------- Isilon Tools -------------------------------------')
    change_exports(args)
    my_logger.info("review "+LOG_FILENAME+" for more information.")
main()
