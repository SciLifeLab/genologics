#!/usr/bin/env python
import sys
import os
import codecs
from optparse import OptionParser
from pprint import pprint
import couchdb
import bcbio.pipeline.config_loader as cl
from genologics.lims import *
from genologics.config import BASEURI, USERNAME, PASSWORD
from datetime import date
import genologics.lims_utils as LU
from statusDB_utils import *

def  main(couch, lims, flowcell_name, all_flowcells):
        """If all_flowcells: all runs run less than a moth ago are uppdated"""
        today = date.today()
        fc_db = couch['flowcells']
        info = None
        if all_flowcells:
		flowcells = lims.get_processes(type = 'Illumina Sequencing (Illumina SBS) 4.0')
                for fc in flowcells:
                        closed = date(*map(int, fc.date_run.split('-')))
                        delta = today-closed
                        if delta.days < 30:
				flowcell_name = dict(fc.udf.items())['Flow Cell Position'] + dict(fc.udf.items())['Flow Cell ID']
				key = find_flowcell_from_view(fc_db, flowcell_name)
				if key:
					dbobj = fc_db.get(key)
					run_info = LU.get_run_info(fc)
					dbobj["illumina"]["run_summary"] = run_info
					save_couchdb_obj(fc_db, dbobj)

        elif flowcell_name is not None:
		fc = lims.get_processes(type = 'Illumina Sequencing (Illumina SBS) 4.0', udf = {'Flow Cell ID':flowcell_name})
		if len(fc) > 0:
			print fc
			key = find_flowcell_from_view(fc_db, flowcell_name)
			if key:
               			dbobj = fc_db.get(key)
				run_info = LU.get_run_info(fc)
				dbobj["illumina"]["run_summary"] = run_info
				save_couchdb_obj(fc_db, dbobj)
		

if __name__ == '__main__':
        usage = """Usage:       python project_summary_upload.py [options]

Options (Only one option is acceptab):
        -a,                     upploads all Lims flowcells into couchDB
        -p <project_ID>,        upploads the project <flowcell_name> into couchDB                                         
"""
        parser = OptionParser(usage=usage)
        parser.add_option("-f", "--flowcell", dest="flowcell_name", default=None)
        parser.add_option("-a", "--all_flowcells", dest="all_flowcells", action="store_true", default=False)
        (options, args) = parser.parse_args()

        config_file = os.path.join(os.environ['HOME'], 'opt/config/post_process.yaml')
        db_conf = cl.load_config(config_file)['couch_db']
        url = db_conf['maggie_login']+':'+db_conf['maggie_pass']+'@'+db_conf['maggie_url']+':'+str(db_conf['maggie_port'])
        couch = couchdb.Server("http://" + url)
	lims = Lims(BASEURI, USERNAME, PASSWORD)
        main(couch, lims, options.flowcell_name, options.all_flowcells)
