#!/usr/bin/env python

"""Script to load project info from Lims into the project database in statusdb.

Maya Brandi, Science for Life Laboratory, Stockholm, Sweden.
"""
import sys
import os
import codecs
from optparse import OptionParser
from statusDB_utils import *
from helpers import *
from pprint import pprint
from genologics.lims import *
from genologics.config import BASEURI, USERNAME, PASSWORD
import objectsDB as DB
from datetime import date
import scilifelab.log
lims = Lims(BASEURI, USERNAME, PASSWORD)

def  main(proj_name, all_projects, days, conf):
    first_of_july = '2013-01-30'#'2013-06-30'
    today = date.today()
    couch = load_couch_server(conf)
    proj_db = couch['analysis']#['projects']
    if all_projects:
        projects = lims.get_projects()
        for proj in projects:
            try:
                closed = proj.close_date
                closed = date(*map(int, proj.close_date.split('-')))
                delta = today-closed
                delta = delta.days 
            except:
                delta = 0
            opened = proj.open_date
            if opened:
                if comp_dates(first_of_july, opened) and (delta < days):
                    proj_time = time.time()
                    obj = DB.ProjectDB(proj.id)
                    key = find_proj_from_view(proj_db, proj.name)
                    obj.project['_id'] = find_or_make_key(key)
                    info = save_couchdb_obj(proj_db, obj.project)
                    LOG.info('project %s %s : _id = %s' % (proj.name, info, obj.project['_id']))
            else:
                LOG.info('Open date missing for project %s' % proj.name)
    elif proj_name is not None:
        proj = lims.get_projects(name = proj_name)
        if len(proj) == 0:
            LOG.warning('No project named %s in Lims' % proj_name)
        else:
            proj = proj[0]
            opened = proj.open_date
            if opened:
                if comp_dates(first_of_july, opened):
                    obj = DB.ProjectDB(proj.id)
                    key = find_proj_from_view(proj_db, proj.name)
                    obj.project['_id'] = find_or_make_key(key)
                    info = save_couchdb_obj(proj_db, obj.project)
                    LOG.info('project %s %s : _id = %s' % (proj_name, info, obj.project['_id']))
            else:
                LOG.info('Open date missing for project %s' % proj.name)

if __name__ == '__main__':
    usage = "Usage:       python project_summary_upload_LIMS.py [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-p", "--project", dest="project_name", default=None,
    help = "eg: M.Uhlen_13_01. Dont use with -a flagg.")

    parser.add_option("-a", "--all_projects", dest="all_projects", action="store_true", default=False,
    help = "Upload all Lims projects into couchDB. Don't use with -f flagg.")

    parser.add_option("-d", "--days", dest="days", default=30,         
    help="Projects with a close_date older than DAYS days are not updated. Default is 30 days. Use with -a flagg")

    parser.add_option("-c", "--conf", dest="conf", 
    default=os.path.join(os.environ['HOME'],'opt/config/post_process.yaml'),         
    help = "Config file.  Default: ~/opt/config/post_process.yaml")

    (options, args) = parser.parse_args()

    LOG = scilifelab.log.file_logger('LOG', options.conf, 'lims2db_projects.log')
    main(options.project_name, options.all_projects, options.days, options.conf)

