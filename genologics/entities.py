"""Python interface to GenoLogics LIMS via its REST API.

Entities and their descriptors for the LIMS interface.

Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
Copyright (C) 2012 Per Kraulis
"""

import re
import urlparse
import datetime
import time
from xml.etree import ElementTree
import logging

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
    smp='http://genologics.com/ri/sample',
    stg='http://genologics.com/ri/stage',
    stp='http://genologics.com/ri/step',
    udf='http://genologics.com/ri/userdefined',
    ver='http://genologics.com/ri/version',
    wkfcnf='http://genologics.com/ri/workflowconfiguration')

for prefix, uri in _NSMAP.iteritems():
    ElementTree._namespace_map[uri] = prefix

_NSPATTERN = re.compile(r'(\{)(.+?)(\})')

def nsmap(tag):
    "Convert from normal XML-ish namespace tag to ElementTree variant."
    parts = tag.split(':')
    if len(parts) != 2:
        raise ValueError("no namespace specifier in tag")
    return "{%s}%s" % (_NSMAP[parts[0]], parts[1])


class SampleHistory:
    """Class handling the history generation for a given sample/artifact
    AFAIK the only fields of the history that are read are proc.type and outart""" 

    def __init__(self, sample_name=None, output_artifact=None, input_artifact=None, lims=None, pro_per_art=None, test=False):
        self.processes_per_artifact=pro_per_art
        if lims:
            self.lims = lims
            if not (test):
                #this is now the default
                self.sample_name=sample_name
                self.alternate_history(output_artifact, input_artifact)
                self.art_map=None
            elif (sample_name) and pro_per_art:
                self.sample_name=sample_name
                self.make_sample_artifact_map()
                if output_artifact:
                    self.get_analyte_hist_sorted(output_artifact, input_artifact)
        else:
            logging.error("Tried to build History without lims")
            raise AttributeError("History cannot be computed without a valid lims object")


    def control(self):
        """this can be used to check the content of the object.
        """
        logging.info("SAMPLE NAME: {}".format(self.sample_name))
        logging.info("outart : {}".format(self.history_list[0]))
        #logging.info ("\nmap :")
        #for key, value in self.art_map.iteritems():
        #    logging.info(value[1]+"->"+value[0].id+"->"+key)
        logging.info ("\nHistory :\n\n")
        logging.info("Input\tProcess\tProcess info")
        for key, dict in self.history.iteritems():
            logging.info (key)
            for key2, dict2 in dict.iteritems():
                logging.info ("\t{}".format(key2))
                for key, value in dict2.iteritems():
                    logging.info ("\t\t{0}->{1}".format(key,(value if value is not None else "None")))
        logging.info ("\nHistory List")
        for art in self.history_list:
            logging.info (art)
        
    def make_sample_artifact_map(self):
        """samp_art_map: connects each output artifact for a specific sample to its 
        corresponding process and input artifact assuming, for a given sample,
        one input -> one process -> one output
        This function starts from the output, 
        and creates an entry like this : output -> (process, input)"""
        samp_art_map ={}
        if self.sample_name:
            artifacts = self.lims.get_artifacts(sample_name = self.sample_name, type = 'Analyte') 
            for one_art in artifacts:
                input_arts = one_art.input_artifact_list()
                for input_art in input_arts:
                    for samp in input_art.samples:
                        if samp.name == self.sample_name:
                            samp_art_map[one_art.id] = (one_art.parent_process, input_art.id)

        self.art_map=samp_art_map
    def alternate_history(self, out_art, in_art=None):
        """This is a try at another way to generate the history.
        This one iterates over Artifact.parent_process and Process.all_inputs()
        Then, it takes all the child processes for each input (because we want
        qc processes too) and puts everything in a dictionnary. 
        """
        history = {}
        hist_list = []
       #getting the list of all expected analytes.
        artifacts = self.lims.get_artifacts(sample_name = self.sample_name, type = 'Analyte')
        processes=[]
        inputs=[]
        if in_art:
            #If theres an input artifact given, I need to make a loop for this one, before treating it as an output
            starting_art=in_art
            inputs.append(in_art)
            history[in_art]={}
            for tempProcess in ( self.processes_per_artifact[in_art] if self.processes_per_artifact else self.lims.get_processes(inputartifactlimsid=in_art)):#If there is a loacl map, use it. else, query the lims.
                history[in_art][tempProcess.id] = {'date' : tempProcess.date_run,
                                                   'id' : tempProcess.id,
                                                   'outart' : (out_art if out_art in [ out.id for out in tempProcess.all_outputs()] else None ),
                                                   'inart' : in_art,
                                                   'type' : tempProcess.type.id,
                                                   'name' : tempProcess.type.name}
        else:
            starting_art=out_art
        #main iteration    
        #it is quite heavy on logging at info level
        not_done=True
        while not_done:
            logging.info ("looking for "+(starting_art))
            not_done=False 
            for o in artifacts:
                logging.info (o.id)
                if o.id == starting_art:
                    if o.parent_process is None:
                        #flow control : if there is no parent process, we can stop iterating, we're done.
                        not_done=False
                        break #breaks the for artifacts, we are done anyway.
                    else:
                        not_done=True #keep the loop running
                    logging.info ("found it")
                    processes.append(o.parent_process)
                    logging.info ("looking for inputs of "+o.parent_process.id)
                    for i in o.parent_process.all_inputs():
                        logging.info (i.id)
                        if i in artifacts:
                            history[i.id]={}
                            for tempProcess in (self.processes_per_artifact[i.id] if self.processes_per_artifact else self.lims.get_processes(inputartifactlimsid=i.id)):#If there is a loacl map, use it. else, query the lims.
                                history[i.id][tempProcess.id] = {'date' : tempProcess.date_run,
                                                               'id' : tempProcess.id,
                                                               'outart' : (o.id if tempProcess.id == o.parent_process.id else None),
                                                               'inart' : i.id,
                                                               'type' : tempProcess.type.id,
                                                               'name' : tempProcess.type.name}



                            logging.info ("found input "+i.id)
                            inputs.append(i.id) #this will be the sorted list of artifacts used to rebuild the history in order
                            # while increment
                            starting_art=i.id
                            
                            break #break the for allinputs, if we found the right one
                    break # breaks the for artifacts if we matched the current one
        self.history=history
        self.history_list=inputs 


    def get_analyte_hist_sorted(self, out_artifact, input_art = None):
         """Makes a history map of an artifac, using the samp_art_map 
         of the corresponding sample.
         The samp_art_map object is built up from analytes. This means that it will not 
         contain output-input info for processes wich have only files as output. 
         This is logical since the samp_art_map object is used for building up the ANALYTE 
         history of a sample. If you want to make the analyte history based on a 
         resultfile, that is; if you want to give a resultfile as out_artifact here, 
         and be given the historylist of analytes and processes for that file, you 
         will also have to give the input artifact for the process that generated 
         the resultfile for wich you want to get the history. In other words, if you 
         want to get the History of the folowing scenario:        
 
         History --- > Input_analyte -> Process -> Output_result_file
         
         then the arguments to this function should be:
         out_artifact = Output_result_file
         input_art = Input_analyte
 
         If you instead want the History of the folowing scenario:
         
         History --- > Input_analyte -> Process -> Output_analyte
 
         then you can skip the input_art argument and only set:
         out_artifact = Output_analyte 
         """
         history = {}
         hist_list = []
         if input_art:
            # In_art = Artifact(lims,id=input_art)
            # try:
            #     pro = In_art.parent_process.id
            # except:
            #     pro = None
             history, out_artifact = self._add_out_art_process_conection_list(input_art, 
                                                         out_artifact, history)
             hist_list.append(input_art)
         while self.art_map.has_key(out_artifact):
             pro, input_art = self.art_map[out_artifact]
             hist_list.append(input_art)
             history, out_artifact = self._add_out_art_process_conection_list(input_art, 
                                                        out_artifact, history)
         self.history=history
         self.history_list=hist_list
 
    def _add_out_art_process_conection_list(self, input_art, out_artifact, history = {}):
        """This function populates the history dict with process info per artifact.
        Maps an artifact to all the processes where its used as input and adds this 
        info to the history dict. Observe that the output artifact for the input 
        artifact in the historychain is given as input to this function. All 
        processes that the input artifact has been involved in, but that are not 
        part of the historychain get the outart set to None. This is very important."""
        # Use the local process map if we have one, else, query the lims 
        for process in self.processes_per_artifact[input_art] if self.processes_per_artifact else lims.get_processes(inputartifactlimsid = inart):
            #outputs = map(lambda a: (a.id), process.all_outputs())
            outputs = [a.id for a in process.all_outputs()] 
            outart = out_artifact if out_artifact in outputs else None 
            step_info = {'date' : process.date_run,
                         'id' : process.id,
                         'outart' : outart,
                         'inart' : input_art,
                         'type' : process.type.id,
                         'name' : process.type.name}
            if history.has_key(input_art):
                history[input_art][process.id] = step_info
            else:
                history[input_art] = {process.id : step_info}
        return history, input_art

class BaseDescriptor(object):
    "Abstract base descriptor for an instance attribute."

    def __get__(self, instance, cls):
        raise NotImplementedError


class TagDescriptor(BaseDescriptor):
    """Abstract base descriptor for an instance attribute
    represented by an XML element.
    """

    def __init__(self, tag):
        self.tag = tag


class StringDescriptor(TagDescriptor):
    """An instance attribute containing a string value
    represented by an XML element.
    """

    def __get__(self, instance, cls):
        instance.get()
        node = self.get_node(instance)
        if node is None:
            return None
        else:
            return node.text

    def __set__(self, instance, value):
        node = self.get_node(instance)
        if node is None:
            raise AttributeError("no element '%s' to set" % self.tag)
        else:
            node.text = value

    def get_node(self, instance):
        if self.tag:
            return instance.root.find(self.tag)
        else:
            return instance.root


class StringAttributeDescriptor(TagDescriptor):
    """An instance attribute containing a string value
    represented by an XML attribute.
    """

    def __get__(self, instance, cls):
        instance.get()
        return instance.root.attrib[self.tag]


class StringListDescriptor(TagDescriptor):
    """An instance attribute containing a list of strings
    represented by multiple XML elements.
    """

    def __get__(self, instance, cls):
        instance.get()
        result = []
        for node in instance.root.findall(self.tag):
            result.append(node.text)
        return result


class StringDictionaryDescriptor(TagDescriptor):
    """An instance attribute containing a dictionary of string key/values
    represented by a hierarchical XML element.
    """

    def __get__(self, instance, cls):
        instance.get()
        result = dict()
        node = instance.root.find(self.tag)
        if node is not None:
            for node2 in node.getchildren():
                result[node2.tag] = node2.text
        return result


class IntegerDescriptor(StringDescriptor):
    """An instance attribute containing an integer value
    represented by an XMl element.
    """

    def __get__(self, instance, cls):
        instance.get()
        node = self.get_node(instance)
        if node is None:
            return None
        else:
            return int(node.text)


class BooleanDescriptor(StringDescriptor):
    """An instance attribute containing a boolean value
    represented by an XMl element.
    """

    def __get__(self, instance, cls):
        instance.get()
        node = self.get_node(instance)
        if node is None:
            return None
        else:
            return node.text.lower() == 'true'


class UdfDictionary(object):
    "Dictionary-like container of UDFs, optionally within a UDT."

    def __init__(self, instance, udt=False):
        self.instance = instance
        self._udt = udt
        self._update_elems()
        self._prepare_lookup()

    def get_udt(self):
        if self._udt == True:
            return None
        else:
            return self._udt

    def set_udt(self, name):
        assert isinstance(name, basestring)
        if not self._udt:
            raise AttributeError('cannot set name for a UDF dictionary')
        self._udt = name
        elem = self.instance.root.find(nsmap('udf:type'))
        assert elem is not None
        elem.set('name', name)

    udt = property(get_udt, set_udt)

    def _update_elems(self):
        self._elems = []
        if self._udt:
            elem = self.instance.root.find(nsmap('udf:type'))
            if elem is not None:
                self._udt = elem.attrib['name']
                self._elems = elem.findall(nsmap('udf:field'))
        else:
            tag = nsmap('udf:field')
            for elem in self.instance.root.getchildren():
                if elem.tag == tag:
                    self._elems.append(elem)

    def _prepare_lookup(self):
        self._lookup = dict()
        for elem in self._elems:
            type = elem.attrib['type'].lower()
            value = elem.text
            if not value:
                value = None
            elif type == 'numeric':
                try:
                    value = int(value)
                except ValueError:
                    value = float(value)
            elif type == 'boolean':
                value = value == 'true'
            elif type == 'date':
                value = datetime.date(*time.strptime(value, "%Y-%m-%d")[:3])
            self._lookup[elem.attrib['name']] = value

    def __contains__(self,key):
        try:
            self._lookup[key]
        except KeyError:
            return False
        return True

    def __getitem__(self, key):
        return self._lookup[key]

    def __setitem__(self, key, value):
        self._lookup[key] = value
        for node in self._elems:
            if node.attrib['name'] != key: continue
            type = node.attrib['type'].lower()

            if value is None:
                pass
            elif type == 'string':
                if not isinstance(value, basestring):
                    raise TypeError('String UDF requires str or unicode value')
            elif type == 'str':
                if not isinstance(value, basestring):
                    raise TypeError('String UDF requires str or unicode value')
            elif type == 'text':
                if not isinstance(value, basestring):
                    raise TypeError('Text UDF requires str or unicode value')
            elif type == 'numeric':
                if not isinstance(value, (int, float)):
                    raise TypeError('Numeric UDF requires int or float value')
                value = str(value)
            elif type == 'boolean':
                if not isinstance(value, bool):
                    raise TypeError('Boolean UDF requires bool value')
                value = value and 'True' or 'False'
            elif type == 'date':
                if not isinstance(value, datetime.date): # Too restrictive?
                    raise TypeError('Date UDF requires datetime.date value')
                value = str(value)
            elif type == 'uri':
                if not isinstance(value, basestring):
                    raise TypeError('URI UDF requires str or punycode (unicode) value')
                value = str(value)
            else:
                raise NotImplemented("UDF type '%s'" % type)
            if not isinstance(value, unicode):
                value = unicode(value, 'UTF-8')
            node.text = value
            break
        else:                           # Create new entry; heuristics for type
            if isinstance(value, basestring):
                type = '\n' in value and 'Text' or 'String'
            elif isinstance(value, (int, float)):
                type = 'Numeric'
            elif isinstance(value, bool):
                type = 'Boolean'
                value = value and 'True' or 'False'
            elif isinstance(value, datetime.date):
                type = 'Date'
                value = str(value)
            else:
                raise NotImplementedError("Cannot handle value of type '%s'"
                                          " for UDF" % type(value))
            if self._udt:
                root = self.instance.root.find(nsmap('udf:type'))
            else:
                root = self.instance.root
            elem = ElementTree.SubElement(root,
                                          nsmap('udf:field'),
                                          type=type,
                                          name=key)
            if not isinstance(value, unicode):
                value = unicode(str(value), 'UTF-8')
            elem.text = value

    def __delitem__(self, key):
        del self._lookup[key]
        for node in self._elems:
            if node.attrib['name'] == key:
                self.instance.root.remove(node)
                break

    def items(self):
        return self._lookup.items()

    def clear(self):
        for elem in self._elems:
            self.instance.root.remove(elem)
        self._update_elems()


class UdfDictionaryDescriptor(BaseDescriptor):
    """An instance attribute containing a dictionary of UDF values
    represented by multiple XML elements.
    """

    _UDT = False

    def __get__(self, instance, cls):
    	instance.get()
   	self.value = UdfDictionary(instance, udt=self._UDT)
   	return self.value

class UdtDictionaryDescriptor(UdfDictionaryDescriptor):
    """An instance attribute containing a dictionary of UDF values
    in a UDT represented by multiple XML elements.
    """

    _UDT = True


class PlacementDictionaryDescriptor(TagDescriptor):
    """An instance attribute containing a dictionary of locations
    keys and artifact values represented by multiple XML elements.
    """

    def __get__(self, instance, cls):
    	instance.get()
      	self.value = dict()
      	for node in instance.root.findall(self.tag):
            key = node.find('value').text
            self.value[key] = Artifact(instance.lims,uri=node.attrib['uri'])
       	return self.value


class ExternalidListDescriptor(BaseDescriptor):
    """An instance attribute yielding a list of tuples (id, uri) for
    external identifiers represented by multiple XML elements.
    """

    def __get__(self, instance, cls):
        instance.get()
        result = []
        for node in instance.root.findall(nsmap('ri:externalid')):
            result.append((node.attrib.get('id'), node.attrib.get('uri')))
        return result


class EntityDescriptor(TagDescriptor):
    "An instance attribute referencing another entity instance."

    def __init__(self, tag, klass):
        super(EntityDescriptor, self).__init__(tag)
        self.klass = klass

    def __get__(self, instance, cls):
        instance.get()
        node = instance.root.find(self.tag)
        if node is None:
            return None
        else:
            return self.klass(instance.lims, uri=node.attrib['uri'])


class EntityListDescriptor(EntityDescriptor):
    """An instance attribute yielding a list of entity instances
    represented by multiple XML elements.
    """

    def __get__(self, instance, cls):
        instance.get()
        result = []
        for node in instance.root.findall(self.tag):
            result.append(self.klass(instance.lims, uri=node.attrib['uri']))
        return result


class DimensionDescriptor(TagDescriptor):
    """An instance attribute containing a dictionary specifying
    the properties of a dimension of a container type.
    """

    def __get__(self, instance, cls):
        instance.get()
        node = instance.root.find(self.tag)
        return dict(is_alpha = node.find('is-alpha').text.lower() == 'true',
                    offset = int(node.find('offset').text),
                    size = int(node.find('size').text))


class LocationDescriptor(TagDescriptor):
    """An instance attribute containing a tuple (container, value)
    specifying the location of an analyte in a container.
    """

    def __get__(self, instance, cls):
        instance.get()
        node = instance.root.find(self.tag)
        uri = node.find('container').attrib['uri']
        return Container(instance.lims, uri=uri), node.find('value').text

class ReagentLabelList(BaseDescriptor):
    """An instance attribute yielding a list of reagent labels"""
    def __get__(self, instance, cls):
	instance.get()
	self.value = []
	for node in instance.root.findall('reagent-label'):
	    try:
	    	self.value.append(node.attrib['name']) 
	    except:
		pass
	return self.value

class InputOutputMapList(BaseDescriptor):
    """An instance attribute yielding a list of tuples (input, output)
    where each item is a dictionary, representing the input/output
    maps of a Process instance.
    """

    def __get__(self, instance, cls):
        instance.get()
        self.value = []
        for node in instance.root.findall('input-output-map'):
            input = self.get_dict(instance.lims, node.find('input'))
            output = self.get_dict(instance.lims, node.find('output'))
            self.value.append((input, output))
        return self.value

    def get_dict(self, lims, node):
        if node is None: return None
        result = dict()
        for key in ['limsid', 'output-type', 'output-generation-type']:
            try:
                result[key] = node.attrib[key]
            except KeyError:
                pass
            for uri in ['uri', 'post-process-uri']:
                try:
                    result[uri] = Artifact(lims, uri=node.attrib[uri])
                except KeyError:
                    pass
        node = node.find('parent-process')
        if node is not None:
            result['parent-process'] = Process(lims, node.attrib['uri'])
        return result


class Entity(object):
    "Base class for the entities in the LIMS database."

    _TAG = None
    _URI = None

    def __new__(cls, lims, uri=None, id=None):
        assert uri or id
        if not uri:
            uri = lims.get_uri(cls._URI, id)
        try:
            return lims.cache[uri]
        except KeyError:
            return object.__new__(cls)

    def __init__(self, lims, uri=None, id=None):
        assert uri or id
        if hasattr(self, 'lims'): return
        if not uri:
            uri = lims.get_uri(self._URI, id)
        lims.cache[uri] = self
        self.lims = lims
        self._uri = uri
        self.root = None

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.id)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.uri)

    @property
    def uri(self):
        return self._uri

    @property
    def id(self):
        "Return the LIMS id; obtained from the URI."
        parts = urlparse.urlsplit(self.uri)
        return parts.path.split('/')[-1]

    def get(self, force=False):
        "Get the XML data for this instance."
        if not force and self.root is not None: return
        self.root = self.lims.get(self.uri)

    def put(self):
        "Save this instance by doing PUT of its serialized XML."
        data = self.lims.tostring(ElementTree.ElementTree(self.root))
        self.lims.put(self.uri, data)


class Lab(Entity):
    "Lab; container of researchers."

    _URI = 'labs'

    name             = StringDescriptor('name')
    billing_address  = StringDictionaryDescriptor('billing-address')
    shipping_address = StringDictionaryDescriptor('shipping-address')
    udf              = UdfDictionaryDescriptor()
    udt              = UdtDictionaryDescriptor()
    externalids      = ExternalidListDescriptor()
    website          = StringDescriptor('website')


class Researcher(Entity):
    "Person; client scientist or lab personnel. Associated with a lab."

    _URI = 'researchers'

    first_name  = StringDescriptor('first-name')
    last_name   = StringDescriptor('last-name')
    phone       = StringDescriptor('phone')
    fax         = StringDescriptor('fax')
    email       = StringDescriptor('email')
    initials    = StringDescriptor('initials')
    lab         = EntityDescriptor('lab', Lab)
    udf         = UdfDictionaryDescriptor()
    udt         = UdtDictionaryDescriptor()
    externalids = ExternalidListDescriptor()
    # credentials XXX

    @property
    def name(self):
        return u"%s %s" % (self.first_name, self.last_name)

class Reagent_label(Entity):
    reagent_label = StringDescriptor('reagent-label')

class Note(Entity):
    "Note attached to a project or a sample."

    content = StringDescriptor(None)    # root element


class File(Entity):
    "File attached to a project or a sample."

    attached_to       = StringDescriptor('attached-to')
    content_location  = StringDescriptor('content-location')
    original_location = StringDescriptor('original-location')
    is_published      = BooleanDescriptor('is-published')


class Project(Entity):
    "Project concerning a number of samples; associated with a researcher."

    _URI = 'projects'

    name          = StringDescriptor('name')
    open_date     = StringDescriptor('open-date')
    close_date    = StringDescriptor('close-date')
    invoice_date  = StringDescriptor('invoice-date')
    researcher    = EntityDescriptor('researcher', Researcher)
    udf           = UdfDictionaryDescriptor()
    udt           = UdtDictionaryDescriptor()
    files         = EntityListDescriptor(nsmap('file:file'), File)
    externalids   = ExternalidListDescriptor()
    # permissions XXX


class Sample(Entity):
    "Customer's sample to be analyzed; associated with a project."

    _URI = 'samples'

    name           = StringDescriptor('name')
    date_received  = StringDescriptor('date-received')
    date_completed = StringDescriptor('date-completed')
    project        = EntityDescriptor('project', Project)
    submitter      = EntityDescriptor('submitter', Researcher)
    # artifact: defined below
    udf            = UdfDictionaryDescriptor()
    udt            = UdtDictionaryDescriptor()
    notes          = EntityListDescriptor('note', Note)
    files          = EntityListDescriptor(nsmap('file:file'), File)
    externalids    = ExternalidListDescriptor()
    # biosource XXX


class Containertype(Entity):
    "Type of container for analyte artifacts."

    _TAG = 'container-type'
    _URI = 'containertypes'

    name              = StringAttributeDescriptor('name')
    calibrant_wells   = StringListDescriptor('calibrant-well')
    unavailable_wells = StringListDescriptor('unavailable-well')
    x_dimension       = DimensionDescriptor('x-dimension')
    y_dimension       = DimensionDescriptor('y-dimension')


class Container(Entity):
    "Container for analyte artifacts."

    _URI = 'containers'

    name           = StringDescriptor('name')
    type           = EntityDescriptor('type', Containertype)
    occupied_wells = IntegerDescriptor('occupied-wells')
    placements     = PlacementDictionaryDescriptor('placement')
    udf            = UdfDictionaryDescriptor()
    udt            = UdtDictionaryDescriptor()
    state          = StringDescriptor('state')

    def get_placements(self):
        """Get the dictionary of locations and artifacts
        using the more efficient batch call."""
        result = self.placements.copy()
        self.lims.get_batch(result.values())
        return result


class Processtype(Entity):

    _TAG = 'process-type'
    _URI = 'processtypes'

    name              = StringAttributeDescriptor('name')
    # XXX

class Udfconfig(Entity):
    "Instance of field type (cnf namespace)."
    _URI = 'configuration/udfs'

    name = StringDescriptor('name')
    attach_to_name = StringDescriptor('attach-to-name')
    attach_to_category = StringDescriptor('attach-to-category')


class Process(Entity):
    "Process (instance of Processtype) executed producing ouputs from inputs."

    _URI = 'processes'

    type          = EntityDescriptor('type', Processtype)
    date_run      = StringDescriptor('date-run')
    technician    = EntityDescriptor('technician', Researcher)
    protocol_name = StringDescriptor('protocol-name')
    input_output_maps = InputOutputMapList()
    udf            = UdfDictionaryDescriptor()
    udt            = UdtDictionaryDescriptor()
    files          = EntityListDescriptor(nsmap('file:file'), File)
    # instrument XXX
    # process_parameters XXX

    def outputs_per_input(self, inart, ResultFile = False, SharedResultFile = False,  Analyte = False):
        """Getting all the output artifacts related to a particual input artifact"""
        
        inouts = filter(lambda io: io[0]['limsid'] == inart, self.input_output_maps)
        if ResultFile:
            inouts = filter(lambda io: io[1]['output-type'] == 'ResultFile', inouts)
        elif SharedResultFile:
            inouts = filter(lambda io: io[1]['output-type'] == 'SharedResultFile', inouts)
        elif Analyte:
            inouts = filter(lambda io: io[1]['output-type'] == 'Analyte', inouts)
        outs = map(lambda io: io[1]['uri'], inouts)
        return outs

    def input_per_sample(self, sample):
        """gettiung all the input artifacts dereved from the specifyed sample"""
        ins_all = self.all_inputs()
        ins = []
        for inp in ins_all:
            for samp in inp.samples:
                if samp.name == sample and inp not in ins:
                    ins.append(inp)
        return ins
    
    def all_inputs(self,unique=True):
        """Retrieving all input artifacts from input_output_maps
        if unique is true, no duplicates are returned.
        """
        #if the process has no input, that is not standard and we want to know about it
        try:
            ids = [io[0]['limsid'] for io in self.input_output_maps]
        except TypeError:
            logging.error("Process ",self," has no input artifacts")
            raise TypeError
        if unique:
            ids = list(frozenset(ids))
        return [Artifact(self.lims,id=id) for id in ids if id is not None]

    def all_outputs(self,unique=True):
        """Retrieving all output artifacts from input_output_maps
        if unique is true, no duplicates are returned.
        """
        #Given how ids is structured, io[1] might be None : some process don't have an output.
        ids = [io[1]['limsid'] for io in self.input_output_maps if io[1] is not None]
        if unique:
            ids = list(frozenset(ids))
        return  [Artifact(self.lims,id=id) for id in ids if id is not None]

    def shared_result_files(self):
        """Retreve all resultfiles of output-generation-type PerAllInputs."""
        artifacts = self.all_outputs(unique=True)
        return filter(lambda a: a.output_type == 'SharedResultFile', artifacts)

    def result_files(self):
        """Retreve all resultfiles of output-generation-type perInput."""
        artifacts = self.all_outputs(unique=True)
        return filter(lambda a: a.output_type == 'ResultFile', artifacts)

    def analytes(self):
        """Retreving the output Analytes of the process, if existing. 
        If the process is not producing any output analytes, the input 
        analytes are returned. Input/Output is returned as a information string.
        Makes aggregate processes and normal processes look the same."""
        info = 'Output'
        artifacts = self.all_outputs(unique=True)
        analytes = filter(lambda a: a.type == 'Analyte', artifacts)
        if len(analytes) == 0:
            artifacts = self.all_inputs(unique=True)
            analytes = filter(lambda a: a.type == 'Analyte', artifacts)
            info = 'Input'
        return analytes, info

    def parent_processes(self):
        """Retrieving all parent processes through the input artifacts"""
        return map(lambda i_a: i_a.parent_process, self.all_inputs(unique=True))

    def output_containers(self):
        """Retrieve all unique output containers"""
        cs = []
        for o_a in self.all_outputs(unique=True):
            if o_a.container:
                cs.append(o_a.container)
        return list(frozenset(cs))

class Artifact(Entity):
    "Any process input or output; analyte or file."

    _URI = 'artifacts'

    name           = StringDescriptor('name')
    type           = StringDescriptor('type')
    output_type    = StringDescriptor('output-type')
    parent_process = EntityDescriptor('parent-process', Process)
    volume         = StringDescriptor('volume')
    concentration  = StringDescriptor('concentration')
    qc_flag        = StringDescriptor('qc-flag')
    location       = LocationDescriptor('location')
    working_flag   = BooleanDescriptor('working-flag')
    samples        = EntityListDescriptor('sample', Sample)
    udf            = UdfDictionaryDescriptor()
    files          = EntityListDescriptor(nsmap('file:file'), File)
    reagent_labels = ReagentLabelList()
    # artifact_flags XXX
    # artifact_groups XXX

    def input_artifact_list(self):
        """Returns the input artifact ids of the parrent process."""
        input_artifact_list=[]
        try:
            for tuple in self.parent_process.input_output_maps:
                if tuple[1]['limsid'] == self.id:
                    input_artifact_list.append(tuple[0]['uri'])#['limsid'])
        except:
            pass
        return input_artifact_list

    def get_state(self):
        "Parse out the state value from the URI."
        parts = urlparse.urlparse(self.uri)
        params = urlparse.parse_qs(parts.query)
        try:
            return params['state'][0]
        except (KeyError, IndexError):
            return None

    @property
    def container(self):
        "The container where the artifact is located, or None"
        try:
            return self.location[0]
        except:
            return None

    # XXX set_state ?
    state = property(get_state)


Sample.artifact = EntityDescriptor('artifact', Artifact)


