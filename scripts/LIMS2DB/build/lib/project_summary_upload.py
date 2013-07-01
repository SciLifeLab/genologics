#!/usr/bin/env python
import sys
import os
import codecs
from statusDB_utils import *
from pprint import pprint
from genologics.lims import *
from genologics.config import BASEURI, USERNAME, PASSWORD
import objectsDB as DB
import couchdb
import bcbio.pipeline.config_loader as cl

def  main(couch, lims, proj_name, all_projects):
        proj_db = couch['analysis']#projects']
        info = None
        if all_projects:
		projects = lims.get_projects()
		for proj in projects:
			obj = DB.ProjectDB(proj.id)
			obj.obj['_id'] = find_or_make_key(proj_db, proj.name)
			info = save_couchdb_obj(proj_db, obj.obj)
	elif proj_name is not None:
		proj = lims.get_projects(name = proj_name)[0]
		obj = DB.ProjectDB(proj.id)
		obj.obj['_id'] = find_or_make_key(proj_db, proj.name)
		info = save_couchdb_obj(proj_db, obj.obj)
	#else:
#		logger.debug('Argument error')
	

f __name__ == '__main__':
        usage = """Usage:       python project_summary_upload.py [options]

Options (Only one option is acceptab):
        -a,                     upploads all Lims projects into couchDB
        -p <project_ID>,        upploads the project <project_ID> into couchDB                                         
"""
        parser = OptionParser(usage=usage)
        parser.add_option("-p", "--project", dest="project_name", default=None)
        parser.add_option("-a", "--all_projects", dest="all_projects", action="store_true", default=False)
        (options, args) = parser.parse_args()

        config_file = os.path.join(os.environ['HOME'], 'opt/config/post_process.yaml')
        db_conf = cl.load_config(config_file)['couch_db']
	url = db_conf['maggie_login']+':'+db_conf['maggie_pass']+'@'+db_conf['maggie_url']+':'+str(db_conf['maggie_port'])
	couch = couchdb.Server("http://" + url)
	lims = Lims(BASEURI, USERNAME, PASSWORD)


        main(couch, lims, options.project_name, options.all_projects)


