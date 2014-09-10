#!/usr/bin/env python
DESC="""EPP script to calculate amount in ng from concentration and volume 
udf:s in Clarity LIMS. The script checks that the 'Volume (ul)' and 
'Concentration' udf:s are defined and that the udf. 'Conc. Units' 
 have the correct value: 'ng/ul', otherwise that artifact is skipped, 
left unchanged, by the script.

Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden
""" 
from argparse import ArgumentParser

from genologics.lims import Lims
from genologics.config import BASEURI,USERNAME,PASSWORD

from genologics.entities import Process
from genologics.epp import EppLogger

import logging
import sys

def apply_calculations(lims,artifacts,udf1,op,udf2,result_udf,epp_logger,process):
    """For each result file of the process: if its corresponding inart has the udf 
    'Dilution Fold', the result_udf: 'Amount (ng)' is calculated as
   
    'Amount (ng)' =  'Concentration'*'Volume (ul)'*'Dilution Fold'
    
    otherwise its calculated as
        
    'Amount (ng)' =  'Concentration'*'Volume (ul)'"""

    logging.info(("result_udf: {0}, udf1: {1}, "
                  "operator: {2}, udf2: {3}").format(result_udf,udf1,op,udf2))
    for artifact in artifacts:
        try:
            artifact.udf[result_udf]
        except KeyError:
            artifact.udf[result_udf]=0

        try:
            inart = process.input_per_sample(artifact.samples[0].name)[0]
            dil_fold = inart.udf['Dilution Fold']
        except:
            dil_fold = None

        logging.info(("Updating: Artifact id: {0}, "
                     "result_udf: {1}, udf1: {2}, "
                     "operator: {3}, udf2: {4}").format(artifact.id, 
                                                        artifact.udf[result_udf],
                                                        artifact.udf[udf1],op,
                                                        artifact.udf[udf2]))
        prod = eval('{0}{1}{2}'.format(artifact.udf[udf1],op,artifact.udf[udf2]))
        if dil_fold:
            prod = eval('{0}{1}{2}'.format(prod, op, dil_fold))
        artifact.udf[result_udf] = prod
        artifact.put()
        logging.info('Updated {0} to {1}.'.format(result_udf,
                                                 artifact.udf[result_udf]))
            
def check_udf_is_defined(artifacts, udf):
    """ Filter and Warn if udf is not defined for any of artifacts. """
    filtered_artifacts = []
    incorrect_artifacts = []
    for artifact in artifacts:
        if (udf in artifact.udf):
            filtered_artifacts.append(artifact)
        else:
            logging.warning(("Found artifact for sample {0} with {1} "
                             "undefined/blank, skipping").format(artifact.samples[0].name, udf))
            incorrect_artifacts.append(artifact)
    return filtered_artifacts, incorrect_artifacts


def check_udf_has_value(artifacts, udf, value):
    """ Filter artifacts on undefined udf or if udf has wrong value. """
    filtered_artifacts = []
    incorrect_artifacts = []
    for artifact in artifacts:
        if udf in artifact.udf and (artifact.udf[udf] == value):
            filtered_artifacts.append(artifact)
        elif udf in artifact.udf:
            incorrect_artifacts.append(artifact)
            logging.warning(("Filtered out artifact for sample: {0}"
                          ", due to wrong {1}").format(artifact.samples[0].name, udf))
        else:
            incorrect_artifacts.append(artifact)
            logging.warning(("Filtered out artifact for sample: {0}"
                          ", due to undefined/blank {1}").format(artifact.samples[0].name, udf))

    return filtered_artifacts, incorrect_artifacts

def main(lims,args,epp_logger):
    p = Process(lims,id = args.pid)
    udf_check = 'Conc. Units'
    value_check = 'ng/ul'
    udf_factor1 = 'Concentration'
    udf_factor2 = 'Volume (ul)'
    result_udf = 'Amount (ng)'

    if args.aggregate:
        artifacts = p.all_inputs(unique=True)
    else:
        all_artifacts = p.all_outputs(unique=True)
        artifacts = filter(lambda a: a.output_type == "ResultFile" ,all_artifacts)

    correct_artifacts, wrong_factor1 = check_udf_is_defined(artifacts, udf_factor1)
    correct_artifacts, wrong_factor2 = check_udf_is_defined(correct_artifacts, udf_factor2)

    correct_artifacts, wrong_value = check_udf_has_value(correct_artifacts, udf_check, value_check)

    if correct_artifacts:
        apply_calculations(lims, correct_artifacts, udf_factor1, '*',
                           udf_factor2, result_udf, epp_logger, p)

    d = {'ca': len(correct_artifacts),
         'ia': len(wrong_factor1)+ len(wrong_factor2) + len(wrong_value)}

    abstract = ("Updated {ca} artifact(s), skipped {ia} artifact(s) with "
                "wrong and/or blank values for some udfs.").format(**d)

    print >> sys.stderr, abstract # stderr will be logged and printed in GUI


if __name__ == "__main__":
    # Initialize parser with standard arguments and description
    parser = ArgumentParser(description=DESC)
    parser.add_argument('--pid',
                        help='Lims id for current Process')
    parser.add_argument('--log',
                        help='Log file for runtime info and errors.')
    parser.add_argument('--aggregate', action='store_true',
                        help=('Use this tag if current Process is an '
                              'aggregate QC step'))
    args = parser.parse_args()

    lims = Lims(BASEURI, USERNAME, PASSWORD)
    lims.check_version()

    with EppLogger(args.log, lims=lims, prepend=True) as epp_logger:
        main(lims, args, epp_logger)
