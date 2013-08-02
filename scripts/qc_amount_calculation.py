#!/usr/bin/env python
"""EPP script to perform basic calculations on UDF:s in Clarity LIMS
Command to trigger this script:
bash -c "PATH/TO/INSTALLED/SCRIPT
--pid {processLuid} 
--log {compoundOutputFileLuidN}"
"

Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden
""" 
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import configure_logging

def apply_calculations(lims,artifacts,udf1,op,udf2,result_udf):
    print ("result_udf: {0}, udf1: {1}, "
           "operator: {2}, udf2: {3}").format(result_udf,udf1,op,udf2)
    for artifact in artifacts:
        try:
            artifact.udf[result_udf]
        except KeyError:
            artifact.udf[result_udf]=0

        print ("Updating: Artifact id: {0}, "
               "result_udf: {1}, udf1: {2}, "
               "operator: {3}, udf2: {4}").format(artifact.id, 
                                                  artifact.udf[result_udf],
                                                  artifact.udf[udf1],op,
                                                  artifact.udf[udf2])
        artifact.udf[result_udf] = eval(
            '{0}{1}{2}'.format(artifact.udf[udf1],op,artifact.udf[udf2]))
        artifact.put()
        print 'Updated {0} to {1}.'.format(result_udf,artifact.udf[result_udf])

def main(lims,args):
    p = Process(lims,id = args.pid)
    inputs = p.all_inputs(unique=True)
    filtered_inputs = filter(lambda a: a.udf['Conc. Units']=='ng/ul',inputs)
    print ("Filtered out {0} artifacts with other "
           "Conc. Unit than 'ng/ul'").format(len(inputs)-len(filtered_inputs))
    apply_calculations(lims,inputs,'Concentration','*',
                       'Volume (ul)','Amount (ng)')


if __name__ == "__main__":
    # Initialize parser with standard arguments and description
    desc = """EPP script to calculate amount in ng from concentration 
and volume udf:s in Clarity LIMS. """

    parser = ArgumentParser(description=desc)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('--log',
                        help='Log file')
    args = parser.parse_args()

    # Start logging
    if args.log:
        configure_logging(args.log)
    lims = Lims(BASEURI,USERNAME,PASSWORD)
    lims.check_version()

    main(lims, args)

