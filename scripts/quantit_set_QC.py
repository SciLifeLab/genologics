#!/usr/bin/env python
DESC = """EPP script for Quant-iT mesurements to verify standards, calculate
concentrations and load input artifact-udfs and output file-udfs of the process 
with concentation values and fluorescence intensity

Reads from:
    --Lims fields--
    "Saturation threshold of fluorescence intensity"    process udf 
    "Allowed %CV of duplicates"                         process udf
    "Fluorescence intensity 1"  udf of input analytes to the process
    "Fluorescence intensity 2"  udf of input analytes to the process

    --files--
    "Standards File (.txt)"     "shared result file" uploaded by user.   
    "Quant-iT Result File 1"    "shared result file" uploaded by user.
    "Quant-iT Result File 2"    "shared result file" uploaded by user. (optional)

Writes to:
    --Lims fields--
    "Intensity check"           udf of process artifacts (result file)
    "%CV"                       udf of process artifacts (result file)
    "QC"                        qc-flag of process artifacts (result file)

Logging:
The script outputs a regular log file with regular execution information.

1) compares the udfs "Fluorescence intensity 1" and "Fluorescence intensity 2" 
with the Saturation threshold of fluorescence intensity. If either of these two 
udfs >= Saturation threshold of fluorescence intensity, assign "Saturated" to 
the udf "Intensity check" and assign "Fail" to the sample. Otherwise assign 
"OK" to the analyte "Intensity check".

2) For a sample with duplicate measurements, "%CV" is calculated by the formula: 
%CV= (SD of "Fluorescence intensity 1" and "Fluorescence intensity 2")/(Mean of 
"Fluorescence intensity 1" and ""Fluorescence intensity 2). 
Copy the values to the sample analyte "%CV".

3) If "%CV" >= Allowed %CV of duplicates, assign "Fail" to the sample. 

4) For a sample with only one measurement, if it passes in step 2, a "Pass" should 
be assigned to the QC flag. For a sample with duplicate measurements, if it passes 
both step 2 and step 4, a "Pass" should be assigned to the QC flag.

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
    def __init__(self, process):
        self.udfs = dict(process.udf.items())
        self.abstract = []
        self.missing_udfs = []
        self.no_samples = 0

    def assign_QC_flag(self, result_file, treshold, allowed_dupl):
        analyte_udfs = dict(result_file.udf.items())
        if "Fluorescence intensity 1" in analyte_udfs.keys():
            flour_int_1 = result_file.udf["Fluorescence intensity 1"]
            if (flour_int_1 >= treshold) or (flour_int_1 >= treshold):
                result_file.udf["Intensity check"] = "Saturated" 
                result_file.qc_flag = "FAILED"
            else:
                result_file.udf["Intensity check"] = "OK"
                result_file.qc_flag = "PASSED"
                if "Fluorescence intensity 2" in analyte_udfs.keys():
                    flour_int_2 = result_file.udf["Fluorescence intensity 2"]
                    procent_CV = np.true_divide(np.std([flour_int_1, flour_int_2]),
                                                np.mean([flour_int_1, flour_int_2]))
                    result_file.udf["%CV"] = procent_CV
                    if procent_CV >= allowed_dupl:
                        result_file.qc_flag = "FAILED"
            set_field(result_file)
            self.no_samples += 1
        else:
            self.abstract.append("Fluorescence intensity missing. Have youe uploaded a Quant-iT Resultfile?")

def main(lims, pid, epp_logger):
    process = Process(lims,id = pid)
    QiT = QunatiT(process)
    requiered_udfs = set(["Saturation threshold of fluorescence intensity", 
                                                        "Allowed %CV of duplicates"])
    if requiered_udfs.issubset(QiT.udfs.keys()):
        treshold = QiT.udfs["Saturation threshold of fluorescence intensity"]
        allowed_dupl = QiT.udfs["Allowed %CV of duplicates"]
        for result_file in process.result_files():
            QiT.assign_QC_flag(result_file, treshold, allowed_dupl)
    else:
        QiT.missing_udfs.append(requiered_udfs)
    if QiT.missing_udfs:
        missing_udfs = ', '.join(QiT.missing_udfs)
        QiT.abstract.append("Are all of the folowing udfs set? : {0}".format(missing_udfs))
    QiT.abstract.append("Uploaded QC-flagg for {0} samples.".format(QiT.no_samples))
    QiT.abstract = list(set(QiT.abstract))
    print >> sys.stderr, ' '.join(QiT.abstract)

if __name__ == "__main__":
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid', default = None , dest = 'pid',
                        help='Lims id for current Process')
    parser.add_argument('--log', dest = 'log',
                        help=('File name for standard log file, '
                              'for runtime information and problems.'))

    args = parser.parse_args()
    lims = Lims(BASEURI,USERNAME,PASSWORD)
    lims.check_version()

    with EppLogger(log_file=args.log, lims=lims, prepend=True) as epp_logger:
        main(lims, args.pid, epp_logger)

