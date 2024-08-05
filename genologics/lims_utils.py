#!/usr/bin/env python


from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.lims import Artifact, Lims

lims = Lims(BASEURI, USERNAME, PASSWORD)


def get_run_info(fc):
    fc_summary = {}
    for iom in fc.input_output_maps:
        art = iom[0]["uri"]
        lane = art.location[1].split(":")[0]
        if lane not in fc_summary:
            fc_summary[lane] = dict(list(art.udf.items()))  # "%.2f" % val ----round??
    return fc_summary


def procHistory(proc, samplename):
    """Quick way to get the ids of parent processes from the given process,
    while staying in a sample scope"""
    hist = []
    artifacts = lims.get_artifacts(sample_name=samplename, type="Analyte")
    not_done = True
    starting_art = proc.input_per_sample(samplename)[0].id
    while not_done:
        not_done = False
        for o in artifacts:
            if o.id == starting_art:
                if o.parent_process is None:
                    # flow control : if there is no parent process, we can stop iterating, we're done.
                    not_done = False
                    break  # breaks the for artifacts, we are done anyway.
                else:
                    not_done = True  # keep the loop running
                hist.append(o.parent_process.id)
                for i in o.parent_process.all_inputs():
                    if i in artifacts:
                        # while increment
                        starting_art = i.id

                        break  # break the for allinputs, if we found the right one
                break  # breaks the for artifacts if we matched the current one
    return hist


def get_sequencing_info(fc):
    """Input: a process object 'fc', of type 'Illumina Sequencing (Illumina SBS) 4.0',
    Output: A dictionary where keys are lanes 1,2,...,8, and values are lane artifact udfs"""
    fc_summary = {}
    for iom in fc.input_output_maps:
        art = Artifact(lims, id=iom[0]["limsid"])
        lane = art.location[1].split(":")[0]
        if lane not in fc_summary:
            fc_summary[lane] = dict(list(art.udf.items()))  # "%.2f" % val ----round??
            fc_summary[lane]["qc"] = art.qc_flag
    return fc_summary


def make_sample_artifact_maps(sample_name):
    """outin: connects each out_art for a specific sample to its
    corresponding in_art and process. one-one relation"""
    outin = {}
    artifacts = lims.get_artifacts(sample_name=sample_name, type="Analyte")
    for outart in artifacts:
        try:
            pro = outart.parent_process
            inarts = outart.input_artifact_list()
            for inart in inarts:
                for samp in inart.samples:
                    if samp.name == sample_name:
                        outin[outart.id] = (pro, inart.id)
        except:
            pass
    return outin
