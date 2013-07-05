#!/usr/bin/env python

"""Script to load runinfo from the lims process: 'Illumina Sequencing (Illumina SBS) 4.0' 
into the flowcell database in statusdb.

Maya Brandi, Science for Life Laboratory, Stockholm, Sweden.
"""
import sys
import os
import codecs
from optparse import OptionParser
from pprint import pprint
from genologics.lims import *
from genologics.config import BASEURI, USERNAME, PASSWORD
from datetime import date
import genologics.lims_utils as lims_utils
from statusDB_utils import *
import scilifelab.log
lims = Lims(BASEURI, USERNAME, PASSWORD)

def  main(flowcell, all_flowcells,days,conf):
    """If all_flowcells: all runs run less than a moth ago are uppdated"""
    today = date.today()
    couch = load_couch_server(conf)
    fc_db = couch['flowcells']
    if all_flowcells:
        flowcells = lims.get_processes(type = 'Illumina Sequencing (Illumina SBS) 4.0')
        for fc in flowcells:
            try:
                closed = date(*map(int, fc.date_run.split('-')))
                delta = today-closed
                if delta.days < days:
                    flowcell_name = dict(fc.udf.items())['Flow Cell Position'] + dict(fc.udf.items())['Flow Cell ID']
                    key = find_flowcell_from_view(fc_db, flowcell_name)
                    if key:
                        dbobj = fc_db.get(key)
                        dbobj["illumina"]["run_summary"] = lims_utils.get_sequencing_info(fc)
                        info = save_couchdb_obj(fc_db, dbobj)
                        LOG.info('flowcell %s %s : _id = %s' % (flowcell_name, info, key))
            except:
                pass
    elif flowcell is not None:
        try:
            flowcell_name = flowcell[1:len(flowcell)]
            flowcell_position = flowcell[0]
            fc = lims.get_processes(type = 'Illumina Sequencing (Illumina SBS) 4.0', 
            udf = {'Flow Cell ID':flowcell_name,'Flow Cell Position':flowcell_position})[0]
            key = find_flowcell_from_view(fc_db, flowcell)
            if key:
                dbobj = fc_db.get(key)
                dbobj["illumina"]["run_summary"] = lims_utils.get_sequencing_info(fc)
                info = save_couchdb_obj(fc_db, dbobj)
                LOG.info('flowcell %s %s : _id = %s' % (flowcell_name, info, key))
        except:
            pass

if __name__ == '__main__':
    usage = "Usage:       python flowcell_summary_upload_LIMS.py [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-f", "--flowcell", dest="flowcell_name", default=None, 
    help = "eg: AD1TAPACXX. Don't use with -a flagg.")

    parser.add_option("-a", "--all_flowcells", dest="all_flowcells", action="store_true", default=False, 
    help = "Uploads all Lims flowcells into couchDB. Don't use with -f flagg.")

    parser.add_option("-d", "--days", dest="days", default=30, 
    help="Runs older than DAYS days are not updated. Default is 30 days. Use with -a flagg")

    parser.add_option("-c", "--conf", dest="conf", 
    default=os.path.join(os.environ['HOME'],'opt/config/post_process.yaml'), 
    help = "Config file.  Default: ~/opt/config/post_process.yaml")

    (options, args) = parser.parse_args()

    LOG = scilifelab.log.file_logger('LOG', options.conf, 'lims2db_flowcells.log')
    main(options.flowcell_name, options.all_flowcells, options.days, options.conf)

