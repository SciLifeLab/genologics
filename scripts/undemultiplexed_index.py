#!/usr/bin/env python
DESC = """This EPP script reads demultiplex end undemultiplexed yields from file
system and then does the following
    
1)  Sets the output artifact qc-flaggs based on the threshold-udfs if the process: 
        % Perfect Index Reads < 60 (default)
        %Q30 < 80 (default)
        expected index < 0.1 M (default)

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
from qc_parsers import FlowcellRunMetricsParser

class UndemuxInd():
    def __init__(self, process):
        self.process = process
        self.flowcell_id = process.all_inputs()[0].container.name
        self.input_pools = process.all_inputs()
        self.demultiplex_stats = None
        self.undemultiplex_stats = None 
        self.QC_thresholds = {}
        self.abstract = []
        self.un_exp_ind_warn = ''
        self.nr_lane_samps_updat = 0
        self.nr_lane_samps_tot = 0

    def get_demultiplex_files(self):
        """ Files are read from the file msf system. Path hard coded."""
        FRMP = FlowcellRunMetricsParser()
        file_path = glob.glob(("/srv/mfs/*iseq_data/*{0}/Unaligned/"
                            "Basecall_Stats_*{0}/".format(self.flowcell_id)))[0]
        try:
            self.demultiplex_stats = FRMP.parse_demultiplex_stats_htm(
                                        file_path + 'Demultiplex_Stats.htm')
            self.undemultiplexed_stats = FRMP.parse_undemultiplexed_barcode_metrics(
                                        file_path + 'Undemultiplexed_stats.metrics')
            logging.info("Parsed files Demultiplex_Stats.htm and Undemultiplexe"
                                        "d_stats.metrics in {0}".format(file_path))
        except:
            sys.exit("Failed to parse files Demultiplex_Stats.htm and "
                     "Undemultiplexed_stats.metrics in {0}. Files might "
                     "be corrupt or not existing".format(file_path))
 

    def set_result_file_udfs(self):
        """populates the target file qc-flags"""

        for pool in self.input_pools:
            lane = pool.location[1][0] #getting lane number
            outarts_per_lane = self.process.outputs_per_input(
                                          pool.id, ResultFile = True)
            for target_file in outarts_per_lane:
                self.nr_lane_samps_tot += 1
                samp_name = target_file.samples[0].name
                for lane_samp in self.demultiplex_stats['Barcode_lane_statistics']:
                    if lane == lane_samp['Lane']:
                        samp = lane_samp['Sample ID']
                        if samp == samp_name:
                            target_file.qc_flag = self._QC(target_file, lane_samp)
                            set_field(target_file)
                            self.nr_lane_samps_updat += 1
 
    def _QC(self, target_file, sample_info):
        """Makes per sample warnings if any of the following holds: 

        % Perfect Index Reads < 60
        % of >= Q30 Bases (PF) < 80
        # Reads < 100000

        OBS: Reads from target file udf if they are already set. Otherwise from 
        file system!!! This is to take into account yield and quality after 
        quality filtering if performed."""

        try: 
            perf_ind_read = float(target_file.udf['% Perfect Index Read'])
            logging.info("Getting % Perfect Index Read from udf")
        except: 
            perf_ind_read = float(sample_info['% Perfect Index Reads'])
            logging.info("Getting % Perfect Index Read from Demultiplex_Stats.htm")
        try: 
            Q30 = float(target_file.udf['% Bases >=Q30'])
            logging.info("Getting % Bases >=Q30 from udf")
        except: 
            Q30 = float(sample_info['% of >= Q30 Bases (PF)'])
            logging.info("Getting % Bases >=Q30 from Demultiplex_Stats.htm")
        try:
            nr_reads = int(target_file.udf['# Reads'])
            logging.info("Getting # Reads from udf")
        except: 
            nr_reads = int(sample_info['# Reads'].replace(',',''))
            logging.info("Getting # Reads from Demultiplex_Stats.htm")

        self._get_QC_thresholds()
        QC1 = (perf_ind_read >= self.QC_thresholds['perf_ind'])
        QC2 = (Q30 >= self.QC_thresholds['%Q30'])
        QC3 = (nr_reads >= self.QC_thresholds['nr_read'])

        if QC1 and QC2 and QC3:
            return 'PASSED'
        else:
            return 'FAILED'

    def _get_QC_thresholds(self):
        """Fetching QC_thresholds from process udfs"""
        try:
            self.QC_thresholds['perf_ind'] = self.process.udf['Threshold for % Perfect Index Reads']
            self.QC_thresholds['%Q30'] = self.process.udf['Threshold for % bases >= Q30']
            self.QC_thresholds['nr_read'] = self.process.udf['Threshold for # Reads']
        except:
            sys.exit("Set QC thresholds and try again!")


    def make_demultiplexed_counts_file(self, demuxfile):
        """Reformats the content of the demultiplex and undemultiplexed files
        to be more easy to read."""

        demuxfile = demuxfile + '.csv'
        keys = ['Project', 'Sample ID', 'Lane', '# Reads', 'Index', 
                                    'Index name', '% of >= Q30 Bases (PF)']
        toCSV = []
        for pool in self.input_pools:
            lane = pool.location[1][0]
            for row in self.demultiplex_stats['Barcode_lane_statistics']:
                if row['Lane'] == lane:
                    row_dict = dict([(x, row[x]) for x in keys if x in row])
                    row_dict['Index name'] = ''
                    toCSV.append(row_dict)
            if lane in self.undemultiplexed_stats.keys():
                undet_per_lane = self.undemultiplexed_stats[lane]['undemultiplexed_barcodes']
                nr_undet = len(undet_per_lane['count'])
                for row in range(nr_undet):
                    row_dict = dict([(x, '') for x in keys])
                    row_dict['# Reads'] = undet_per_lane['count'][row]
                    row_dict['Index'] = undet_per_lane['sequence'][row]
                    row_dict['Index name'] = undet_per_lane['index_name'][row]
                    row_dict['Lane'] = undet_per_lane['lane'][row]
                    toCSV.append(row_dict)    
        try:
            f = open(demuxfile, 'wb')
            dict_writer = csv.DictWriter(f, keys, dialect='excel')
            dict_writer.writer.writerow(keys)
            dict_writer.writerows(toCSV)
            f.close
            self.abstract.append("INFO: A Metrics file has been created with "
                      "demultiplexed and undemultiplexed counts for debugging.")
        except:
            self.abstract.append("WARNING: Could not generate a Metrics file "
                               "with demultiplexed and undemultiplexed counts.")

    def logging(self):
        """Collects and prints logging info."""
        self._check_unexpected_yield()
        self.abstract.append("INFO: QC-data found and QC-flags uploaded for {0}"
              " out of {1} analytes. Flags are set based on the selected thresh"
              "olds. ".format(self.nr_lane_samps_updat, self.nr_lane_samps_tot))
        if self.un_exp_ind_warn:
            sys.exit(' '.join(self.abstract))
        else:
            print >> sys.stderr, ' '.join(self.abstract)

    def _check_unexpected_yield(self):
        """Warning if any unexpected index has yield > 0.5M"""
        warn = {'1':[],'2':[],'3':[],'4':[],'5':[],'6':[],'7':[],'8':[]}
        for pool in self.input_pools:
            lane = pool.location[1][0]
            lane_inf = self.undemultiplexed_stats[lane]
            counts = lane_inf['undemultiplexed_barcodes']['count']
            sequence = lane_inf['undemultiplexed_barcodes']['sequence']
            index_name = lane_inf['undemultiplexed_barcodes']['index_name']
            lanes = lane_inf['undemultiplexed_barcodes']['lane']
            for i, c in enumerate(counts):
                if int(c) > 100000:
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
                self.un_exp_ind_warn = self.un_exp_ind_warn + ''.join([inds,
                                                          ' on Lane ', l, ', '])
        if self.un_exp_ind_warn:
            self.abstract.insert(0, "WARNING: High yield of unexpected index:"
                                  " {0}. Please check the Metrics file!".format(
                                                          self.un_exp_ind_warn))

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
