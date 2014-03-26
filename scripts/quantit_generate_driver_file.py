#!/usr/bin/env python
DESC = """EPP script for Quant-iT mesurements to generate a driver file (.csv) 
which include the Sample names and their positions in the working plate.

Reads from:
    --Lims fields--
    "location"      field of input analytes to the process

Writes to:
    --file--
    "Driver File"   shared result file

Logging:
The script outputs a regular log file with regular execution information.

Written by Maya Brandi 
"""

import os
import sys
import logging
import numpy as np

from argparse import ArgumentParser
from requests import HTTPError
from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.entities import Process
from genologics.epp import EppLogger
from genologics.epp import set_field
from genologics.epp import ReadResultFiles
lims = Lims(BASEURI,USERNAME,PASSWORD)

class QunatiT():
    def __init__(self, process, drivf):
        self.udfs = dict(process.udf.items())
        self.abstract = []
        self.no_samples = 0
        self.drivf = drivf

    def make_location_dict(self, io_filtered):
        location_dict = {}
        for input, output in io_filtered:
            try:
                well = output['uri'].location[1]
                sample = input['uri'].name
                row, col = well.split(':')
                location_dict[well] = ','.join([row, col,'', sample])
            except:
                self.no_samples +=1
        return location_dict

    def make_file(self, location_dict):
        keylist = location_dict.keys()
        keylist.sort()
        f = open( self.drivf, 'a')
        print >> f , 'Row,Column,*Target Name,*Sample Name'
        for key in keylist:
            print >> f ,location_dict[key]
        f.close()

def main(lims, pid, drivf ,epp_logger):
    process = Process(lims,id = pid)
    QiT = QunatiT(process, drivf)
    io = process.input_output_maps
    io_filtered = filter(lambda (x,y): y['output-generation-type']=='PerInput', io)
    io_filtered = filter(lambda (x,y): y['output-type']=='ResultFile', io_filtered)
    location_dict = QiT.make_location_dict(io_filtered)
    if QiT.no_samples:
        QiT.abstract.append("Could not get location for {0} samples.".format(QiT.no_samples))
    QiT.make_file(location_dict)

    print >> sys.stderr, ' '.join(QiT.abstract)

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid', default = None , dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('--log', dest = 'log',
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))
    parser.add_argument('--drivf', dest = 'drivf', default = 'QuantiT_driver_file_exported_from_LIMS.csv',
                            help=('File name for Driver file to be generated'))

    args = parser.parse_args()
    lims = Lims(BASEURI,USERNAME,PASSWORD)
    lims.check_version()

    with EppLogger(log_file=args.log, lims=lims, prepend=True) as epp_logger:
        main(lims, args.pid, args.drivf, epp_logger)

