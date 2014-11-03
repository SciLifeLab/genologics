#!/usr/bin/env python
DESC = """EPP script for updating #Reads and %Q30 for quality filtered reads.
The script reads the new values from a csv file "Quality Filter" that first 
need to be generated by the quality filter script XXX and uploaded to the process.

Reads from:
    --files--
    "Quality Filter"            "shared result file" uploaded by user.   

Writes to:
    --Lims fields--
    "% Bases >=Q30"             udf of process artifacts (result file)
    "#Reads"                    udf of process artifacts (result file)

Logging:
    The script outputs a regular log file with regular execution information.

Written by Maya Brandi 
"""

import os
import sys
import logging
import csv

from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process
from genologics.epp import EppLogger
from genologics.epp import set_field

class QualityFilter():
    def __init__(self, process):
        self.process = process
        self.flowcell_id = process.all_inputs()[0].container.name
        self.project_name = process.all_outputs()[0].samples[0].project.name
        self.result_files = process.result_files()
        self.source_file = None
        self.QF_from_file = {}
        self.missing_samps = []
        self.abstract = []
        self.nr_samps_updat = []

    def read_QF_file(self):
        """ QF file is read from the file msf system. Path hard coded."""
        file_path = ("/srv/mfs/QF/{0}/{1}.csv".format(self.project_name, self.flowcell_id))
        of = open(file_path ,'r')
        self.source_file = [row for row in csv.reader(of.read().splitlines())]
        of.close()

    def get_and_set_yield_and_Q30(self):
        self._format_file()
        input_pools = self.process.all_inputs()
        self.abstract.append("Yield and Q30 uploaded on")
        for pool in input_pools:
            self.nr_samps_updat = []
            self.missing_samps = []
            lane = pool.location[1][0] #getting lane number
            outarts_per_lane = self.process.outputs_per_input(
                                          pool.id, ResultFile = True)
            for target_file in outarts_per_lane:
                samp_name = target_file.samples[0].name
                self._set_udfs(samp_name, target_file, lane)
            self.abstract.append("LANE: {0} for {0} samples."
                              "".format(lane, self.nr_samps_updat))
            if self.missing_samps:
                self.abstract.append("The following samples are missing in Quality "
                "Filter file: {0}.".format(', '.join(self.missing_samps)))
        self._logging()

    def _format_file(self):
        keys = self.source_file[0]
        l_ind = keys.index('Lane')
        s_ind = keys.index('Sample')
        q_ind = keys.index('% Bases >=Q30')
        y_ind = keys.index('# Reads')
        for line in self.source_file[1:]:
            lane = line[l_ind]
            samp = line[s_ind]
            if not lane in self.QF_from_file.keys():
                self.QF_from_file[lane] = {}
            self.QF_from_file[lane][samp] = {'% Bases >=Q30' : line[q_ind],
                                                   '# Reads' : line[y_ind]}
  
    def _set_udfs(self, samp_name, target_file, lane):
        if lane in self.QF_from_file.keys():
            if samp_name in self.QF_from_file[lane].keys():
                s_inf = self.QF_from_file[lane][samp_name]
                target_file.udf['# Reads'] = int(s_inf['# Reads'])
                target_file.udf['% Bases >=Q30'] = float(s_inf['% Bases >=Q30'])
                self.nr_samps_updat.append(samp_name)
            else:
                self.missing_samps.append(samp_name)
        set_field(target_file)

    def _logging(self):
        #self.nr_samps_updat = len(set(self.nr_samps_updat))
        #self.abstract.append("Yield and Q30 uploaded for {0} out of {1} samples."
        #                      "".format(self.nr_samps_updat, self.nr_samps_tot))
        #if self.missing_samps:
        #    self.abstract.append("The following samples are missing in Quality "
        #    "Filter file: {0}.".format(', '.join(self.missing_samps)))
        print >> sys.stderr, ' '.join(self.abstract)

def main(lims, pid, epp_logger):
    process = Process(lims,id = pid)
    QF = QualityFilter(process)
    QF.read_QF_file()
    QF.get_and_set_yield_and_Q30()
    

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid', default = None , dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('--log', dest = 'log',
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))

    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    with EppLogger(log_file=args.log, lims=lims, prepend=True) as epp_logger:
        main(lims, args.pid, epp_logger)
