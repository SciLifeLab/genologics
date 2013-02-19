"""Python interface to GenoLogics LIMS via its REST API.

LIMS interface.

Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
Copyright (C) 2012 Per Kraulis
"""

__all__ = ['Lab', 'Researcher', 'Project', 'Sample',
           'Containertype', 'Container', 'Processtype', 'Process',
           'Artifact', 'Lims']

import urllib
from cStringIO import StringIO

# http://docs.python-requests.org/
import requests

from .entities import *


class Lims(object):
    "LIMS interface through which all entity instances are retrieved."

    VERSION = 'v2'

    def __init__(self, baseuri, username, password):
        """baseuri: Base URI for the GenoLogics server, excluding
                    the 'api' or version parts!
                    For example: https://genologics.scilifelab.se:8443/
        username: The account name of the user to login as.
        password: The password for the user account to login as.
        """
        self.baseuri = baseuri.rstrip('/') + '/'
        self.username = username
        self.password = password
        self.cache = dict()

    def get_uri(self, *segments, **query):
        "Return the full URI given the path segments and optional query."
        segments = ['api', self.VERSION] + list(segments)
        url = urlparse.urljoin(self.baseuri, '/'.join(segments))
        if query:
            url += '?' + urllib.urlencode(query)
        return url

    def get(self, uri, params=dict()):
        "GET data from the URI. Return the response XML as an ElementTree."
        r = requests.get(uri, params=params,
                         auth=(self.username, self.password),
                         headers=dict(accept='application/xml'))
        return self.parse_response(r)

    def put(self, uri, data, params=dict()):
        """PUT the serialized XML to the given URI.
        Return the response XML as an ElementTree.
        """
        r = requests.put(uri, data=data, params=params,
                         auth=(self.username, self.password),
                         headers={'content-type':'application/xml',
                                  'accept': 'application/xml'})
        return self.parse_response(r)

    def post(self, uri, data, params=dict()):
        """POST the serialized XML to the given URI.
        Return the response XML as an ElementTree.
        """
        r = requests.post(uri, data=data, params=params,
                          auth=(self.username, self.password),
                          headers={'content-type': 'application/xml',
                                   'accept': 'application/xml'})
        return self.parse_response(r)

    def check_version(self):
        """Raise ValueError if the version for this interface
        does not match any of the versions given for the API.
        """
        uri = urlparse.urljoin(self.baseuri, 'api')
        r = requests.get(uri, auth=(self.username, self.password))
        root = self.parse_response(r)
        tag = nsmap('ver:versions')
        assert tag == root.tag
        for node in root.findall('version'):
            if node.attrib['major'] == self.VERSION: return
        raise ValueError('version mismatch')

    def parse_response(self, response):
        """Parse the XML returned in the response.
        Raise an HTTP error if the response status is not 200.
        """
        root = ElementTree.fromstring(response.content)
        if response.status_code != 200:
            node = root.find('message')
            if node is None:
                response.raise_for_status()
            message = "%s: %s" % (response.status_code, node.text)
            node = root.find('suggested-actions')
            if node is not None:
                message += ' ' + node.text
            raise requests.exceptions.HTTPError(message)
        return root

    def get_labs(self, name=None, last_modified=None,
                 udf=dict(), udtname=None, udt=dict(), start_index=None):
        """Get a list of labs, filtered by keyword arguments.
        name: Lab name, or list of names.
        last_modified: Since the given ISO format datetime.
        udf: dictionary of UDFs with 'UDFNAME[OPERATOR]' as keys.
        udtname: UDT name, or list of names.
        udt: dictionary of UDT UDFs with 'UDTNAME.UDFNAME[OPERATOR]' as keys
             and a string or list of strings as value.
        start_index: Page to retrieve; all if None.
        """
        params = self._get_params(name=name,
                                  last_modified=last_modified,
                                  start_index=start_index)
        params.update(self._get_params_udf(udf=udf, udtname=udtname, udt=udt))
        return self._get_instances(Lab, params=params)

    def get_researchers(self, firstname=None, lastname=None, username=None,
                        last_modified=None,
                        udf=dict(), udtname=None, udt=dict(),start_index=None):
        """Get a list of researchers, filtered by keyword arguments.
        firstname: Researcher first name, or list of names.
        lastname: Researcher last name, or list of names.
        username: Researcher account name, or list of names.
        last_modified: Since the given ISO format datetime.
        udf: dictionary of UDFs with 'UDFNAME[OPERATOR]' as keys.
        udtname: UDT name, or list of names.
        udt: dictionary of UDT UDFs with 'UDTNAME.UDFNAME[OPERATOR]' as keys
             and a string or list of strings as value.
        start_index: Page to retrieve; all if None.
        """
        params = self._get_params(firstname=firstname,
                                  lastname=lastname,
                                  username=username,
                                  last_modified=last_modified,
                                  start_index=start_index)
        params.update(self._get_params_udf(udf=udf, udtname=udtname, udt=udt))
        return self._get_instances(Researcher, params=params)

    def get_projects(self, name=None, open_date=None, last_modified=None,
                     udf=dict(), udtname=None, udt=dict(), start_index=None):
        """Get a list of projects, filtered by keyword arguments.
        name: Project name, or list of names.
        open_date: Since the given ISO format date.
        last_modified: Since the given ISO format datetime.
        udf: dictionary of UDFs with 'UDFNAME[OPERATOR]' as keys.
        udtname: UDT name, or list of names.
        udt: dictionary of UDT UDFs with 'UDTNAME.UDFNAME[OPERATOR]' as keys
             and a string or list of strings as value.
        start_index: Page to retrieve; all if None.
        """
        params = self._get_params(name=name,
                                  open_date=open_date,
                                  last_modified=last_modified,
                                  start_index=start_index)
        params.update(self._get_params_udf(udf=udf, udtname=udtname, udt=udt))
        return self._get_instances(Project, params=params)

    def get_samples(self, name=None, projectname=None, projectlimsid=None,
                    udf=dict(), udtname=None, udt=dict(), start_index=None):
        """Get a list of samples, filtered by keyword arguments.
        name: Sample name, or list of names.
        projectlimsid: Samples for the project of the given LIMS id.
        projectname: Samples for the project of the name.
        udf: dictionary of UDFs with 'UDFNAME[OPERATOR]' as keys.
        udtname: UDT name, or list of names.
        udt: dictionary of UDT UDFs with 'UDTNAME.UDFNAME[OPERATOR]' as keys
             and a string or list of strings as value.
        start_index: Page to retrieve; all if None.
        """
        params = self._get_params(name=name,
                                  projectname=projectname,
                                  projectlimsid=projectlimsid,
                                  start_index=start_index)
        params.update(self._get_params_udf(udf=udf, udtname=udtname, udt=udt))
        return self._get_instances(Sample, params=params)

    def get_artifacts(self, name=None, type=None, process_type=None,
                      artifact_flag_name=None, working_flag=None, qc_flag=None,
                      sample_name=None, artifactgroup=None, containername=None,
                      containerlimsid=None, reagent_label=None,
                      udf=dict(), udtname=None, udt=dict(), start_index=None):
        """Get a list of artifacts, filtered by keyword arguments.
        name: Artifact name, or list of names.
        type: Artifact type, or list of types.
        process_type: Produced by the process type, or list of types.
        artifact_flag_name: Tagged with the genealogy flag, or list of flags.
        working_flag: Having the given working flag; boolean.
        qc_flag: Having the given QC flag: UNKNOWN, PASSED, FAILED.
        sample_name: Related to the given sample name.
        artifactgroup: Belonging to the artifact group (experiment in client).
        containername: Residing in given container, by name, or list.
        containerlimsid: Residing in given container, by LIMS id, or list.
        reagent_label: having attached reagent labels.
        udf: dictionary of UDFs with 'UDFNAME[OPERATOR]' as keys.
        udtname: UDT name, or list of names.
        udt: dictionary of UDT UDFs with 'UDTNAME.UDFNAME[OPERATOR]' as keys
             and a string or list of strings as value.
        start_index: Page to retrieve; all if None.
        """
        params = self._get_params(name=name,
                                  type=type,
                                  process_type=process_type,
                                  artifact_flag_name=artifact_flag_name,
                                  working_flag=working_flag,
                                  qc_flag=qc_flag,
                                  sample_name=sample_name,
                                  artifactgroup=artifactgroup,
                                  containername=containername,
                                  containerlimsid=containerlimsid,
                                  reagent_label=reagent_label,
                                  start_index=start_index)
        params.update(self._get_params_udf(udf=udf, udtname=udtname, udt=udt))
        return self._get_instances(Artifact, params=params)

    def get_containers(self, name=None, type=None,
                       state=None, last_modified=None,
                       udf=dict(), udtname=None, udt=dict(), start_index=None):
        """Get a list of containers, filtered by keyword arguments.
        name: Containers name, or list of names.
        type: Container type, or list of types.
        state: Container state: Empty, Populated, Discarded, Reagent-Only.
        last_modified: Since the given ISO format datetime.
        udf: dictionary of UDFs with 'UDFNAME[OPERATOR]' as keys.
        udtname: UDT name, or list of names.
        udt: dictionary of UDT UDFs with 'UDTNAME.UDFNAME[OPERATOR]' as keys
             and a string or list of strings as value.
        start_index: Page to retrieve; all if None.
        """
        params = self._get_params(name=name,
                                  type=type,
                                  state=state,
                                  last_modified=last_modified,
                                  start_index=start_index)
        params.update(self._get_params_udf(udf=udf, udtname=udtname, udt=udt))
        return self._get_instances(Container, params=params)

    def get_processes(self, last_modified=None, type=None,
                      inputartifactslimsid=None,
                      techfirstname=None, techlastname=None, projectname=None,
                      udf=dict(), udtname=None, udt=dict(), start_index=None):
        """Get a list of processes, filtered by keyword arguments.
        last_modified: Since the given ISO format datetime.
        type: Process type, or list of types.
        inputartifactslimsid: Input artifact LIMS id, or list of.
        udf: dictionary of UDFs with 'UDFNAME[OPERATOR]' as keys.
        udtname: UDT name, or list of names.
        udt: dictionary of UDT UDFs with 'UDTNAME.UDFNAME[OPERATOR]' as keys
             and a string or list of strings as value.
        techfirstname: First name of researcher, or list of.
        techlastname: Last name of researcher, or list of.
        projectname: Name of project, or list of.
        start_index: Page to retrieve; all if None.
        """
        params = self._get_params(last_modified=last_modified,
                                  type=type,
                                  inputartifactslimsid=inputartifactslimsid,
                                  techfirstname=techfirstname,
                                  techlastname=techlastname,
                                  projectname=projectname,
                                  start_index=start_index)
        params.update(self._get_params_udf(udf=udf, udtname=udtname, udt=udt))
        return self._get_instances(Process, params=params)

    def _get_params(self, **kwargs):
        "Convert keyword arguments to a kwargs dictionary."
        result = dict()
        for key, value in kwargs.iteritems():
            if value is None: continue
            result[key.replace('_', '-')] = value
        return result

    def _get_params_udf(self, udf=dict(), udtname=None, udt=dict()):
        "Convert UDF-ish arguments to a params dictionary."
        result = dict()
        for key, value in udf.iteritems():
            result["udf.%s" % key] = value
        if udtname is not None:
            result['udt.name'] = udtname
        for key, value in udt.iteritems():
            result["udt.%s" % key] = value
        return result

    def _get_instances(self, klass, params=dict()):
        result = []
        tag = klass._TAG
        if tag is None:
            tag = klass.__name__.lower()
        root = self.get(self.get_uri(klass._URI), params=params)
        while params.get('start-index') is None: # Loop over all pages.
            for node in root.findall(tag):
                result.append(klass(self, uri=node.attrib['uri']))
            node = root.find('next-page')
            if node is None: break
            root = self.get(node.attrib['uri'], params=params)
        return result

    def get_batch(self, instances):
        "Get the content of a set of instances using the efficient batch call."
        if not instances:
            return []
        klass = instances[0].__class__
        root = ElementTree.Element(nsmap('ri:links'))
        for instance in instances:
            ElementTree.SubElement(root, 'link', dict(uri=instance.uri,
                                                      rel=klass._URI))
        uri = self.get_uri(klass._URI, 'batch/retrieve')
        data = self.tostring(ElementTree.ElementTree(root))
        root = self.post(uri, data)
        result = []
        for node in root.getchildren():
            instance = klass(self, uri=node.attrib['uri'])
            instance.root = node
            result.append(instance)
        return result

    def tostring(self, etree):
        "Return the ElementTree contents as a UTF-8 encoded XML string."
        outfile = StringIO()
        self.write(outfile, etree)
        return outfile.getvalue()

    def write(self, outfile, etree):
        "Write the ElementTree contents as UTF-8 encoded XML to the open file."
        etree.write(outfile, encoding='UTF-8')
