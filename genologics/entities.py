"""Python interface to GenoLogics LIMS via its REST API.

Entities and their descriptors for the LIMS interface.

Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
Copyright (C) 2012 Per Kraulis
"""

from genologics.constants import nsmap
from genologics.descriptors import StringDescriptor, StringDictionaryDescriptor, UdfDictionaryDescriptor, \
    UdtDictionaryDescriptor, ExternalidListDescriptor, EntityDescriptor, BooleanDescriptor, EntityListDescriptor, \
    StringAttributeDescriptor, StringListDescriptor, DimensionDescriptor, IntegerDescriptor, \
    PlacementDictionaryDescriptor, InputOutputMapList, LocationDescriptor, ReagentLabelList, IntegerAttributeDescriptor, \
    AttributeListDescriptor

try:
    from urllib.parse import urlsplit, urlparse, parse_qs, urlunparse
except ImportError:
    from urlparse import urlsplit, urlparse, parse_qs, urlunparse

from xml.etree import ElementTree

import logging

logger = logging.getLogger(__name__)


class SampleHistory:
    """Class handling the history generation for a given sample/artifact
    AFAIK the only fields of the history that are read are proc.type and outart"""

    def __init__(self, sample_name=None, output_artifact=None, input_artifact=None, lims=None, pro_per_art=None,
                 test=False):
        self.processes_per_artifact = pro_per_art
        if lims:
            self.lims = lims
            if not (test):
                # this is now the default
                self.sample_name = sample_name
                self.alternate_history(output_artifact, input_artifact)
                self.art_map = None
            elif (sample_name) and pro_per_art:
                self.sample_name = sample_name
                self.make_sample_artifact_map()
                if output_artifact:
                    self.get_analyte_hist_sorted(output_artifact, input_artifact)
        else:
            logger.error("Tried to build History without lims")
            raise AttributeError("History cannot be computed without a valid lims object")

    def control(self):
        """this can be used to check the content of the object.
        """
        logger.info("SAMPLE NAME: {}".format(self.sample_name))
        logger.info("outart : {}".format(self.history_list[0]))
        # logger.info ("\nmap :")
        # for key, value in self.art_map.iteritems():
        #    logger.info(value[1]+"->"+value[0].id+"->"+key)
        logger.info("\nHistory :\n\n")
        logger.info("Input\tProcess\tProcess info")
        for key, dict in self.history.items():
            logger.info(key)
            for key2, dict2 in dict.items():
                logger.info("\t{}".format(key2))
                for key, value in dict2.items():
                    logger.info("\t\t{0}->{1}".format(key, (value if value is not None else "None")))
        logger.info("\nHistory List")
        for art in self.history_list:
            logger.info(art)

    def make_sample_artifact_map(self):
        """samp_art_map: connects each output artifact for a specific sample to its
        corresponding process and input artifact assuming, for a given sample,
        one input -> one process -> one output
        This function starts from the output,
        and creates an entry like this : output -> (process, input)"""
        samp_art_map = {}
        if self.sample_name:
            artifacts = self.lims.get_artifacts(sample_name=self.sample_name, type='Analyte', resolve=False)
            for one_art in artifacts:
                input_arts = one_art.input_artifact_list()
                for input_art in input_arts:
                    for samp in input_art.samples:
                        if samp.name == self.sample_name:
                            samp_art_map[one_art.id] = (one_art.parent_process, input_art.id)

        self.art_map = samp_art_map

    def alternate_history(self, out_art, in_art=None):
        """This is a try at another way to generate the history.
        This one iterates over Artifact.parent_process and Process.all_inputs()
        Then, it takes all the child processes for each input (because we want
        qc processes too) and puts everything in a dictionnary.
        """
        history = {}
        hist_list = []
        # getting the list of all expected analytes.
        artifacts = self.lims.get_artifacts(sample_name=self.sample_name, type='Analyte', resolve=False)
        processes = []
        inputs = []
        if in_art:
            # If theres an input artifact given, I need to make a loop for this one, before treating it as an output
            starting_art = in_art
            inputs.append(in_art)
            history[in_art] = {}
            # If there is a loacl map, use it. else, query the lims.
            if self.processes_per_artifact and in_art in self.processes_per_artifact:
                valid_pcs = self.processes_per_artifact[in_art]
            else:
                valid_pcs = self.lims.get_processes(inputartifactlimsid=in_art)

            for tempProcess in valid_pcs:
                history[in_art][tempProcess.id] = {'date': tempProcess.date_run,
                                                   'id': tempProcess.id,
                                                   'outart': (out_art if out_art in [out.id for out in tempProcess.all_outputs()] else None),
                                                   'inart': in_art,
                                                   'type': tempProcess.type.id,
                                                   'name': tempProcess.type.name}
        else:
            starting_art = out_art
        # main iteration
        # it is quite heavy on logger at info level
        not_done = True
        while not_done:
            logger.info("looking for " + (starting_art))
            not_done = False
            for o in artifacts:
                logger.info(o.id)
                if o.id == starting_art:
                    if o.parent_process is None:
                        # flow control : if there is no parent process, we can stop iterating, we're done.
                        not_done = False
                        break  # breaks the for artifacts, we are done anyway.
                    else:
                        not_done = True  # keep the loop running
                    logger.info("found it")
                    processes.append(o.parent_process)
                    logger.info("looking for inputs of " + o.parent_process.id)
                    for i in o.parent_process.all_inputs():
                        logger.info(i.id)
                        if i in artifacts:
                            history[i.id] = {}
                            for tempProcess in (self.processes_per_artifact[i.id] if self.processes_per_artifact else self.lims.get_processes(inputartifactlimsid=i.id)):  # If there is a loacl map, use it. else, query the lims.
                                history[i.id][tempProcess.id] = {'date': tempProcess.date_run,
                                                                 'id': tempProcess.id,
                                                                 'outart': (
                                                                 o.id if tempProcess.id == o.parent_process.id else None),
                                                                 'inart': i.id,
                                                                 'type': tempProcess.type.id,
                                                                 'name': tempProcess.type.name}

                            logger.info("found input " + i.id)
                            inputs.append(
                                i.id)  # this will be the sorted list of artifacts used to rebuild the history in order
                            # while increment
                            starting_art = i.id

                            break  # break the for allinputs, if we found the right one
                    break  # breaks the for artifacts if we matched the current one
        self.history = history
        self.history_list = inputs

    def get_analyte_hist_sorted(self, out_artifact, input_art=None):
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
            history, out_artifact = self._add_out_art_process_conection_list(input_art, out_artifact, history)
            hist_list.append(input_art)
        while out_artifact in self.art_map:
            pro, input_art = self.art_map[out_artifact]
            hist_list.append(input_art)
            history, out_artifact = self._add_out_art_process_conection_list(input_art, out_artifact, history)
        self.history = history
        self.history_list = hist_list

    def _add_out_art_process_conection_list(self, input_art, out_artifact, history={}):
        """This function populates the history dict with process info per artifact.
        Maps an artifact to all the processes where its used as input and adds this
        info to the history dict. Observe that the output artifact for the input
        artifact in the historychain is given as input to this function. All
        processes that the input artifact has been involved in, but that are not
        part of the historychain get the outart set to None. This is very important."""
        # Use the local process map if we have one, else, query the lims
        for process in self.processes_per_artifact[input_art] if self.processes_per_artifact else lims.get_processes(
                inputartifactlimsid=input_art):
            # outputs = map(lambda a: (a.id), process.all_outputs())
            outputs = [a.id for a in process.all_outputs()]
            outart = out_artifact if out_artifact in outputs else None
            step_info = {'date': process.date_run,
                         'id': process.id,
                         'outart': outart,
                         'inart': input_art,
                         'type': process.type.id,
                         'name': process.type.name}
            if input_art in history:
                history[input_art][process.id] = step_info
            else:
                history[input_art] = {process.id: step_info}
        return history, input_art


class Entity(object):
    "Base class for the entities in the LIMS database."

    _TAG = None
    _URI = None
    _PREFIX = None

    def __new__(cls, lims, uri=None, id=None, _create_new=False):
        if not uri:
            if id:
                uri = lims.get_uri(cls._URI, id)
            elif _create_new:
                # create the Object without id or uri
                pass
            else:
                raise ValueError("Entity uri and id can't be both None")
        try:
            return lims.cache[uri]
        except KeyError:
            return object.__new__(cls)

    def __init__(self, lims, uri=None, id=None, _create_new=False):
        assert uri or id or _create_new
        if not _create_new:
            if hasattr(self, 'lims'): return
            if not uri:
                uri = lims.get_uri(self._URI, id)
            lims.cache[uri] = self
            self.root = None
        self.lims = lims
        self._uri = uri
        self.root = None

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.id)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.uri)

    @property
    def uri(self):
        try:
            return self._uri
        except:
            return self._URI

    @property
    def id(self):
        "Return the LIMS id; obtained from the URI."
        parts = urlsplit(self.uri)
        return parts.path.split('/')[-1]

    def get(self, force=False):
        "Get the XML data for this instance."
        if not force and self.root is not None: return
        self.root = self.lims.get(self.uri)

    def put(self):
        "Save this instance by doing PUT of its serialized XML."
        data = self.lims.tostring(ElementTree.ElementTree(self.root))
        self.lims.put(self.uri, data)

    def post(self):
        "Save this instance with POST"
        data = self.lims.tostring(ElementTree.ElementTree(self.root))
        self.lims.post(self.uri, data)

    @classmethod
    def _create(cls, lims, creation_tag=None, **kwargs):
        """Create an instance from attributes and return it"""
        instance = cls(lims, _create_new=True)
        if creation_tag:
            instance.root = ElementTree.Element(nsmap(cls._PREFIX + ':' + creation_tag))
        elif cls._TAG:
            instance.root = ElementTree.Element(nsmap(cls._PREFIX + ':' + cls._TAG))
        else:
            instance.root = ElementTree.Element(nsmap(cls._PREFIX + ':' + cls.__name__.lower()))
        for attribute in kwargs:
            if hasattr(instance, attribute):
                setattr(instance, attribute, kwargs.get(attribute))
            else:
                raise TypeError("%s create: got an unexpected keyword argument '%s'" % (cls.__name__, attribute))

        return instance

    @classmethod
    def create(cls, lims, creation_tag=None, **kwargs):
        """Create an instance from attributes then post it to the LIMS"""
        instance = cls._create(lims, creation_tag=None, **kwargs)
        data = lims.tostring(ElementTree.ElementTree(instance.root))
        instance.root = lims.post(uri=lims.get_uri(cls._URI), data=data)
        instance._uri = instance.root.attrib['uri']
        return instance


class Lab(Entity):
    "Lab; container of researchers."

    _URI = 'labs'
    _PREFIX = 'lab'

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
    _PREFIX = 'res'

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
        return "%s %s" % (self.first_name, self.last_name)


class Reagent_label(Entity):
    """Reagent label element"""
    reagent_label = StringDescriptor('reagent-label')


class Note(Entity):
    "Note attached to a project or a sample."

    content = StringDescriptor(None)  # root element


class File(Entity):
    "File attached to a project or a sample."

    attached_to       = StringDescriptor('attached-to')
    content_location  = StringDescriptor('content-location')
    original_location = StringDescriptor('original-location')
    is_published      = BooleanDescriptor('is-published')


class Project(Entity):
    "Project concerning a number of samples; associated with a researcher."

    _URI = 'projects'
    _PREFIX = 'prj'

    name         = StringDescriptor('name')
    open_date    = StringDescriptor('open-date')
    close_date   = StringDescriptor('close-date')
    invoice_date = StringDescriptor('invoice-date')
    researcher   = EntityDescriptor('researcher', Researcher)
    udf          = UdfDictionaryDescriptor()
    udt          = UdtDictionaryDescriptor()
    files        = EntityListDescriptor(nsmap('file:file'), File)
    externalids  = ExternalidListDescriptor()
    # permissions XXX


class Sample(Entity):
    "Customer's sample to be analyzed; associated with a project."

    _URI = 'samples'
    _PREFIX = 'smp'

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


    @classmethod
    def create(cls, lims, container, position, **kwargs):
        """Create an instance of Sample from attributes then post it to the LIMS"""
        if not isinstance(container, Container):
            raise TypeError('%s is not of type Container'%container)
        instance = super(Sample, cls)._create(lims, creation_tag='samplecreation', **kwargs)

        location = ElementTree.SubElement(instance.root, 'location')
        ElementTree.SubElement(location, 'container', dict(uri=container.uri))
        position_element = ElementTree.SubElement(location, 'value')
        position_element.text = position
        data = lims.tostring(ElementTree.ElementTree(instance.root))
        instance.root = lims.post(uri=lims.get_uri(cls._URI), data=data)
        instance._uri = instance.root.attrib['uri']
        return instance


class Containertype(Entity):
    "Type of container for analyte artifacts."

    _TAG = 'container-type'
    _URI = 'containertypes'
    _PREFIX = 'ctp'

    name              = StringAttributeDescriptor('name')
    calibrant_wells   = StringListDescriptor('calibrant-well')
    unavailable_wells = StringListDescriptor('unavailable-well')
    x_dimension       = DimensionDescriptor('x-dimension')
    y_dimension       = DimensionDescriptor('y-dimension')


class Container(Entity):
    "Container for analyte artifacts."

    _URI = 'containers'
    _PREFIX = 'con'

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
        self.lims.get_batch(list(result.values()))
        return result


class Processtype(Entity):
    _TAG = 'process-type'
    _URI = 'processtypes'
    _PREFIX = 'ptp'

    name = StringAttributeDescriptor('name')
    # XXX


class Udfconfig(Entity):
    "Instance of field type (cnf namespace)."
    _URI = 'configuration/udfs'

    name                          = StringDescriptor('name')
    attach_to_name                = StringDescriptor('attach-to-name')
    attach_to_category            = StringDescriptor('attach-to-category')
    show_in_lablink               = BooleanDescriptor('show-in-lablink')
    allow_non_preset_values       = BooleanDescriptor('allow-non-preset-values')
    first_preset_is_default_value = BooleanDescriptor('first-preset-is-default-value')
    show_in_tables                = BooleanDescriptor('show-in-tables')
    is_editable                   = BooleanDescriptor('is-editable')
    is_deviation                  = BooleanDescriptor('is-deviation') 
    is_controlled_vocabulary      = BooleanDescriptor('is-controlled-vocabulary')
    presets                       = StringListDescriptor('preset') 



class Process(Entity):
    "Process (instance of Processtype) executed producing ouputs from inputs."

    _URI = 'processes'
    _PREFIX = 'prc'

    type              = EntityDescriptor('type', Processtype)
    date_run          = StringDescriptor('date-run')
    technician        = EntityDescriptor('technician', Researcher)
    protocol_name     = StringDescriptor('protocol-name')
    input_output_maps = InputOutputMapList()
    udf               = UdfDictionaryDescriptor()
    udt               = UdtDictionaryDescriptor()
    files             = EntityListDescriptor(nsmap('file:file'), File)
    process_parameter = StringDescriptor('process-parameter')

    # instrument XXX
    # process_parameters XXX

    def outputs_per_input(self, inart, ResultFile=False, SharedResultFile=False, Analyte=False):
        """Getting all the output artifacts related to a particual input artifact"""

        inouts = [io for io in self.input_output_maps if io[0]['limsid'] == inart]
        if ResultFile:
            inouts = [io for io in inouts if io[1]['output-type'] == 'ResultFile']
        elif SharedResultFile:
            inouts = [io for io in inouts if io[1]['output-type'] == 'SharedResultFile']
        elif Analyte:
            inouts = [io for io in inouts if io[1]['output-type'] == 'Analyte']
        outs = [io[1]['uri'] for io in inouts]
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

    def all_inputs(self, unique=True, resolve=False):
        """Retrieving all input artifacts from input_output_maps
        if unique is true, no duplicates are returned.
        """
        # if the process has no input, that is not standard and we want to know about it
        try:
            ids = [io[0]['limsid'] for io in self.input_output_maps]
        except TypeError:
            logger.error("Process ", self, " has no input artifacts")
            raise TypeError
        if unique:
            ids = list(frozenset(ids))
        if resolve:
            return self.lims.get_batch([Artifact(self.lims, id=id) for id in ids if id is not None])
        else:
            return [Artifact(self.lims, id=id) for id in ids if id is not None]

    def all_outputs(self, unique=True, resolve=False):
        """Retrieving all output artifacts from input_output_maps
        if unique is true, no duplicates are returned.
        """
        # Given how ids is structured, io[1] might be None : some process don't have an output.
        ids = [io[1]['limsid'] for io in self.input_output_maps if io[1] is not None]
        if unique:
            ids = list(frozenset(ids))
        if resolve:
            return self.lims.get_batch([Artifact(self.lims, id=id) for id in ids if id is not None])
        else:
            return [Artifact(self.lims, id=id) for id in ids if id is not None]

    def shared_result_files(self):
        """Retreve all resultfiles of output-generation-type PerAllInputs."""
        artifacts = self.all_outputs(unique=True)
        return [a for a in artifacts if a.output_type == 'SharedResultFile']

    def result_files(self):
        """Retreve all resultfiles of output-generation-type perInput."""
        artifacts = self.all_outputs(unique=True)
        return [a for a in artifacts if a.output_type == 'ResultFile']

    def analytes(self):
        """Retreving the output Analytes of the process, if existing. 
        If the process is not producing any output analytes, the input 
        analytes are returned. Input/Output is returned as a information string.
        Makes aggregate processes and normal processes look the same."""
        info = 'Output'
        artifacts = self.all_outputs(unique=True)
        analytes = [a for a in artifacts if a.type == 'Analyte']
        if len(analytes) == 0:
            artifacts = self.all_inputs(unique=True)
            analytes = [a for a in artifacts if a.type == 'Analyte']
            info = 'Input'
        return analytes, info

    def parent_processes(self):
        """Retrieving all parent processes through the input artifacts"""
        return [i_a.parent_process for i_a in self.all_inputs(unique=True)]

    def output_containers(self):
        """Retrieve all unique output containers"""
        cs = []
        for o_a in self.all_outputs(unique=True):
            if o_a.container:
                cs.append(o_a.container)
        return list(frozenset(cs))

    @property
    def step(self):
        """Retrive the Step coresponding to this process. They share the same id"""
        return Step(self.lims, id=self.id)


class Artifact(Entity):
    "Any process input or output; analyte or file."

    _URI = 'artifacts'
    _PREFIX = 'art'

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
        input_artifact_list = []
        try:
            for tuple in self.parent_process.input_output_maps:
                if tuple[1]['limsid'] == self.id:
                    input_artifact_list.append(tuple[0]['uri'])  # ['limsid'])
        except:
            pass
        return input_artifact_list

    def get_state(self):
        "Parse out the state value from the URI."
        parts = urlparse(self.uri)
        params = parse_qs(parts.query)
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

    def stateless(self):
        "returns the artefact independently of it's state"
        parts = urlparse(self.uri)
        if 'state' in parts[4]:
            stateless_uri = urlunparse([parts[0], parts[1], parts[2], parts[3], '', ''])
            return Artifact(self.lims, uri=stateless_uri)
        else:
            return self

    # XXX set_state ?
    state = property(get_state)
    stateless = property(stateless)

    def _get_workflow_stages_and_statuses(self):
        self.get()
        result = []
        rootnode = self.root.find('workflow-stages')
        for node in rootnode.findall('workflow-stage'):
            result.append((Stage(self.lims, uri=node.attrib['uri']), node.attrib['status'], node.attrib['name']))
        return result

    workflow_stages_and_statuses = property(_get_workflow_stages_and_statuses)


class StepPlacements(Entity):
    """Placements from within a step. Supports POST"""
    _placementslist = None

    # [[A,(C,'A:1')][A,(C,'A:2')]] where A is an Artifact and C a Container
    def get_placement_list(self):
        if not self._placementslist:
            # Only fetch the data once.
            self.get()
            self._placementslist = []
            for node in self.root.find('output-placements').findall('output-placement'):
                input = Artifact(self.lims, uri=node.attrib['uri'])
                location = (None, None)
                if node.find('location'):
                    location = (
                        Container(self.lims, uri=node.find('location').find('container').attrib['uri']),
                        node.find('location').find('value').text
                    )
                self._placementslist.append([input, location])
        return self._placementslist

    def set_placement_list(self, value):
        containers = set()
        self.get_placement_list()
        for node in self.root.find('output-placements').findall('output-placement'):
            for pair in value:
                art = pair[0]
                if art.uri == node.attrib['uri']:
                    location = pair[1]
                    workset = location[0]
                    well = location[1]
                    if workset and location:
                        containers.add(workset)
                        if node.find('location') is not None:
                            cont_el = node.find('location').find('container')
                            cont_el.attrib['uri'] = workset.uri
                            cont_el.attrib['limsid'] = workset.id
                            value_el = node.find('location').find('value')
                            value_el.text = well
                        else:
                            loc_el = ElementTree.SubElement(node, 'location')
                            cont_el = ElementTree.SubElement(loc_el, 'container',
                                                             {'uri': workset.uri, 'limsid': workset.id})
                            well_el = ElementTree.SubElement(loc_el, 'value')
                            well_el.text = well  # not supported in the constructor
        # Handle selected containers
        sc = self.root.find("selected-containers")
        sc.clear()
        for cont in containers:
            ElementTree.SubElement(sc, 'container', uri=cont.uri)
        self._placementslist = value

    placement_list = property(get_placement_list, set_placement_list)

    _selected_containers = None

    def get_selected_containers(self):
        _selected_containers = []
        if not _selected_containers:
            self.get()
            for node in self.root.find('selected-containers').findall('container'):
                _selected_containers.append(Container(self.lims, uri=node.attrib['uri']))

        return _selected_containers

    selected_containers = property(get_selected_containers)


class StepActions(Entity):
    """Actions associated with a step"""
    _escalation = None

    @property
    def escalation(self):
        if not self._escalation:
            self.get()
            self._escalation = {}
            for node in self.root.findall('escalation'):
                self._escalation['artifacts'] = []
                self._escalation['author'] = Researcher(self.lims,
                                                        uri=node.find('request').find('author').attrib.get('uri'))
                self._escalation['request'] = uri = node.find('request').find('comment').text
                if node.find('review') is not None:  # recommended by the Etree doc
                    self._escalation['status'] = 'Reviewed'
                    self._escalation['reviewer'] = Researcher(self.lims,
                                                              uri=node.find('review').find('author').attrib.get('uri'))
                    self._escalation['answer'] = uri = node.find('review').find('comment').text
                else:
                    self._escalation['status'] = 'Pending'

                for node2 in node.findall('escalated-artifacts'):
                    art = self.lims.get_batch([Artifact(self.lims, uri=ch.attrib.get('uri')) for ch in node2])
                    self._escalation['artifacts'].extend(art)
        return self._escalation

    def get_next_actions(self):
        actions = []
        self.get()
        if self.root.find('next-actions') is not None:
            for node in self.root.find('next-actions').findall('next-action'):
                action = {
                    'artifact': Artifact(self.lims, node.attrib.get('artifact-uri')),
                    'action': node.attrib.get('action'),
                }
                if node.attrib.get('step-uri'):
                    action['step'] = Step(self.lims, uri=node.attrib.get('step-uri'))
                if node.attrib.get('rework-step-uri'):
                    action['rework-step'] = Step(self.lims, uri=node.attrib.get('rework-step-uri'))
                actions.append(action)
        return actions

    def set_next_actions(self, actions):
        for node in self.root.find('next-actions').findall('next-action'):
            art_uri = node.attrib.get('artifact-uri')
            action = [action for action in actions if action['artifact'].uri == art_uri][0]
            if 'action' in action: node.attrib['action'] = action.get('action')

    next_actions = property(get_next_actions, set_next_actions)


class ReagentKit(Entity):
    """Type of Reagent with information about the provider"""
    _URI = "reagentkits"
    _TAG = "reagent-kit"
    _PREFIX = 'kit'

    name     = StringDescriptor('name')
    supplier = StringDescriptor('supplier')
    website  = StringDescriptor('website')
    archived = BooleanDescriptor('archived')


class ReagentLot(Entity):
    """Reagent Lots contain information about a particualr lot of reagent used in a step"""
    _URI = "reagentlots"
    _TAG = "reagent-lot"
    _PREFIX = 'lot'

    reagent_kit        = EntityDescriptor('reagent-kit', ReagentKit)
    name               = StringDescriptor('name')
    lot_number         = StringDescriptor('lot-number')
    created_date       = StringDescriptor('created-date')
    last_modified_date = StringDescriptor('last-modified-date')
    expiry_date        = StringDescriptor('expiry-date')
    created_by         = EntityDescriptor('created-by', Researcher)
    last_modified_by   = EntityDescriptor('last-modified-by', Researcher)
    status             = StringDescriptor('status')
    usage_count        = IntegerDescriptor('usage-count')


class StepReagentLots(Entity):
    reagent_lots = EntityListDescriptor('reagent-lot', ReagentLot, nesting=['reagent-lots'])

class StepDetails(Entity):
    """Detail associated with a step"""

    input_output_maps = InputOutputMapList('input-output-maps')
    udf = UdfDictionaryDescriptor('fields')
    udt = UdtDictionaryDescriptor('fields')


class Step(Entity):
    "Step, as defined by the genologics API."

    _URI = 'steps'
    _PREFIX = 'stp'

    current_state = StringAttributeDescriptor('current-state')
    _reagent_lots = EntityDescriptor('reagent-lots', StepReagentLots)
    actions       = EntityDescriptor('actions', StepActions)
    placements    = EntityDescriptor('placements', StepPlacements)
    details       = EntityDescriptor('details', StepDetails)

    #program_status     = EntityDescriptor('program-status',StepProgramStatus)

    def advance(self):
        self.root = self.lims.post(
            uri="{}/advance".format(self.uri),
            data=self.lims.tostring(ElementTree.ElementTree(self.root))
        )

    @property
    def reagent_lots(self):
        return self._reagent_lots.reagent_lots


class ProtocolStep(Entity):
    """Steps key in the Protocol object"""

    _TAG = 'step'

    name                = StringAttributeDescriptor("name")
    type                = EntityDescriptor('type', Processtype)
    permittedcontainers = StringListDescriptor('container-type', nesting=['container-types'])
    queue_fields        = AttributeListDescriptor('queue-field', nesting=['queue-fields'])
    step_fields         = AttributeListDescriptor('step-field', nesting=['step-fields'])
    sample_fields       = AttributeListDescriptor('sample-field', nesting=['sample-fields'])
    step_properties     = AttributeListDescriptor('step_property', nesting=['step_properties'])
    epp_triggers        = AttributeListDescriptor('epp_trigger', nesting=['epp_triggers'])


class Protocol(Entity):
    """Protocol, holding ProtocolSteps and protocol-properties"""
    _URI = 'configuration/protocols'
    _TAG = 'protocol'

    steps      = EntityListDescriptor('step', ProtocolStep, nesting=['steps'])
    properties = AttributeListDescriptor('protocol-property', nesting=['protocol-properties'])


class Stage(Entity):
    """Holds Protocol/Workflow"""
    name     = StringAttributeDescriptor('name')
    index    = IntegerAttributeDescriptor('index')
    protocol = EntityDescriptor('protocol', Protocol)
    step     = EntityDescriptor('step', ProtocolStep)


class Workflow(Entity):
    """ Workflow, introduced in 3.5"""
    _URI = "configuration/workflows"
    _TAG = "workflow"

    name      = StringAttributeDescriptor("name")
    status    = StringAttributeDescriptor("status")
    protocols = EntityListDescriptor('protocol', Protocol, nesting=['protocols'])
    stages    = EntityListDescriptor('stage', Stage, nesting=['stages'])


class ReagentType(Entity):
    """Reagent Type, usually, indexes for sequencing"""
    _URI = "reagenttypes"
    _TAG = "reagent-type"
    _PREFIX = 'rtp'

    category = StringDescriptor('reagent-category')

    def __init__(self, lims, uri=None, id=None):
        super(ReagentType, self).__init__(lims, uri, id)
        assert self.uri is not None
        self.root = lims.get(self.uri)
        self.sequence = None
        for t in self.root.findall('special-type'):
            if t.attrib.get("name") == "Index":
                for child in t.findall("attribute"):
                    if child.attrib.get("name") == "Sequence":
                        self.sequence = child.attrib.get("value")

class Queue(Entity):
    """Queue of a given step"""
    _URI = "queues"
    _TAG= "queue"
    _PREFIX = "que"

    artifacts = EntityListDescriptor("artifact", Artifact, nesting=["artifacts"])

Sample.artifact          = EntityDescriptor('artifact', Artifact)
StepActions.step         = EntityDescriptor('step', Step)
Stage.workflow           = EntityDescriptor('workflow', Workflow)
Artifact.workflow_stages = EntityListDescriptor('workflow-stage', Stage, nesting=['workflow-stages'])
Step.configuration       = EntityDescriptor('configuration', ProtocolStep)

