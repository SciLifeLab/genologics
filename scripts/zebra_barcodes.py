#!/usr/bin/env python
import sys
from argparse import ArgumentParser
import subprocess
import logging
import datetime
from genologics.config import BASEURI,USERNAME,PASSWORD
from genologics.lims import Lims
from genologics.epp import EppLogger
from genologics.entities import Process

def makeContainerBarcode(plateid,copies=1):
    """ Construct label with container id as human readable and barcode """
    lines = []
    lines.append("^XA") #start of label
    # download and store format, name of format, 
    # end of field data (FS = field stop)
    lines.append("^DFFORMAT^FS") 
    lines.append("^LH0,0") # label home position (label home = LH)
    # AF = assign font F, field number 1 (FN1), 
    # print text at position field origin (FO) rel. to home
    lines.append("^FO360,20^AFN 78,39^FN1^FS")
    # BC=barcode 128, field number 2, Normal orientation, 
    # height 70, no interpreation line. 
    lines.append("^FO70,5^BCN,70,N,N^FN2^FS")
    lines.append("^XZ") #end format

    for copy in xrange(copies):
        lines.append("^XA") #start of label format
        lines.append("^XFFORMAT^FS") #label home position
        lines.append("^FN1^FD"+plateid+"^FS") #this is readable
        lines.append("^FN2^FD"+plateid+"^FS") #this is also readable
        lines.append("^XZ")
    return lines

def makeContainerNameBarcode(plate_name,copies=1):
    """ Constrcut label with container name as human readable """
    lines = []
    lines.append("^XA") #start of label
    # download and store format, name of format, 
    # end of field data (FS = field stop)
    lines.append("^DFFORMAT^FS") 
    lines.append("^LH0,0") # label home position (label home = LH)
    # AF = assign font F, field number 1 (FN1), 
    # print text at position field origin (FO) rel. to home
    if len(plate_name)>21:
        # Use smaller font, fits 28 chars
        lines.append("^FO20,30^ADN 54,30^FN1^FS")
    else:
        # Use larger font, fits 21 chars
        lines.append("^FO20,20^AFN 78,39^FN1^FS")

    lines.append("^XZ") #end format

    for copy in xrange(copies):
        lines.append("^XA") #start of label format
        lines.append("^XFFORMAT^FS") #label home position
        lines.append("^FN1^FD"+plate_name+"^FS") #this is readable
        lines.append("^XZ")
    return lines

def makeOperatorAndDateBarcode(operator,date,copies=1):
    """ Construct label with operator name and date in human readable format"""
    lines = []
    lines.append("^XA") #start of label
    # Download and store format, name of format, 
    # end of field data (FS = field stop)
    lines.append("^DFFORMAT^FS") 
    lines.append("^LH0,0") # label home position (label home = LH)
    # AF = assign font F, field number 1 (FN1), 
    # print text at position field origin (FO) rel. to home
    lines.append("^FO460,30^ADN,36,20^FN1^FS")
    lines.append("^FO20, 30^ADN,36,20^FN2^FS")
    lines.append("^XZ") #end format

    if len(operator)>19:
        operator = operator[:19] # If string is longer, it would cover the date
    for copy in xrange(copies):
        lines.append("^XA") #start of label format
        lines.append("^XFFORMAT^FS") #label home position
        lines.append("^FN1^FD"+date+"^FS") #this is readable
        lines.append("^FN2^FD"+operator+"^FS") #this is also readable
        lines.append("^XZ")
    return lines

def makeProcessNameBarcode(process_name,copies=1):
    """ Constrcut label with process name as human readable """
    lines = []
    lines.append("^XA") #start of label
    # download and store format, name of format, 
    # end of field data (FS = field stop)
    lines.append("^DFFORMAT^FS") 
    lines.append("^LH0,0") # label home position (label home = LH)
    # AF = assign font F, field number 1 (FN1), 
    # print text at position field origin (FO) rel. to home
    if len(process_name)>21:
        # Use smaller font, fits 28 chars
        lines.append("^FO20,30^ADN 54,30^FN1^FS")
    else:
        # Use larger font, fits 21 chars
        lines.append("^FO20,20^AFN 78,39^FN1^FS")

    lines.append("^XZ") #end format

    for copy in xrange(copies):
        lines.append("^XA") #start of label format
        lines.append("^XFFORMAT^FS") #label home position
        lines.append("^FN1^FD"+process_name+"^FS") #this is readable
        lines.append("^XZ")
    return lines
    
def getArgs():
    desc = (" Print barcodes on zebra barcode printer, "
            " different label types available. Information "
            " is fetched from Clarity LIMS.")
    parser = ArgumentParser(description=desc)
    parser.add_argument('--container_id', action='store_true',
                        help=('Print container id label in both '
                        'barcode format and human readable.'))
    parser.add_argument('--operator_and_date',action='store_true',
                        help=('Print label with both operator '
                              'and todays date.'))
    parser.add_argument('--container_name',action='store_true',
                        help=('Print label with human readable'
                              'container name (user defined)'))
    parser.add_argument('--process_name', action='store_true',
                        help=('Print label with human readable'
                              'process name'))
    parser.add_argument('--copies', default=1, type=int,
                        help=('Number of printout copies, only used'
                              ' if neither container_name nor container_id'
                              ' type labels are printed. In that case, print'
                              ' one label of each type for each container.'))
    parser.add_argument('--pid',
                        help='The process LIMS id.')
    parser.add_argument('--log',
                        help='File name to use as log file')
    parser.add_argument('--use_printer',action="store_true",
                        help=('Print file on default or '
                              'supplied printer using lp command.'))
    parser.add_argument('--hostname',
                        help='Hostname for lp CUPS server.')
    parser.add_argument('--destination',
                        help='Name of printer.')
    parser.add_argument('--no_prepend', action='store_true',
                        help='Do not prepend old log, useful when ran locally')
    return parser.parse_args()


def main(args,lims,epp_logger):
    p = Process(lims,id=args.pid)
    lines = []
    cs = []
    if args.container_id:
        cs = p.output_containers()
        for c in cs:
            logging.info('Constructing barcode for container {0}.'.format(c.id))
            lines += makeContainerBarcode(c.id, copies=1)
    if args.container_name:
        cs = p.output_containers()
        for c in cs:
            logging.info('Constructing name label for container {0}.'.format(c.id))
            lines += makeContainerNameBarcode(c.name,copies=1)
    if args.operator_and_date:
        op = p.technician.name
        date = str(datetime.date.today())
        if cs: # list of containers
            copies = len(cs)
        else:
            copies = args.copies
        lines += makeOperatorAndDateBarcode(op,date,copies=copies)
    if args.process_name:
        pn = p.type.name
        if cs: # list of containers
            copies = len(cs)
        else:
            copies = args.copies
        lines += makeProcessNameBarcode(pn,copies=copies)
    if not (args.container_id or args.container_name or 
            args.operator_and_date or args.process_name):
        logging.info('No recognized label type given, exiting.')
        sys.exit(-1)
    if not args.use_printer:
        logging.info('Writing to stdout.')
        epp_logger.saved_stdout.write('\n'.join(lines)+'\n')
    elif lines: # Avoid printing empty files
        lp_args = ["lp"]
        if args.hostname:
            lp_args += ["-h",args.hostname]
        if args.destination:
            lp_args += ["-d",args.destination]
        lp_args.append("-") # lp accepts stdin if '-' is given as filename
        logging.info('Ready to call lp for printing.')
        sp = subprocess.Popen(lp_args, 
                              stdin=subprocess.PIPE, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
        sp.stdin.write(str('\n'.join(lines)))
        logging.info('lp command is called for printing.')
        stdout,stderr = sp.communicate() # Will wait for sp to finish
        logging.info('lp stdout: {0}'.format(stdout))
        logging.info('lp stderr: {0}'.format(stderr))
        logging.info('lp command finished')
        sp.stdin.close()

if __name__ == '__main__':
    arguments = getArgs()
    lims = Lims(BASEURI,USERNAME,PASSWORD)
    lims.check_version()
    prepend = not arguments.no_prepend
    with EppLogger(arguments.log,lims=lims,prepend=prepend) as epp_logger:
        main(arguments,lims,epp_logger)
