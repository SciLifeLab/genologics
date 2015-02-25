#!/usr/bin/env python
DESC = """This EPP script reads demultiplex end undemultiplexed yields from file
system and then does the following

1)  Sets the output artifact udfs based demultiplex resultfile.
 
2)  Sets the output artifact qc-flaggs based on the threshold-udfs if the process: 
        % Perfect Index Reads < 60 (default)
        %Q30 < 80 (default)
        expected index < 0.1 M (default)

3)  Warns if anny unexpected index has yield > 0.5M

4)  Loads a result file with demultiplex end undemultiplexed yields. This should
    be checked if warnings are given.

Reads from:
    --files--
    Demultiplex_Stats.htm                           in mfs file system
    Undemultiplexed_stats.metrics                   in mfs file system

Writes to:
    --Lims fields--
    qc-flag                                         per artifact (result file)
    % One Mismatch Reads (Index)                    per artifact (result file)
    % of Raw Clusters Per Lane                      per artifact (result file)
    %PF                                             per artifact (result file)
    Ave Q Score                                     per artifact (result file)
    Yield PF (Gb)                                   per artifact (result file)
    % Perfect Index Read                            per artifact (result file)
    % Bases >=Q30                                   per artifact (result file)
    # Reads                                         per artifact (result file)
    # Read Pairs

Logging:
    The script outputs a regular log file with regular execution information.

Written by Maya Brandi 
"""

import os
import sys
import logging
import glob
import csv
import numpy as np

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
        self.input_pools = process.all_inputs()
        self.dem_stat = None
        self.undem_stat = None 
        self.QC_thresholds = {}
        self.abstract = []
        self.un_exp_ind_warn = ''
        self.nr_lane_samps_updat = 0
        self.nr_lane_samps_tot = 0
        self.seq_run = None
        self.single = True
        self.read_pairs = None
        self.file_path = None
        self.run_udfs = {}
        self.demux_udfs = dict(self.process.udf.items())
        self.read_length = None


    def get_run_info(self):
        try:
            cont_name = self.process.all_inputs()[0].location[0].name
        except:
            sys.exit('Could not find container name.')
        miseq = lims.get_processes(
                                udf={'Reagent Cartridge ID' : cont_name},
                                type = 'MiSeq Run (MiSeq) 4.0')
        hiseq = lims.get_processes(
                                udf = {'Flow Cell ID' : cont_name},
                                type = 'Illumina Sequencing (Illumina SBS) 4.0')
        hiseq_X10 = None #lims.get_processes(
#                                udf = {'Flow Cell ID' : cont_name},
#                                type = 'Illumina Sequencing (HiSeq X) 1.0')
        if miseq:
            self.seq_run = miseq[0]
            self.run_type = 'MiSeq'
        elif hiseq:
            self.seq_run = hiseq[0]
            try:
                self.run_type = self.seq_run.udf['Flow Cell Version']
            except:
                sys.exit("Missing field 'Flow Cell Version' in sequencing process")
            path_id = cont_name
        elif hiseq_X10:
            self.seq_run = hiseq_X10[0]
            self.run_type = 'HiSeqX10'
            path_id = cont_name
        else:
            sys.exit("run not found")

        self.run_udfs = dict(self.seq_run.udf.items())
        self._get_run_id()
        self._get_cycles()
        self._get_file_path(cont_name)
        self._get_demultiplex_files()

    def _get_run_id(self):
        if self.run_udfs.has_key('Run ID'):
            self.process.udf['Run ID'] = self.run_udfs['Run ID']
            set_field(self.process)

    def _get_cycles(self):
        if self.run_udfs.has_key('Read 1 Cycles'):
            self.read_length = self.run_udfs['Read 1 Cycles']
        else:
            sys.exit("Could not get 'Read 1 Cycles' from the sequencing step.")
        if self.run_udfs.has_key('Read 2 Cycles'):
            self.single = False

    def _get_file_path(self, cont_name):
        if self.run_type == 'MiSeq':
            path_id = self.run_udfs['Flow Cell ID']
        elif self.run_type in ['HiSeq','HiSeqX10']:
            path_id = cont_name
        try:
            self.file_path = glob.glob(("/srv/mfs/*iseq_data/*{0}/Unaligned/"
                                        "Basecall_Stats_*/".format(path_id)))[0]
        except:
            sys.exit("Failed to get file path")

    def _get_demultiplex_files(self):
        """ Files are read from the file msf system. Path hard coded."""
        FRMP = FlowcellRunMetricsParser()
        try:
            fp_dem = self.file_path + 'Demultiplex_Stats.htm'
            self.dem_stat = FRMP.parse_demultiplex_stats_htm(fp_dem)
            logging.info("Parsed file {0}".format(fp_dem))
        except:
            sys.exit("Failed to find or parse Demultiplex_Stats.htm.")
        try:
            fp_und = self.file_path + 'Undemultiplexed_stats.metrics'
            self.undem_stat = FRMP.parse_undemultiplexed_barcode_metrics(fp_und)
            logging.info("Parsed file {0}".format(fp_und))
        except:
            sys.exit("Failed to find or parse Undemultiplexed_stats.metrics")



    def set_result_file_udfs(self):
        """populates the target file qc-flags"""
        for pool in self.input_pools:
            if self.run_type == 'MiSeq':
                lane = '1'
            else:
                lane = pool.location[1][0] #getting lane number
            outarts_per_lane = self.process.outputs_per_input(
                                          pool.id, ResultFile = True)

            nr_lane_samps = len(outarts_per_lane)
            pool_udfs = dict(pool.udf.items())
            thresholds = {'perf_ind' : self._QC_threshold_perf_ind(pool_udfs),
                'Q30' : self._QC_threshold_Q30(pool_udfs),
                'nr_read' : self._QC_threshold_nr_read(pool_udfs, nr_lane_samps)}

            for target_file in outarts_per_lane:
                self.nr_lane_samps_tot += 1
                samp_name = target_file.samples[0].name
                for lane_samp in self.dem_stat['Barcode_lane_statistics']:
                    if lane == lane_samp['Lane']:
                        samp = lane_samp['Sample ID']
                        if samp == samp_name:
                            self._QC(target_file, lane_samp, thresholds)
                            self._get_fields(target_file, lane_samp)
                            set_field(target_file)
                            self.nr_lane_samps_updat += 1


    def _QC(self, target_file, sample_info, threshold):
        """Makes per sample warnings if any of the following holds: 
                % Perfect Index Reads < ..
                % of >= Q30 Bases (PF) < ..
                # Reads < ..
            sets qc flaggs        
            Sets the include reads field
        OBS: Reads from target file udf if they are already set. Otherwise from 
        file system!!! This is to take into account yield and quality after 
        quality filtering if performed."""

        perf_ind_read = float(sample_info['% Perfect Index Reads'])
        Q30 = float(sample_info['% of >= Q30 Bases (PF)'])
        QC1 = (perf_ind_read >= threshold['perf_ind'])
        QC2 = (Q30 >= threshold['Q30'])
        QC3 = (self.read_pairs >= threshold['nr_read'])
        if QC1 and QC2 and QC3:
            target_file.udf['Include reads'] = 'YES'
            target_file.qc_flag = 'PASSED'
        else:
            target_file.udf['Include reads'] = 'NO'
            target_file.qc_flag = 'FAILED'

    def _QC_threshold_perf_ind(self, pool_udfs):
        if self.demux_udfs.has_key('Threshold for % Perfect Index Reads'):
            return self.demux_udfs['Threshold for % Perfect Index Reads']
        else:
            return 40

    def _QC_threshold_Q30(self, pool_udfs):
        if self.demux_udfs.has_key('Threshold for % bases >= Q30'):
            return self.demux_udfs['Threshold for % bases >= Q30']
        elif pool_udfs.has_key("Clusters PF R1"):
            nr_reads = pool_udfs["Clusters PF R1"]
            if self.run_type == 'MiSeq':
                if self.read_length < 101:
                    Q30_threshold = 80
                elif self.read_length == 101:
                    Q30_threshold = 75
                elif self.read_length == 151:
                    Q30_threshold = 70
                elif self.read_length >= 251:
                    Q30_threshold = 60
            else:
                if self.read_length == 51:
                    Q30_threshold = 85
                elif self.read_length == 101:
                    Q30_threshold = 80
                elif self.read_length == 126:
                    Q30_threshold = 80
                elif self.read_length == 151:
                    Q30_threshold = 75
                self.process.udf['Threshold for % bases >= Q30'] = Q30_threshold
                set_field(self.process)
                return Q30_threshold

    def _QC_threshold_nr_read(self, pool_udfs, nr_lane_samps):
        if self.demux_udfs.has_key('Threshold for # Reads'):
            return self.demux_udfs['Threshold for # Reads']
        elif pool_udfs.has_key("Clusters PF R1"):
            print pool_udfs
            if self.run_type == 'MiSeq':
                if self.read_length in [76, 301]:   # ver3
                    exp_lane_clust = 18000000
                else:                               # ver2
                    exp_lane_clust = 10000000
            elif self.run_type == 'HiSeq Rapid Flow Cell v1':
                exp_lane_clust = 114000000
            elif self.run_type == 'HiSeq Flow Cell v4':
                exp_lane_clust = 143000000
            elif self.run_type == 'HiSeq Flow Cell v3':
                exp_lane_clust = 188000000
            elif self.run_type == 'HiSeqX10':
                exp_lane_clust = 250000000
            exp_samp_clust = np.true_divide(exp_lane_clust, nr_lane_samps)
            reads_threshold = int(np.true_divide(exp_samp_clust, 2))
            print "INFO: Threshold for # Reads on lane is {0}. Value based on nr of sampels: {1}, and run type {2}.".format(
                                 reads_threshold, nr_lane_samps, self.run_type)
            self.abstract.append("INFO: Threshold for # Reads on lane is {0}. "
                   "Value based on nr of sampels: {1}, and run type {2}.".format(
                                reads_threshold, nr_lane_samps, self.run_type))
            print self.abstract
            return reads_threshold
        #else:
            # do some log


    def _get_fields(self, t_file, sample_info):
        """ Populates the target file udfs. (run lane index resolution)
        sample_info -   Barcode lane statistics fetched from demultiplexed 
                        stats file
        t_file -   output artifact of the bcl-conv & demux process (run 
                        lane index resolution)"""

        omr = float(sample_info['% One Mismatch Reads (Index)'])
        rcl = float(sample_info['% of raw clusters per lane'])
        pf  = float(sample_info['% PF'])
        mqs = float(sample_info['Mean Quality Score (PF)'])
        yMb = float(sample_info['Yield (Mbases)'].replace(',',''))
        pir = float(sample_info['% Perfect Index Reads'])
        q30 = float(sample_info['% of >= Q30 Bases (PF)'])
        nrr = float(sample_info['# Reads'].replace(',',''))

        t_file.udf['% One Mismatch Reads (Index)'] = omr
        t_file.udf['% of Raw Clusters Per Lane'] = rcl
        t_file.udf['%PF'] = pf
        t_file.udf['Ave Q Score'] = mqs
        t_file.udf['Yield PF (Gb)'] = np.true_divide(yMb, 1000)
        t_file.udf['% Perfect Index Read'] = pir 

        if not dict(t_file.udf.items()).has_key('% Bases >=Q30'):
            t_file.udf['% Bases >=Q30'] = q30
        if not dict(t_file.udf.items()).has_key('# Reads'):
            t_file.udf['# Reads'] = nrr 
        if self.single:
            self.read_pairs = int(t_file.udf['# Reads'])
        else:
            self.read_pairs = np.true_divide(float(t_file.udf['# Reads']), 2)
        t_file.udf['# Read Pairs'] = self.read_pairs

    def make_demultiplexed_counts_file(self, demuxfile):
        """Reformats the content of the demultiplex and undemultiplexed files
        to be more easy to read."""

        demuxfile = demuxfile + '.csv'
        keys = ['Project', 'Sample ID', 'Lane', '# Reads', 'Index', 
                                    'Index name', '% of >= Q30 Bases (PF)']
        toCSV = []
        for pool in self.input_pools:
            if self.run_type == 'MiSeq':
                lane = '1'
            else:
                lane = pool.location[1][0]
            for row in self.dem_stat['Barcode_lane_statistics']:
                if row['Lane'] == lane:
                    row_dict = dict([(x, row[x]) for x in keys if x in row])
                    row_dict['Index name'] = ''
                    toCSV.append(row_dict)
            if lane in self.undem_stat.keys():
                undet_per_lane = self.undem_stat[lane]['undemultiplexed_barcodes']
                nr_undet = len(undet_per_lane['count'])
                for row in range(nr_undet):
                    row_dict = dict([(x, '') for x in keys])
                    row_dict['# Reads'] = undet_per_lane['count'][row]
                    row_dict['Index'] = undet_per_lane['sequence'][row]
                    row_dict['Index name'] = undet_per_lane['index_name'][row]
                    row_dict['Lane'] = undet_per_lane['lane'][row]
                    toCSV.append(row_dict)    
        try:
            f = open(demuxfile, 'w')
            dict_writer = csv.DictWriter(f, keys, dialect='excel')
            dict_writer.writer.writerow(keys)
            dict_writer.writerows(toCSV)
            f.close
            self.abstract.append("INFO: A Metrics file has been created with "
                      "demultiplexed and undemultiplexed counts for debugging.")
        except:
            self.abstract.append("WARNING: Could not generate a Metrics file "
                               "with demultiplexed and undemultiplexed counts.")



    def check_unexpected_yield(self):
        """Warning if any unexpected index has yield > 0.5M"""
        warn = {'1':[],'2':[],'3':[],'4':[],'5':[],'6':[],'7':[],'8':[]}
        for pool in self.input_pools:
            if self.run_type == 'MiSeq':
                lane = '1'
            else: 
                lane = pool.location[1][0]
            lane_inf = self.undem_stat[lane]
            counts = lane_inf['undemultiplexed_barcodes']['count']
            sequence = lane_inf['undemultiplexed_barcodes']['sequence']
            index_name = lane_inf['undemultiplexed_barcodes']['index_name']
            lanes = lane_inf['undemultiplexed_barcodes']['lane']
            for i, c in enumerate(counts):
                if int(c) > self._QC_threshold_undem_yield():
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
            print self.abstract
            self.abstract.insert(0, "WARNING: High yield of unexpected index:"
                                  " {0}. Please check the Metrics file!".format(
                                                          self.un_exp_ind_warn))
            print self.abstract
            print 'ss'

    def _QC_threshold_undem_yield(self):
        if self.demux_udfs.has_key('Threshold for Undemultiplexed Index Yield'):
            return self.demux_udfs['Threshold for Undemultiplexed Index Yield']
        else:
            return 500000

    def logging(self):
        """Collects and prints logging info."""
        self.abstract.append("INFO: QC-data found and QC-flags uploaded for {0}"
              " out of {1} analytes. Flags are set based on the selected thresh"
              "olds. ".format(self.nr_lane_samps_updat, self.nr_lane_samps_tot))
        if self.un_exp_ind_warn:
            sys.exit(' '.join(self.abstract))
        else:
            print >> sys.stderr, ' '.join(self.abstract)

######################### 

def main(lims, pid, epp_logger, demuxfile):
    process = Process(lims,id = pid)
    UDI = UndemuxInd(process)
    UDI.get_run_info()
    UDI.set_result_file_udfs()
    UDI.make_demultiplexed_counts_file(demuxfile)
    UDI.check_unexpected_yield()
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