"""Python interface to GenoLogics LIMS via its REST API.

Entities and their descriptors for the LIMS interface.

Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
Copyright (C) 2012 Per Kraulis
"""

import re
from xml.etree import ElementTree

_NSMAP = dict(
        art='http://genologics.com/ri/artifact',
        artgr='http://genologics.com/ri/artifactgroup',
        cnf='http://genologics.com/ri/configuration',
        con='http://genologics.com/ri/container',
        ctp='http://genologics.com/ri/containertype',
        exc='http://genologics.com/ri/exception',
        file='http://genologics.com/ri/file',
        inst='http://genologics.com/ri/instrument',
        lab='http://genologics.com/ri/lab',
        prc='http://genologics.com/ri/process',
        prj='http://genologics.com/ri/project',
        prop='http://genologics.com/ri/property',
        protcnf='http://genologics.com/ri/protocolconfiguration',
        protstepcnf='http://genologics.com/ri/stepconfiguration',
        prx='http://genologics.com/ri/processexecution',
        ptm='http://genologics.com/ri/processtemplate',
        ptp='http://genologics.com/ri/processtype',
        res='http://genologics.com/ri/researcher',
        ri='http://genologics.com/ri',
        rt='http://genologics.com/ri/routing',
        rtp='http://genologics.com/ri/reagenttype',
        kit='http://genologics.com/ri/reagentkit',
        lot='http://genologics.com/ri/reagentlot',
        smp='http://genologics.com/ri/sample',
        stg='http://genologics.com/ri/stage',
        stp='http://genologics.com/ri/step',
        udf='http://genologics.com/ri/userdefined',
        ver='http://genologics.com/ri/version',
        wkfcnf='http://genologics.com/ri/workflowconfiguration'
)

for prefix, uri in list(_NSMAP.items()):
    ElementTree._namespace_map[uri] = prefix

_NSPATTERN = re.compile(r'(\{)(.+?)(\})')


def nsmap(tag):
    "Convert from normal XML-ish namespace tag to ElementTree variant."
    parts = tag.split(':')
    if len(parts) != 2:
        raise ValueError("no namespace specifier in tag")
    return "{%s}%s" % (_NSMAP[parts[0]], parts[1])
