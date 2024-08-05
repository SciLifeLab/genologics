"""Python interface to GenoLogics LIMS via its REST API.

Entities and their descriptors for the LIMS interface.

Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
Copyright (C) 2012 Per Kraulis
"""

import logging
from urllib.parse import parse_qs, urlparse, urlsplit, urlunparse
from xml.etree import ElementTree

from genologics.constants import nsmap
from genologics.descriptors import (
    BooleanDescriptor,
    DimensionDescriptor,
    EntityDescriptor,
    EntityListDescriptor,
    ExternalidListDescriptor,
    InputOutputMapList,
    IntegerAttributeDescriptor,
    IntegerDescriptor,
    LocationDescriptor,
    MultiPageNestedEntityListDescriptor,
    NamedStringDescriptor,
    NestedAttributeListDescriptor,
    NestedBooleanDescriptor,
    NestedEntityListDescriptor,
    NestedStringDescriptor,
    NestedStringListDescriptor,
    OutputReagentList,
    PlacementDictionaryDescriptor,
    ProcessTypeParametersDescriptor,
    ProcessTypeProcessInputDescriptor,
    ProcessTypeProcessOutputDescriptor,
    ReagentLabelList,
    StringAttributeDescriptor,
    StringDescriptor,
    StringDictionaryDescriptor,
    StringListDescriptor,
    UdfDictionaryDescriptor,
    UdtDictionaryDescriptor,
)

logger = logging.getLogger(__name__)


class SampleHistory:
    """Class handling the history generation for a given sample/artifact
    AFAIK the only fields of the history that are read are proc.type and outart"""

    def __init__(
        self,
        sample_name=None,
        output_artifact=None,
        input_artifact=None,
        lims=None,
        pro_per_art=None,
        test=False,
    ):
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
            raise AttributeError(
                "History cannot be computed without a valid lims object"
            )

    def control(self):
        """this can be used to check the content of the object."""
        logger.info(f"SAMPLE NAME: {self.sample_name}")
        logger.info(f"outart : {self.history_list[0]}")
        # logger.info ("\nmap :")
        # for key, value in self.art_map.iteritems():
        #    logger.info(value[1]+"->"+value[0].id+"->"+key)
        logger.info("\nHistory :\n\n")
        logger.info("Input\tProcess\tProcess info")
        for key, dict in self.history.items():
            logger.info(key)
            for key2, dict2 in dict.items():
                logger.info(f"\t{key2}")
                for key, value in dict2.items():
                    logger.info(
                        "\t\t{}->{}".format(
                            key, (value if value is not None else "None")
                        )
                    )
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
            artifacts = self.lims.get_artifacts(
                sample_name=self.sample_name, type="Analyte", resolve=False
            )
            for one_art in artifacts:
                input_arts = one_art.input_artifact_list()
                for input_art in input_arts:
                    for samp in input_art.samples:
                        if samp.name == self.sample_name:
                            samp_art_map[one_art.id] = (
                                one_art.parent_process,
                                input_art.id,
                            )

        self.art_map = samp_art_map

    def alternate_history(self, out_art, in_art=None):
        """This is a try at another way to generate the history.
        This one iterates over Artifact.parent_process and Process.all_inputs()
        Then, it takes all the child processes for each input (because we want
        qc processes too) and puts everything in a dictionnary.
        """
        history = {}
        # getting the list of all expected analytes.
        artifacts = self.lims.get_artifacts(
            sample_name=self.sample_name, type="Analyte", resolve=False
        )
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
                history[in_art][tempProcess.id] = {
                    "date": tempProcess.date_run,
                    "id": tempProcess.id,
                    "outart": (
                        out_art
                        if out_art in [out.id for out in tempProcess.all_outputs()]
                        else None
                    ),
                    "inart": in_art,
                    "type": tempProcess.type.id,
                    "name": tempProcess.type.name,
                }
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
                            for tempProcess in (
                                self.processes_per_artifact[i.id]
                                if self.processes_per_artifact
                                else self.lims.get_processes(inputartifactlimsid=i.id)
                            ):  # If there is a loacl map, use it. else, query the lims.
                                history[i.id][tempProcess.id] = {
                                    "date": tempProcess.date_run,
                                    "id": tempProcess.id,
                                    "outart": (
                                        o.id
                                        if tempProcess.id == o.parent_process.id
                                        else None
                                    ),
                                    "inart": i.id,
                                    "type": tempProcess.type.id,
                                    "name": tempProcess.type.name,
                                }

                            logger.info("found input " + i.id)
                            inputs.append(
                                i.id
                            )  # this will be the sorted list of artifacts used to rebuild the history in order
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
            history, out_artifact = self._add_out_art_process_conection_list(
                input_art, out_artifact, history
            )
            hist_list.append(input_art)
        while out_artifact in self.art_map:
            pro, input_art = self.art_map[out_artifact]
            hist_list.append(input_art)
            history, out_artifact = self._add_out_art_process_conection_list(
                input_art, out_artifact, history
            )
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
        for process in (
            self.processes_per_artifact[input_art]
            if self.processes_per_artifact
            else self.lims.get_processes(inputartifactlimsid=input_art)
        ):
            # outputs = map(lambda a: (a.id), process.all_outputs())
            outputs = [a.id for a in process.all_outputs()]
            outart = out_artifact if out_artifact in outputs else None
            step_info = {
                "date": process.date_run,
                "id": process.id,
                "outart": outart,
                "inart": input_art,
                "type": process.type.id,
                "name": process.type.name,
            }
            if input_art in history:
                history[input_art][process.id] = step_info
            else:
                history[input_art] = {process.id: step_info}
        return history, input_art


class Entity:
    "Base class for the entities in the LIMS database."

    _TAG: str | None = None
    _URI: str | None = None
    _PREFIX: str | None = None

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
            if hasattr(self, "lims"):
                return
            if not uri:
                uri = lims.get_uri(self._URI, id)
            lims.cache[uri] = self
            self.root = None
        self.lims = lims
        self._uri = uri
        self.root = None

    def __str__(self):
        return f"{self.__class__.__name__}({self.id})"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.uri})"

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
        return parts.path.split("/")[-1]

    def get(self, force=False):
        "Get the XML data for this instance."
        if not force and self.root is not None:
            return
        self.root = self.lims.get(self.uri)

    def put(self):
        "Save this instance by doing PUT of its serialized XML."
        data = self.lims.tostring(ElementTree.ElementTree(self.root))
        self.lims.put(self.uri, data)

    def post(self):
        "Save this instance with POST"
        data = self.lims.tostring(ElementTree.ElementTree(self.root))
        self.lims.post(self.uri, data)

    def xml(self):
        return self.lims.tostring(ElementTree.ElementTree(self.root))

    @classmethod
    def _create(cls, lims, creation_tag=None, udfs=None, **kwargs):
        """Create an instance from attributes and return it"""
        if not udfs:
            udfs = {}
        instance = cls(lims, _create_new=True)
        if creation_tag:
            instance.root = ElementTree.Element(nsmap(cls._PREFIX + ":" + creation_tag))
        elif cls._TAG:
            instance.root = ElementTree.Element(nsmap(cls._PREFIX + ":" + cls._TAG))
        else:
            instance.root = ElementTree.Element(
                nsmap(cls._PREFIX + ":" + cls.__name__.lower())
            )
        for key in udfs:
            instance.udf[key] = udfs[key]
        for attribute in kwargs:
            if hasattr(instance, attribute):
                setattr(instance, attribute, kwargs.get(attribute))
            else:
                raise TypeError(
                    f"{cls.__name__} create: got an unexpected keyword argument '{attribute}'"
                )

        return instance

    @classmethod
    def create(cls, lims, creation_tag=None, **kwargs):
        """Create an instance from attributes then post it to the LIMS"""
        instance = cls._create(lims, creation_tag=creation_tag, **kwargs)
        data = lims.tostring(ElementTree.ElementTree(instance.root))
        instance.root = lims.post(uri=lims.get_uri(cls._URI), data=data)
        instance._uri = instance.root.attrib["uri"]
        return instance


class Instrument(Entity):
    """Lab Instrument"""

    _URI = "instruments"
    _TAG = "instrument"
    _PREFIX = "inst"

    name = StringDescriptor("name")
    type = StringDescriptor("type")
    serial_number = StringDescriptor("serial-number")
    expiry_date = StringDescriptor("expiry-date")
    archived = BooleanDescriptor("archived")


class Lab(Entity):
    "Lab; container of researchers."

    _URI = "labs"
    _PREFIX = "lab"

    name = StringDescriptor("name")
    billing_address = StringDictionaryDescriptor("billing-address")
    shipping_address = StringDictionaryDescriptor("shipping-address")
    udf = UdfDictionaryDescriptor()
    udt = UdtDictionaryDescriptor()
    externalids = ExternalidListDescriptor()
    website = StringDescriptor("website")


class Researcher(Entity):
    "Person; client scientist or lab personnel. Associated with a lab."

    _URI = "researchers"
    _PREFIX = "res"

    first_name = StringDescriptor("first-name")
    last_name = StringDescriptor("last-name")
    phone = StringDescriptor("phone")
    fax = StringDescriptor("fax")
    email = StringDescriptor("email")
    initials = StringDescriptor("initials")
    lab = EntityDescriptor("lab", Lab)
    udf = UdfDictionaryDescriptor()
    udt = UdtDictionaryDescriptor()
    externalids = ExternalidListDescriptor()

    # credentials XXX
    username = NestedStringDescriptor("username", "credentials")
    account_locked = NestedBooleanDescriptor("account-locked", "credentials")

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"


class Permission(Entity):
    """A Clarity permission. Only supports GET"""

    name = StringDescriptor("name")
    action = StringDescriptor("action")
    description = StringDescriptor("description")


class Role(Entity):
    """Clarity Role, hosting permissions"""

    name = StringDescriptor("name")
    researchers = NestedEntityListDescriptor("researcher", Researcher, "researchers")
    permissions = NestedEntityListDescriptor("permission", Permission, "permissions")


class Reagent_label(Entity):
    """Reagent label element"""

    reagent_label = StringDescriptor("reagent-label")


class Note(Entity):
    "Note attached to a project or a sample."

    content = StringDescriptor(None)  # root element


class File(Entity):
    "File attached to a project or a sample."

    attached_to = StringDescriptor("attached-to")
    content_location = StringDescriptor("content-location")
    original_location = StringDescriptor("original-location")
    is_published = BooleanDescriptor("is-published")


class Project(Entity):
    "Project concerning a number of samples; associated with a researcher."

    _URI = "projects"
    _TAG = "project"
    _PREFIX = "prj"

    name = StringDescriptor("name")
    open_date = StringDescriptor("open-date")
    close_date = StringDescriptor("close-date")
    invoice_date = StringDescriptor("invoice-date")
    researcher = EntityDescriptor("researcher", Researcher)
    udf = UdfDictionaryDescriptor()
    udt = UdtDictionaryDescriptor()
    files = EntityListDescriptor(nsmap("file:file"), File)
    externalids = ExternalidListDescriptor()
    # permissions XXX


class Sample(Entity):
    "Customer's sample to be analyzed; associated with a project."

    _URI = "samples"
    _TAG = "sample"
    _PREFIX = "smp"

    name = StringDescriptor("name")
    date_received = StringDescriptor("date-received")
    date_completed = StringDescriptor("date-completed")
    project = EntityDescriptor("project", Project)
    submitter = EntityDescriptor("submitter", Researcher)
    # artifact: defined below
    udf = UdfDictionaryDescriptor()
    udt = UdtDictionaryDescriptor()
    notes = EntityListDescriptor("note", Note)
    files = EntityListDescriptor(nsmap("file:file"), File)
    externalids = ExternalidListDescriptor()
    # biosource XXX

    @classmethod
    def create(cls, lims, container, position, udfs=None, **kwargs):
        """Create an instance of Sample from attributes then post it to the LIMS"""
        if udfs is None:
            udfs = {}
        if not isinstance(container, Container):
            raise TypeError(f"{container} is not of type Container")
        instance = super()._create(
            lims, creation_tag="samplecreation", udfs=udfs, **kwargs
        )

        location = ElementTree.SubElement(instance.root, "location")
        ElementTree.SubElement(location, "container", dict(uri=container.uri))
        position_element = ElementTree.SubElement(location, "value")
        position_element.text = position
        data = lims.tostring(ElementTree.ElementTree(instance.root))
        instance.root = lims.post(uri=lims.get_uri(cls._URI), data=data)
        instance._uri = instance.root.attrib["uri"]
        return instance


class Containertype(Entity):
    "Type of container for analyte artifacts."

    _TAG = "container-type"
    _URI = "containertypes"
    _PREFIX = "ctp"

    name = StringAttributeDescriptor("name")
    calibrant_wells = StringListDescriptor("calibrant-well")
    unavailable_wells = StringListDescriptor("unavailable-well")
    x_dimension = DimensionDescriptor("x-dimension")
    y_dimension = DimensionDescriptor("y-dimension")


class Container(Entity):
    "Container for analyte artifacts."

    _URI = "containers"
    _TAG = "container"
    _PREFIX = "con"

    name = StringDescriptor("name")
    type = EntityDescriptor("type", Containertype)
    occupied_wells = IntegerDescriptor("occupied-wells")
    placements = PlacementDictionaryDescriptor("placement")
    udf = UdfDictionaryDescriptor()
    udt = UdtDictionaryDescriptor()
    state = StringDescriptor("state")

    def get_placements(self):
        """Get the dictionary of locations and artifacts
        using the more efficient batch call."""
        result = self.placements.copy()
        self.lims.get_batch(list(result.values()))
        return result

    def delete(self):
        self.lims.delete(self.uri)


class Udfconfig(Entity):
    "Instance of field type (cnf namespace)."

    _URI = "configuration/udfs"

    name = StringDescriptor("name")
    attach_to_name = StringDescriptor("attach-to-name")
    attach_to_category = StringDescriptor("attach-to-category")
    show_in_lablink = BooleanDescriptor("show-in-lablink")
    allow_non_preset_values = BooleanDescriptor("allow-non-preset-values")
    first_preset_is_default_value = BooleanDescriptor("first-preset-is-default-value")
    show_in_tables = BooleanDescriptor("show-in-tables")
    is_editable = BooleanDescriptor("is-editable")
    is_required = BooleanDescriptor("is-required")
    is_deviation = BooleanDescriptor("is-deviation")
    is_controlled_vocabulary = BooleanDescriptor("is-controlled-vocabulary")
    presets = StringListDescriptor("preset")


class Processtype(Entity):
    _TAG = "process-type"
    _URI = "processtypes"
    _PREFIX = "ptp"

    def __init__(self, lims, uri=None, id=None, _create_new=False):
        super().__init__(lims, uri, id, _create_new)
        self.parameters = ProcessTypeParametersDescriptor(self)

    name = StringAttributeDescriptor("name")
    field_definition = EntityListDescriptor("field-definition", Udfconfig)
    process_inputs = ProcessTypeProcessInputDescriptor()
    process_outputs = ProcessTypeProcessOutputDescriptor()
    process_type_attribute = NamedStringDescriptor("process-type-attribute")

    @property
    def process_input(self):
        return self.process_inputs[0]


class ControlType(Entity):
    _URI = "controltypes"
    _TAG = "control-type"
    _PREFIX = "ctrltp"

    name = StringAttributeDescriptor("name")
    supplier = StringDescriptor("supplier")
    archived = BooleanDescriptor("archived")
    single_step = BooleanDescriptor("single_step")


class Process(Entity):
    "Process (instance of Processtype) executed producing ouputs from inputs."

    _URI = "processes"
    _PREFIX = "prc"

    type = EntityDescriptor("type", Processtype)
    date_run = StringDescriptor("date-run")
    technician = EntityDescriptor("technician", Researcher)
    protocol_name = StringDescriptor("protocol-name")
    input_output_maps = InputOutputMapList()
    udf = UdfDictionaryDescriptor()
    udt = UdtDictionaryDescriptor()
    files = EntityListDescriptor(nsmap("file:file"), File)
    process_parameter = StringDescriptor("process-parameter")
    instrument = EntityDescriptor("instrument", Instrument)

    # process_parameters XXX

    def outputs_per_input(
        self, inart, ResultFile=False, SharedResultFile=False, Analyte=False
    ):
        """Getting all the output artifacts related to a particual input artifact"""

        inouts = [io for io in self.input_output_maps if io[0]["limsid"] == inart]
        if ResultFile:
            inouts = [io for io in inouts if io[1]["output-type"] == "ResultFile"]
        elif SharedResultFile:
            inouts = [io for io in inouts if io[1]["output-type"] == "SharedResultFile"]
        elif Analyte:
            inouts = [io for io in inouts if io[1]["output-type"] == "Analyte"]
        outs = [io[1]["uri"] for io in inouts]
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
            ids = [io[0]["limsid"] for io in self.input_output_maps]
        except TypeError:
            logger.error("Process ", self, " has no input artifacts")
            raise TypeError
        if unique:
            ids = list(frozenset(ids))
        if resolve:
            return self.lims.get_batch(
                [Artifact(self.lims, id=id) for id in ids if id is not None]
            )
        else:
            return [Artifact(self.lims, id=id) for id in ids if id is not None]

    def all_outputs(self, unique=True, resolve=False):
        """Retrieving all output artifacts from input_output_maps
        if unique is true, no duplicates are returned.
        """
        # Given how ids is structured, io[1] might be None : some process don't have an output.
        ids = [io[1]["limsid"] for io in self.input_output_maps if io[1] is not None]
        if unique:
            ids = list(frozenset(ids))
        if resolve:
            return self.lims.get_batch(
                [Artifact(self.lims, id=id) for id in ids if id is not None]
            )
        else:
            return [Artifact(self.lims, id=id) for id in ids if id is not None]

    def shared_result_files(self):
        """Retreve all resultfiles of output-generation-type PerAllInputs."""
        artifacts = self.all_outputs(unique=True)
        return [a for a in artifacts if a.output_type == "SharedResultFile"]

    def result_files(self):
        """Retreve all resultfiles of output-generation-type perInput."""
        artifacts = self.all_outputs(unique=True)
        return [a for a in artifacts if a.output_type == "ResultFile"]

    def analytes(self):
        """Retreving the output Analytes of the process, if existing.
        If the process is not producing any output analytes, the input
        analytes are returned. Input/Output is returned as a information string.
        Makes aggregate processes and normal processes look the same."""
        info = "Output"
        artifacts = self.all_outputs(unique=True)
        analytes = [a for a in artifacts if a.type == "Analyte"]
        if len(analytes) == 0:
            artifacts = self.all_inputs(unique=True)
            analytes = [a for a in artifacts if a.type == "Analyte"]
            info = "Input"
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

    _URI = "artifacts"
    _TAG = "artifact"
    _PREFIX = "art"

    name = StringDescriptor("name")
    type = StringDescriptor("type")
    output_type = StringDescriptor("output-type")
    parent_process = EntityDescriptor("parent-process", Process)
    volume = StringDescriptor("volume")
    concentration = StringDescriptor("concentration")
    qc_flag = StringDescriptor("qc-flag")
    location = LocationDescriptor("location")
    working_flag = BooleanDescriptor("working-flag")
    samples = EntityListDescriptor("sample", Sample)
    udf = UdfDictionaryDescriptor()
    files = EntityListDescriptor(nsmap("file:file"), File)
    reagent_labels = ReagentLabelList()

    # artifact_flags XXX
    # artifact_groups XXX

    def input_artifact_list(self):
        """Returns the input artifact ids of the parrent process."""
        input_artifact_list = []
        try:
            for tuple in self.parent_process.input_output_maps:
                if tuple[1]["limsid"] == self.id:
                    input_artifact_list.append(tuple[0]["uri"])  # ['limsid'])
        except:
            pass
        return input_artifact_list

    def get_state(self):
        "Parse out the state value from the URI."
        parts = urlparse(self.uri)
        params = parse_qs(parts.query)
        try:
            return params["state"][0]
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
        if "state" in parts[4]:
            stateless_uri = urlunparse([parts[0], parts[1], parts[2], parts[3], "", ""])
            return Artifact(self.lims, uri=stateless_uri)
        else:
            return self

    # XXX set_state ?
    state = property(get_state)  # type: ignore
    stateless = property(stateless)  # type: ignore

    def _get_workflow_stages_and_statuses(self):
        self.get()
        result = []
        rootnode = self.root.find("workflow-stages")
        for node in rootnode.findall("workflow-stage"):
            result.append(
                (
                    Stage(self.lims, uri=node.attrib["uri"]),
                    node.attrib["status"],
                    node.attrib["name"],
                )
            )
        return result

    workflow_stages_and_statuses = property(_get_workflow_stages_and_statuses)


class StepPools(Entity):
    """Pools from within a step. Supports POST
    pools : [ {'output' : output_art, 'name' : 'AAAA', 'inputs':[input_art_1, input_art_2, ...]}, ...]
    available_inputs : {input1:{'replicates':N}}
    When POSTing, only pools need to be updated, available_inputs can be left as is.
    In pools, output can be left blank, Clarity will generate an output artifact."""

    _pools = None
    _available_inputs = None

    def _remove_available_inputs(self, input_art):
        """removes an input from the available inputs, one replicate at a time"""
        self.get_available_inputs()
        rep = self._available_inputs.get(input_art, {"replicates": 0}).get(
            "replicates", 1
        )
        if rep > 1:
            self._available_inputs[input_art]["replicates"] = rep - 1
        elif rep == 1:
            del self._available_inputs[input_art]
        else:
            logger.info(f"using more inputs than replicates for input {input_art.uri}")
        self.available_inputs = self._available_inputs

    def set_available_inputs(self, available_inputs):
        available_inputs_root = self.root.find("available-inputs")
        available_inputs_root.clear()
        for input_art in available_inputs:
            current_elem = ElementTree.SubElement(available_inputs_root, "input")
            current_elem.attrib["uri"] = input_art.uri
            current_elem.attrib["replicates"] = str(
                available_inputs[input_art]["replicates"]
            )
        self._available_inputs = available_inputs

    def get_available_inputs(self):
        if not self._available_inputs:
            self.get()
            self._available_inputs = {}
            for ai_node in self.root.find("available-inputs").findall("input"):
                input = Artifact(self.lims, uri=ai_node.attrib["uri"])
                self._available_inputs[input] = {}
                if "replicates" in ai_node.attrib:
                    self._available_inputs[input]["replicates"] = int(
                        ai_node.attrib["replicates"]
                    )

        return self._available_inputs

    def get_pools(self):
        if not self._pools:
            self.get()
            self._pools = []

            for idx, pool_node in enumerate(
                self.root.find("pooled-inputs").findall("pool")
            ):
                pool_name = pool_node.attrib.get("name", f"Pool #{idx + 1}")
                pool_object = {"name": pool_name, "inputs": [], "output": None}
                if pool_node.attrib.get("output-uri", False):
                    pool_object["output"] = Artifact(
                        self.lims, uri=pool_node.attrib["output-uri"]
                    )
                for input_node in pool_node.findall("input"):
                    input = Artifact(self.lims, uri=input_node.attrib["uri"])
                    pool_object["inputs"].append(input)

                self._pools.append(pool_object)

        return self._pools

    def set_pools(self, pools):
        pool_root = self.root.find("pooled-inputs")
        pool_root.clear()
        for idx, pool_obj in enumerate(pools):
            current_pool = ElementTree.SubElement(pool_root, "pool")
            if pool_obj.get("output", False):
                current_pool.attrib["output-uri"] = pool_obj["output"].uri
            current_pool.attrib["name"] = pool_obj.get("name", f"Pool #{idx + 1}")
            for input_art in pool_obj.get("inputs", []):
                current_input = ElementTree.SubElement(current_pool, "input")
                current_input.attrib["uri"] = input_art.uri
                self._remove_available_inputs(input_art)

        self._pools = pools

    pools = property(get_pools, set_pools)
    available_inputs = property(get_available_inputs, set_available_inputs)


class StepPlacements(Entity):
    """Placements from within a step. Supports POST"""

    _placementslist = None

    # [[A,(C,'A:1')][A,(C,'A:2')]] where A is an Artifact and C a Container
    def get_placement_list(self):
        if not self._placementslist:
            # Only fetch the data once.
            self.get()
            self._placementslist = []
            for node in self.root.find("output-placements").findall("output-placement"):
                input = Artifact(self.lims, uri=node.attrib["uri"])
                location = (None, None)
                if node.find("location") is not None:
                    location = (
                        Container(
                            self.lims,
                            uri=node.find("location").find("container").attrib["uri"],
                        ),
                        node.find("location").find("value").text,
                    )
                self._placementslist.append([input, location])
        return self._placementslist

    def set_placement_list(self, value):
        containers = set()
        self.get_placement_list()
        placement_dict = {x[0].stateless.uri: x for x in value}
        for node in self.root.find("output-placements").findall("output-placement"):
            location = placement_dict[node.attrib["uri"]][1]
            container = location[0]
            well = location[1]
            if container and location:
                containers.add(container)
                if node.find("location") is not None:
                    cont_el = node.find("location").find("container")
                    cont_el.attrib["uri"] = container.uri
                    cont_el.attrib["limsid"] = container.id
                    value_el = node.find("location").find("value")
                    value_el.text = well
                else:
                    loc_el = ElementTree.SubElement(node, "location")
                    cont_el = ElementTree.SubElement(
                        loc_el,
                        "container",
                        {"uri": container.uri, "limsid": container.id},
                    )
                    well_el = ElementTree.SubElement(loc_el, "value")
                    well_el.text = well  # not supported in the constructor
        # Handle selected containers
        sc = self.root.find("selected-containers")
        sc.clear()
        for cont in containers:
            ElementTree.SubElement(sc, "container", uri=cont.uri)
        self._placementslist = value

    placement_list = property(get_placement_list, set_placement_list)

    _selected_containers = None

    def get_selected_containers(self):
        _selected_containers = []
        if not _selected_containers:
            self.get()
            for node in self.root.find("selected-containers").findall("container"):
                _selected_containers.append(
                    Container(self.lims, uri=node.attrib["uri"])
                )

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
            for node in self.root.findall("escalation"):
                self._escalation["artifacts"] = []
                self._escalation["author"] = Researcher(
                    self.lims, uri=node.find("request").find("author").attrib.get("uri")
                )
                try:
                    self._escalation["request"] = (
                        node.find("request").find("comment").text
                    )
                except:
                    self._escalation["request"] = ""

                if node.find("review") is not None:  # recommended by the Etree doc
                    self._escalation["status"] = "Reviewed"
                    self._escalation["reviewer"] = Researcher(
                        self.lims,
                        uri=node.find("review").find("author").attrib.get("uri"),
                    )
                    try:
                        self._escalation["answer"] = (
                            node.find("review").find("comment").text
                        )
                    except:
                        self._escalation["answer"] = ""

                else:
                    self._escalation["status"] = "Pending"

                for node2 in node.findall("escalated-artifacts"):
                    art = self.lims.get_batch(
                        [Artifact(self.lims, uri=ch.attrib.get("uri")) for ch in node2]
                    )
                    self._escalation["artifacts"].extend(art)
        return self._escalation

    def get_next_actions(self):
        actions = []
        self.get()
        if self.root.find("next-actions") is not None:
            for node in self.root.find("next-actions").findall("next-action"):
                action = {
                    "artifact": Artifact(self.lims, node.attrib.get("artifact-uri")),
                    "action": node.attrib.get("action"),
                }
                if node.attrib.get("step-uri"):
                    action["step"] = Step(self.lims, uri=node.attrib.get("step-uri"))
                if node.attrib.get("rework-step-uri"):
                    action["rework-step"] = Step(
                        self.lims, uri=node.attrib.get("rework-step-uri")
                    )
                actions.append(action)
        return actions

    def set_next_actions(self, actions):
        action_dict = {a["artifact"].uri: a for a in actions}
        for node in self.root.find("next-actions").findall("next-action"):
            art_uri = node.attrib.get("artifact-uri")
            action = action_dict[art_uri]
            if "action" in action:
                node.attrib["action"] = action.get("action")
                if "step-uri" in action:
                    node.attrib["step-uri"] = action.get("step-uri")
                if "rework-step-uri" in action:
                    node.attrib["rework-step-uri"] = action.get("rework-step-uri")

    next_actions = property(get_next_actions, set_next_actions)


class StepProgramStatus(Entity):
    """Allows custom handling of program status.
    message supports HTML. Cross handling of EPPs is possible.
    Supports PUT"""

    status = StringDescriptor("status")
    message = StringDescriptor("message")


class ReagentKit(Entity):
    """Type of Reagent with information about the provider"""

    _URI = "reagentkits"
    _TAG = "reagent-kit"
    _PREFIX = "kit"

    name = StringDescriptor("name")
    supplier = StringDescriptor("supplier")
    website = StringDescriptor("website")
    archived = BooleanDescriptor("archived")


class ReagentLot(Entity):
    """Reagent Lots contain information about a particualr lot of reagent used in a step"""

    _URI = "reagentlots"
    _TAG = "reagent-lot"
    _PREFIX = "lot"

    reagent_kit = EntityDescriptor("reagent-kit", ReagentKit)
    name = StringDescriptor("name")
    lot_number = StringDescriptor("lot-number")
    created_date = StringDescriptor("created-date")
    last_modified_date = StringDescriptor("last-modified-date")
    expiry_date = StringDescriptor("expiry-date")
    created_by = EntityDescriptor("created-by", Researcher)
    last_modified_by = EntityDescriptor("last-modified-by", Researcher)
    status = StringDescriptor("status")
    usage_count = IntegerDescriptor("usage-count")


class StepReagentLots(Entity):
    reagent_lots = NestedEntityListDescriptor("reagent-lot", ReagentLot, "reagent-lots")


class StepDetails(Entity):
    """Detail associated with a step"""

    input_output_maps = InputOutputMapList("input-output-maps")
    udf = UdfDictionaryDescriptor("fields")
    udt = UdtDictionaryDescriptor("fields")


class StepReagents(Entity):
    reagent_category = StringDescriptor("reagent-category")
    output_reagents = OutputReagentList(Artifact)


class Step(Entity):
    "Step, as defined by the genologics API."

    _URI = "steps"
    _PREFIX = "stp"

    current_state = StringAttributeDescriptor("current-state")
    _reagent_lots = EntityDescriptor("reagent-lots", StepReagentLots)
    actions = EntityDescriptor("actions", StepActions)
    date_started = StringDescriptor("date-started")
    date_completed = StringDescriptor("date-completed")
    placements = EntityDescriptor("placements", StepPlacements)
    details = EntityDescriptor("details", StepDetails)
    step_pools = EntityDescriptor("pools", StepPools)
    program_status = EntityDescriptor("program-status", StepProgramStatus)
    reagents = EntityDescriptor("reagents", StepReagents)

    def advance(self):
        self.get()
        self.root = self.lims.post(
            uri=f"{self.uri}/advance",
            data=self.lims.tostring(ElementTree.ElementTree(self.root)),
        )

    @property
    def reagent_lots(self):
        return self._reagent_lots.reagent_lots

    @classmethod
    def create(cls, lims, protocol_step, container_type, inputs, **kwargs):
        """
        Create a new instance of a Step. This method will start a step from queued artifacts.

        :param protocol_step: the ProtocolStep class object specifying the step to start.
        :param inputs: A list of Aritfact class objects as input to the step.
            These need to be queued for that step for the query to be successful.
        """
        if not isinstance(protocol_step, ProtocolStep):
            raise TypeError(f"{protocol_step} is not of type ProtocolStep")
        elif not isinstance(container_type, Containertype):
            raise TypeError(f"{container_type} is not of type Containertype")
        elif not all([isinstance(input, Artifact) for input in inputs]):
            raise TypeError(f"{inputs} does not contain only items of type Artifact")

        instance = super()._create(lims, creation_tag="step-creation", **kwargs)

        # Setup configuration element
        configuration_element = ElementTree.SubElement(instance.root, "configuration")
        configuration_element.attrib["uri"] = protocol_step.uri
        configuration_element.text = protocol_step.name

        # Setup container type element
        container_type_element = ElementTree.SubElement(instance.root, "container-type")
        container_type_element.text = container_type.name

        # Setup inputs element
        inputs_element = ElementTree.SubElement(instance.root, "inputs")
        for input in inputs:
            input_element = ElementTree.SubElement(inputs_element, "input")
            input_element.attrib["uri"] = input.uri

        data = lims.tostring(ElementTree.ElementTree(instance.root))

        instance.root = lims.post(uri=lims.get_uri(cls._URI), data=data)
        instance._uri = instance.root.attrib["uri"]

        return instance


class ProtocolStep(Entity):
    """Steps key in the Protocol object"""

    _TAG = "step"

    name = StringAttributeDescriptor("name")
    type = EntityDescriptor("process-type", Processtype)
    permittedcontainers = NestedStringListDescriptor(
        "container-type", "permitted-containers"
    )
    permitted_control_types = NestedEntityListDescriptor(
        "control-type", ControlType, "permitted-control-types"
    )
    required_reagent_kits = NestedEntityListDescriptor(
        "reagent-kit", ReagentKit, "required-reagent-kits"
    )
    queue_fields = NestedAttributeListDescriptor("queue-field", "queue-fields")
    step_fields = NestedAttributeListDescriptor("step-field", "step-fields")
    sample_fields = NestedAttributeListDescriptor("sample-field", "sample-fields")
    step_properties = NestedAttributeListDescriptor("step-property", "step-properties")
    epp_triggers = NestedAttributeListDescriptor("epp-trigger", "epp-triggers")


class Protocol(Entity):
    """Protocol, holding ProtocolSteps and protocol-properties"""

    _URI = "configuration/protocols"
    _TAG = "protocol"

    steps = NestedEntityListDescriptor("step", ProtocolStep, "steps")
    properties = NestedAttributeListDescriptor(
        "protocol-property", "protocol-properties"
    )


class Automation(Entity):
    """Automation, holding Automation configurations"""

    _URI = "configuration/automations"
    _TAG = "automation"

    process_types = NestedEntityListDescriptor(
        "process-type", Processtype, "process-types"
    )
    string = NestedStringDescriptor("string")
    name = StringAttributeDescriptor("name")
    context = NestedStringDescriptor("context")


class Stage(Entity):
    """Holds Protocol/Workflow"""

    name = StringAttributeDescriptor("name")
    index = IntegerAttributeDescriptor("index")
    protocol = EntityDescriptor("protocol", Protocol)
    step = EntityDescriptor("step", ProtocolStep)


class Workflow(Entity):
    """Workflow, introduced in 3.5"""

    _URI = "configuration/workflows"
    _TAG = "workflow"

    name = StringAttributeDescriptor("name")
    status = StringAttributeDescriptor("status")
    protocols = NestedEntityListDescriptor("protocol", Protocol, "protocols")
    stages = NestedEntityListDescriptor("stage", Stage, "stages")


class ReagentType(Entity):
    """Reagent Type, usually, indexes for sequencing"""

    _URI = "reagenttypes"
    _TAG = "reagent-type"
    _PREFIX = "rtp"

    category = StringDescriptor("reagent-category")
    name = StringAttributeDescriptor("name")

    def __init__(self, lims, uri=None, id=None):
        super().__init__(lims, uri, id)
        assert self.uri is not None
        self.root = lims.get(self.uri)
        self.sequence = None
        for t in self.root.findall("special-type"):
            if t.attrib.get("name") == "Index":
                for child in t.findall("attribute"):
                    if child.attrib.get("name") == "Sequence":
                        self.sequence = child.attrib.get("value")


class Queue(Entity):
    """Queue of a given step. Will recursively get all the pages of artifacts, and therefore, can be quite slow to load"""

    _URI = "queues"
    _TAG = "queue"
    _PREFIX = "que"

    artifacts = MultiPageNestedEntityListDescriptor("artifact", Artifact, "artifacts")


# Set class-interdependent class variables
setattr(Sample, "artifact", EntityDescriptor("artifact", Artifact))
setattr(StepActions, "step", EntityDescriptor("step", Step))
setattr(Stage, "workflow", EntityDescriptor("workflow", Workflow))
setattr(
    Artifact,
    "workflow_stages",
    NestedEntityListDescriptor("workflow-stage", Stage, "workflow-stages"),
)
setattr(Step, "configuration", EntityDescriptor("configuration", ProtocolStep))
setattr(
    StepProgramStatus, "configuration", EntityDescriptor("configuration", ProtocolStep)
)
setattr(Researcher, "roles", NestedEntityListDescriptor("role", Role, "credentials"))
