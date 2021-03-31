#!/usr/bin/env python
"""EPP example script for Clarity LIMS, written in Python

Usage example: Trigger from Clarity with command
bash -c "PATH/TO/INSTALLED/SCRIPT
--log {compoundOutputFileLuidN}
--pid {processLuid} 
--file PATH_TO_FILE_TO_UPLOAD
"



Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden.
"""
from argparse import ArgumentParser
from genologics.lims import Lims
from genologics.entities import Process
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.epp import EppLogger, attach_file
import sys

def main(lims,pid,file):
    """Uploads a given file to the first output artifact of the process

    lims: The LIMS instance
    pid: Process Lims id
    file: File to be attached
    """
    p=Process(lims,id=pid)

    # Fetch all input-output artifact pairs
    io = p.input_output_maps

    # Filter them so that only PerInput output artifacts remains
    io_filtered = [x_y for x_y in io if x_y[1]['output-generation-type']=='PerInput']

    # Fetch the first input-output artifact pair
    (input,output) = io_filtered[0]

    # Instantiate the output artifact
    output_artifact = Artifact(output['limsid'])

    # Attach the file
    attach_file(args.file,output_artifact)


if __name__ == "__main__":
    parser = ArgumentParser()
    # Arguments that are useful in all EPP scripts
    parser.add_argument("--log",default=sys.stdout,
                        help="Log file")

    # Arguments specific for this scripts task
    parser.add_argument("--pid", help="Process id")
    parser.add_argument("--file", help="File to upload")

    args = parser.parse_args()

    # Log everything to log argument
    with EppLogger(args.log):
        lims = Lims(BASEURI,USERNAME,PASSWORD)
        lims.check_version()

        main(lims,args.pid,args.file)
