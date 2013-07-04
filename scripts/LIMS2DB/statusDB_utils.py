#!/usr/bin/env python
from uuid import uuid4
import time
from  datetime  import  datetime
import couchdb
import bcbio.pipeline.config_utils as cl

def load_couch_server(config_file):
    """loads couch server with settings specified in 'config_file'"""
    try:
        db_conf = cl.load_config(config_file)['couch_db']
        url = db_conf['maggie_login']+':'+db_conf['maggie_pass']+'@'+db_conf['maggie_url']+':'+str(db_conf['maggie_port'])
        couch = couchdb.Server("http://" + url)
        return couch
    except:
        return None

def find_or_make_key(key):
    if not key:
        key = uuid4().hex
    return key

def save_couchdb_obj(db, obj):
    """Updates ocr creates the object obj in database db."""
    dbobj = db.get(obj['_id'])
    time_log = datetime.utcnow().isoformat() + "Z"
    if dbobj is None:
        obj["creation_time"] = time_log
        obj["modification_time"] = time_log
        db.save(obj)
        return 'created'
    else:
        obj["_rev"] = dbobj.get("_rev")
        del dbobj["modification_time"]
        obj["creation_time"] = dbobj["creation_time"]
        if not comp_obj(obj, dbobj):
            obj["modification_time"] = time_log
            db.save(obj)
            return 'uppdated'
    return 'not uppdated'

def comp_obj(obj, dbobj):
    """compares the two dictionaries obj and dbobj"""
    keys = list(set(obj.keys() + dbobj.keys()))
    for key in keys:
        if (obj.has_key(key)) and dbobj.has_key(key):
            if (obj[key] != dbobj[key]):
                return False
        else:
            return False
    return True

def find_proj_from_view(proj_db, project_name):
    view = proj_db.view('project/project_name')
    for proj in view:
        if proj.key == project_name:
            return proj.value
    return None

def find_samp_from_view(samp_db, proj_name):
    view = samp_db.view('names/id_to_proj')
    samps = {}
    for doc in view:
        if (doc.value[0] == proj_name)|(doc.value[0] == proj_name.lower()):
            samps[doc.key] = doc.value[1:3]
    return samps

def find_flowcell_from_view(flowcell_db, flowcell_name):
    view = flowcell_db.view('names/id_to_name')
    for doc in view:
        id = doc.value.split('_')[1]
        if (id == flowcell_name):
            return doc.key

def find_sample_run_id_from_view(samp_db,sample_run):
    view = samp_db.view('names/id_to_name')
    for doc in view:
        if doc.value == sample_run:
            return doc.key
    return None


