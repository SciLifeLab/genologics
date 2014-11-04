#!/usr/bin/env python
DESC = """This EPP script reads Application QC files from file
system and sets the qc values for each sample. Allso a a easy to read App QC 
file is generated with more information about the application specific qc that 
was done. The file is suposed to be a help file in case of failed QC -flaggs.

Logging:
    The script outputs a regular log file with regular execution information.

Written by Maya Brandi (14-10-14)
"""

import os
import sys
import logging
import glob
import csv
import json

from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process
from genologics.epp import EppLogger
from genologics.epp import set_field

class AppQC():
    def __init__(self, process):
        self.app_QC = {}
        self.project_name = process.all_outputs()[0].samples[0].project.name
        self.target_files = dict((r.samples[0].name, r) for r in process.all_outputs())
        self.missing_samps = []
        self.nr_samps_updat = 0
        self.abstract = []
        self.process = process
        self.nr_samps_tot = str(len(self.target_files))
        self.QF_from_file = {}

    def get_app_QC_file(self):
        """ App QC file is read from the file msf system. Path hard coded."""
        file_path = ("/srv/mfs/app_QC/{0}.json".format(self.project_name))
        json_data = open(file_path).read()
        self.app_QC = json.loads(json_data)

    def set_result_file_udfs(self):
        """populates the target file App QC udf"""
        for samp_name, target_file in self.target_files.items():
            if samp_name in self.app_QC.keys():
                qc_passed = str(self.app_QC[samp_name]['automated_qc']['qc_passed'])
                sample = target_file.samples[0]
                sample.udf['App QC'] = qc_passed
                set_field(sample)
                self.nr_samps_updat += 1
            else:
                self.missing_samps.append(samp_name)
    
    def make_App_QC_file(self, app_qc_file):
        """Formates a easy to read App QC file."""
        keys= ['sample', 'qc_passed', 'qc_reason']
        list2csv = []
        for samp, info in self.app_QC.items():
            d = info['automated_qc']
            d['sample'] = samp
            list2csv.append(d)
        app_qc_file = app_qc_file + '.csv'
        test_file = open(app_qc_file,'wb')
        dict_writer = csv.DictWriter(test_file, keys, dialect = 'excel')
        dict_writer.writer.writerow(keys)
        dict_writer.writerows(list2csv)
        test_file.close()

    def logging(self):
        """Collects and prints logging info."""
        self.abstract.append("qc-flaggs uploaded for {0} out of {1} samples."
                                        "See App_QC_file for details.".format(
                                        self.nr_samps_updat, self.nr_samps_tot))
        if self.missing_samps:
            self.abstract.append("The following samples are missing in "
                                                    "App_QC_file: {0}.".format(
                                                ', '.join(self.missing_samps)))
        print >> sys.stderr, ' '.join(self.abstract)

def main(lims, pid, epp_logger, App_QC_file):
    process = Process(lims, id = pid)
    AQC = AppQC(process)
    AQC.get_app_QC_file()
    AQC.set_result_file_udfs()
    AQC.make_App_QC_file(App_QC_file)
    AQC.logging()
    

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid', default = None , dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('--log', dest = 'log',
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))
    parser.add_argument('--file', dest = 'file',
                        help=('File path to new App_QC file'))
    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    with EppLogger(log_file=args.log, lims=lims, prepend=True) as epp_logger:
        main(lims, args.pid, epp_logger, args.file)
