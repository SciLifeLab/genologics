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
import glob

from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.config import BASEURI, USERNAME, PASSWORD
from genologics.entities import Process
from genologics.epp import EppLogger
from genologics.epp import set_field
from genologics.epp import ReadResultFiles
from qc_parsers import FlowcellRunMetricsParser

class UndemuxInd():
    def __init__(self, process):
        self.process = process
        self.target_files = dict((r.samples[0].name, r) for r in process.result_files())
        self.nr_samps_tot = str(len(self.target_files))
        self.demultiplex_stats = None
        self.undemultiplex_stats = None
        self.barcode_lane_statistics = None
        self.abstract = []
 
        self.QF_from_file = {}
        self.missing_samps = []
        self.nr_samps_updat = 0

    def get_demultiplex_files(self):
        """"""
        fh = ReadResultFiles(self.process)
        FRMP = FlowcellRunMetricsParser()
        demultiplex_stats = filter(lambda f: f.name == 'Demultiplex Stats'
                                         ,self.process.shared_result_files())[0]
        htm_file_path = fh.get_file_path(demultiplex_stats)
        self.demultiplex_stats = FRMP.parse_demultiplex_stats_htm(htm_file_path)
        met_file_path = ("/srv/mfs/*iseq_data/*{0}/Unaligned/Basecall_Stats_*{0}"
                          "/Undemultiplexed_stats.metrics".format(FRMP.flowcell))
        met_file_path = glob.glob(met_file_path)[0]
        self.undemultiplexed_stats = FRMP.parse_undemultiplexed_barcode_metrics(
                                                                  met_file_path)
        self.barcode_lane_statistics = dict(map(lambda f: (f['Sample ID'],f) ,
                             self.demultiplex_stats['Barcode_lane_statistics']))
    
    def _index_QC(self, sample_info):
        """Makes per sample warnings if any of the following holds: 
        % Perfect Index Reads < 60
        % of >= Q30 Bases (PF) < 80
        # Reads < 100000"""

        perf_ind_read = float(sample_info['% Perfect Index Reads'])
        Q30 = float(sample_info['% of >= Q30 Bases (PF)'])
        nr_reads = int(sample_info['# Reads'].replace(',',''))

        QC1 = perf_ind_read >= 60
        QC2 = Q30 >= 80
        QC3 = nr_reads >= 100000

        if QC1 and QC2 and QC3:
            return 'PASS'
        else:
            return 'WARN'

    def set_result_file_udfs(self):
        """populates udfs: '% Perfect Index Reads' and 'Index QC'"""
        for samp_name, target_file in self.target_files.items():
            print 'LLLLLLLLLLLL'
            print target_file
            if samp_name in self.barcode_lane_statistics.keys():
                s_inf = self.barcode_lane_statistics[samp_name]
                target_file.udf['% Perfect Index Reads'] = s_inf['% Perfect Index Reads']
                target_file.udf['Index QC'] = self._index_QC(s_inf)
                print target_file.udf['Index QC']
                print target_file.udf['% Perfect Index Reads']
                print '***********'
                set_field(target_file)
                self.nr_samps_updat += 1
            else:
                self.missing_samps.append(samp_name)


    def _check_unexpected_yield(self):
        """Warning if an unexpected index has yield > 0.5M"""
        warn = {'1':[],'2':[],'3':[],'4':[],'5':[],'6':[],'7':[],'8':[]}
        warning = ''
        for l, lane_inf in self.undemultiplexed_stats.items():
            counts = lane_inf['undemultiplexed_barcodes']['count']
            sequence = lane_inf['undemultiplexed_barcodes']['sequence']
            index_name = lane_inf['undemultiplexed_barcodes']['index_name']
            lanes = lane_inf['undemultiplexed_barcodes']['lane']
            for i, c in enumerate(counts):
                if int(c) > 200000:#500000:
                    ##  Format warning message
                    lane = lanes[i]
                    if index_name[i]:
                        s = ' '.join([sequence[i],'(',index_name[i],')'])
                        warn[lane].append(s)
                    else:
                        warn[lane].append(sequence[i])
        for l, w in warn.items():
            if w:
                inds = ', '.join(w)
                warning = warning + ''.join([inds,' on Lane ', l, '. '])
        if warning:
            self.abstract.append("WARNING for high yield of unexpected index:"
                                                         " {0}".format(warning))
                

    def make_demultiplexed_counts_file(self):
        """"""

    def logging(self):
        self._check_unexpected_yield()
        self.abstract.append("Index QC and % Perfect Index Reads uploaded for "
                           "{0} out of {1} samples.".format(self.nr_samps_updat,
                                                             self.nr_samps_tot))
        if self.missing_samps:
            self.abstract.append("The following samples are missing in "
                                          "Demultiplex Stats file: {0}.".format(
                                                 ', '.join(self.missing_samps)))
        print >> sys.stderr, ' '.join(self.abstract)

def main(lims, pid, epp_logger):
    process = Process(lims,id = pid)
    UDI = UndemuxInd(process)
    UDI.get_demultiplex_files()
    UDI.set_result_file_udfs()
    #UDI.make_demultiplexed_counts_file()
    UDI.logging()
    

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
