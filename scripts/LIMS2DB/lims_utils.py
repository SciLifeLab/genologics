#!/usr/bin/env python

"""A module with lims help functions.

Maya Brandi, Science for Life Laboratory, Stockholm, Sweden.
"""

from genologics.lims import *
from genologics.config import BASEURI, USERNAME, PASSWORD
lims = Lims(BASEURI, USERNAME, PASSWORD)

"""process category dictionaries

In the LIMS2DB context, processes are categorised into groups that define, 
or are used to define a certain type of statusdb key. The categories and their 
processes are defined here:"""

INITALQC = {'63' : 'Quant-iT QC (DNA) 4.0',
    '65' : 'Quant-iT QC (RNA) 4.0',
    '66' : 'Qubit QC (DNA) 4.0',
    '68' : 'Qubit QC (RNA) 4.0',
    '24' : 'Customer Gel QC',
    '20' : 'CaliperGX QC (DNA)',
    '16' : 'Bioanalyzer QC (DNA) 4.0',
    '18' : 'Bioanalyzer QC (RNA) 4.0',
    '116' : 'CaliperGX QC (RNA)',
    '48' : 'NanoDrop QC (DNA) 4.0'}
AGRINITQC = {'7' : 'Aggregate QC (DNA) 4.0',
    '9' : 'Aggregate QC (RNA) 4.0'}
PREPSTART = {'10' : 'Aliquot Libraries for Hybridization (SS XT)',
    '47' : 'mRNA Purification, Fragmentation & cDNA synthesis (TruSeq RNA) 4.0',
    '33' : 'Fragment DNA (TruSeq DNA) 4.0'}
PREPEND = {'111' : 'Amplify Captured Libraries to Add Index Tags (SS XT) 4.0',
    '109' : 'CA Purification'}
LIBVAL = {'62' : 'qPCR QC (Library Validation) 4.0',
    '64' : 'Quant-iT QC (Library Validation) 4.0',
    '67' : 'Qubit QC (Library Validation) 4.0',
    '20' : 'CaliperGX QC (DNA)',
    '17' : 'Bioanalyzer QC (Library Validation) 4.0'}
AGRLIBVAL ={'8': 'Aggregate QC (Library Validation) 4.0'}
SEQSTART = {'40' : 'Library Normalization (MiSeq) 4.0',
    '39' : 'Library Normalization (Illumina SBS) 4.0'}
SEQUENCING = {'38' : 'Illumina Sequencing (Illumina SBS) 4.0',
    '46' : 'MiSeq Run (MiSeq) 4.0'}

def get_sequencing_info(fc):
    """Input: a process object 'fc', of type 'Illumina Sequencing (Illumina SBS) 4.0',
    Output: A dictionary where keys are lanes 1,2,...,8, and values are lane artifact udfs"""
    fc_summary={}
    for iom in fc.input_output_maps:
        art = iom[0]['uri']
        lane = art.location[1].split(':')[0]
        if not fc_summary.has_key(lane):
                 fc_summary[lane]= dict(art.udf.items()) #"%.2f" % val ----round??
    return fc_summary



def make_sample_artifact_maps(sample_name):
    """
    outin: connects each out_art for a specific sample to its 
    corresponding in_art and process. one-one relation
    
    inout: connects each in_art for a specific sample to all its 
    coresponding out_arts and processes. one-many relation"""
    outin = {}
    inout = {}
    artifacts = lims.get_artifacts(sample_name = sample_name)
    for outart in artifacts:
        try:
            pro = outart.parent_process
            inarts = outart.input_artifact_list()
            for inart in inarts:
                for samp in inart.samples:
                    if samp.name == sample_name:
                        outin[outart.id] = (pro, inart.id)
                        if not inout.has_key(inart.id): inout[inart.id] = {}
                        inout[inart.id][pro] = outart.id
        except:
            pass
    return outin, inout

def get_analyte_hist(analyte, outin, inout):
    """Makes a history map of an analyte, using the inout-map 
    and outin-map of the corresponding sample."""
    history = {}
    while outin.has_key(analyte):
        hist_process, inart = outin[analyte]
        for process, outart in inout[inart].items():
            if (process == hist_process) or (process.type.id in INITALQC.keys()) or (process.type.id in LIBVAL.keys()) or (process.type.id in AGRINITQC.keys()) or (process.type.id in AGRLIBVAL.keys()):
                history[process.id] = {'date' : process.date_run,
                            'id' : process.id,
                            'outart' : outart,
                            'inart' : inart,
                            'type' : process.type.id,
                            'name' : process.type.name}
        analyte = inart
    return history

