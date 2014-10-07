#!/usr/bin/env python
DESC = """This EPP script reads demultiplex end undemultiplexed yields from file
system and then does the following
    
1)  Sets the output artifact qc-flaggs based on the tresholds: 
        % Perfect Index Reads < 60
        %Q30 < 80
        expected index < 0.1 M

2)  Warns if anny unexpected index has yield > 0.5M

3)  Loads a result file with demultiplex end undemultiplexed yields. This should
    be checked if warnings are given.

Reads from:
    --files--
    Demultiplex_Stats.htm                           in mfs file system
    Undemultiplexed_stats.metrics                   in mfs file system

Writes to:
    --Lims fields--
    "qc-flag"                                       per artifact (result file)

Logging:
    The script outputs a regular log file with regular execution information.

Written by Maya Brandi 
"""

import os
import sys
import logging
import glob
import csv

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
        self.flowcell_id = process.all_inputs()[0].container.name
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
        """ Files are read from the file msf system. Path hard coded."""
        fh = ReadResultFiles(self.process)
        FRMP = FlowcellRunMetricsParser()
        file_path = ("/srv/mfs/*iseq_data/*{0}/Unaligned/Basecall_Stats_*{0}"
                                                   "/".format(self.flowcell_id))
        file_path = glob.glob(file_path)[0]
        demux_file = file_path + 'Demultiplex_Stats.htm'
        undemux_file = file_path + 'Undemultiplexed_stats.metrics'
        self.demultiplex_stats = FRMP.parse_demultiplex_stats_htm(demux_file)
        self.undemultiplexed_stats = FRMP.parse_undemultiplexed_barcode_metrics(
                                                                  undemux_file)
        self.barcode_lane_statistics = dict(map(lambda f: (f['Sample ID'],f) ,
                             self.demultiplex_stats['Barcode_lane_statistics']))
    
    def _index_QC(self, target_file):
        """Makes per sample warnings if any of the following holds: 
        % Perfect Index Reads < 60
        % of >= Q30 Bases (PF) < 80
        # Reads < 100000"""
        print 'hjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjjj'
        print target_file.udf.items()
        print dict(target_file.udf.items()).keys()
        
        perf_ind_read = target_file.udf['% Perfect Index Reads']
        Q30 = target_file.udf['% of >= Q30 Bases (PF)']
        nr_reads = int(target_file.udf['# Reads'])
        #perf_ind_read = float(sample_info['% Perfect Index Reads'])
        #Q30 = float(sample_info['% of >= Q30 Bases (PF)'])
        #nr_reads = int(sample_info['# Reads'].replace(',',''))

        QC1 = perf_ind_read >= 60
        QC2 = Q30 >= 80
        QC3 = nr_reads >= 100000

        if QC1 and QC2 and QC3:
            return 'PASSED'
        else:
            return 'FAILED'

    def set_result_file_udfs(self):
        """populates the target file qc-flags"""
        for samp_name, target_file in self.target_files.items():
            if samp_name in self.barcode_lane_statistics.keys():
                #s_inf = self.barcode_lane_statistics[samp_name]
                target_file.qc_flag = self._index_QC(target_file)
                set_field(target_file)
                self.nr_samps_updat += 1
            else:
                self.missing_samps.append(samp_name)


    def _check_unexpected_yield(self):
        """Warning if any unexpected index has yield > 0.5M"""
        warn = {'1':[],'2':[],'3':[],'4':[],'5':[],'6':[],'7':[],'8':[]}
        warning = ''
        for l, lane_inf in self.undemultiplexed_stats.items():
            counts = lane_inf['undemultiplexed_barcodes']['count']
            sequence = lane_inf['undemultiplexed_barcodes']['sequence']
            index_name = lane_inf['undemultiplexed_barcodes']['index_name']
            lanes = lane_inf['undemultiplexed_barcodes']['lane']
            for i, c in enumerate(counts):
                if int(c) > 500000:
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
                warning = warning + ''.join([inds,' on Lane ', l, ', '])
        if warning:
            self.abstract.append("WARNING: High yield of unexpected index:"
                                                         " {0}".format(warning))
                

    def make_demultiplexed_counts_file(self, demuxfile):
        """reformats the content of the demultiplex and undemultiplexed files
        to be more easy to read."""
        demuxfile = demuxfile + '.csv'
        keys = ['Project', 'Sample ID', 'Lane', '# Reads', 'Index', 
                                    'Index name', '% of >= Q30 Bases (PF)']
        toCSV = []
        for lane in range(1,9):
            for row in self.demultiplex_stats['Barcode_lane_statistics']:
                if row['Lane'] == str(lane):
                    row_dict = dict([(x, row[x]) for x in keys if x in row])
                    row_dict['Index name'] = ''
                    toCSV.append(row_dict)
            undet_per_lane = self.undemultiplexed_stats[str(lane)]['undemultiplexed_barcodes']
            nr_undet = len(undet_per_lane['count'])
            for row in range(nr_undet):
                row_dict = dict([(x, '') for x in keys])
                row_dict['# Reads'] = undet_per_lane['count'][row]
                row_dict['Index'] = undet_per_lane['sequence'][row]
                row_dict['Index name'] = undet_per_lane['index_name'][row]
                row_dict['Lane'] = undet_per_lane['lane'][row]
                toCSV.append(row_dict)    
        f = open(demuxfile, 'wb')
        dict_writer = csv.DictWriter(f, keys, dialect='excel')
        dict_writer.writer.writerow(keys)
        dict_writer.writerows(toCSV)
        f.close

    def logging(self):
        """Collects and prints logging info."""
        self._check_unexpected_yield()
        self.abstract.append("qc-flaggs uploaded for {0} out of {1} samples."
              "The qc thresholds are: '% Perfect Index Reads' < "
              "60%, '% of >= Q30 Bases (PF)' < 80%, '# Reads' < 100000.".format(
                                       self.nr_samps_updat, self.nr_samps_tot))
        if self.missing_samps:
            self.abstract.append("The following samples are missing in "
                                          "Demultiplex Stats file: {0}.".format(
                                                 ', '.join(self.missing_samps)))
        print >> sys.stderr, ' '.join(self.abstract)

def main(lims, pid, epp_logger, demuxfile):
    process = Process(lims,id = pid)
    UDI = UndemuxInd(process)
    UDI.get_demultiplex_files()
    UDI.set_result_file_udfs()
    UDI.make_demultiplexed_counts_file(demuxfile)
    UDI.logging()
    

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid', default = None , dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('--log', dest = 'log',
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))
    parser.add_argument('--file', dest = 'file', default = 'demux',
                        help=('File path to demultiplexed metrics files'))
    args = parser.parse_args()
    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    with EppLogger(log_file=args.log, lims=lims, prepend=True) as epp_logger:
        main(lims, args.pid, epp_logger, args.file)
