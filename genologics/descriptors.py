"""Python interface to GenoLogics LIMS via its REST API.

Entities and their descriptors for the LIMS interface.

Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
Copyright (C) 2012 Per Kraulis
"""

from genologics.constants import nsmap

try:
    from urllib.parse import urlsplit, urlparse, parse_qs, urlunparse
except ImportError:
    from urllib.parse import urlsplit, urlparse, parse_qs, urlunparse

from decimal import Decimal
import datetime
import time
from xml.etree import ElementTree

import logging

logger = logging.getLogger(__name__)


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

    def get_node(self, instance):
        if self.tag:
            return instance.root.find(self.tag)
        else:
            return instance.root


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
        instance.get()
        node = self.get_node(instance)
        if node is None:
            # create the new tag
            node = ElementTree.Element(self.tag)
            instance.root.append(node)
        node.text = str(value)


class StringAttributeDescriptor(TagDescriptor):
    """An instance attribute containing a string value
    represented by an XML attribute.
    """

    def __get__(self, instance, cls):
        # Skip loading the instance if we have information in the extra dictionary. This
        # allows faster loading when the data is available in an overview page. An example is
        # that names of Stages and Protocols is available in the details page for Workflows.

        # If we have loaded the details for this entity (instance.root is not None), we always use that.
        if instance.extra is not None and instance.root is None and self.tag in instance.extra:
            return instance.extra[self.tag]
        instance.get()
        return instance.root.attrib[self.tag]

    def __set__(self, instance, value):
        instance.get()
        instance.root.attrib[self.tag] = value


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
        text = super(IntegerDescriptor, self).__get__(instance, cls)
        if text is not None:
            return int(text)


class IntegerAttributeDescriptor(TagDescriptor):
    """An instance attribute containing a integer value
    represented by an XML attribute.
    """

    def __get__(self, instance, cls):
        instance.get()
        return int(instance.root.attrib[self.tag])


class BooleanDescriptor(StringDescriptor):
    """An instance attribute containing a boolean value
    represented by an XMl element.
    """

    def __get__(self, instance, cls):
        text = super(BooleanDescriptor, self).__get__(instance, cls)
        if text is not None:
            return text.lower() == 'true'

    def __set__(self, instance, value):
        super(BooleanDescriptor, self).__set__(instance, str(value).lower())


class UdfDictionary(object):
    "Dictionary-like container of UDFs, optionally within a UDT."

    def _is_string(self, value):
        try:
            return isinstance(value, str)
        except:
            return isinstance(value, str)

    def __init__(self, instance, *args, **kwargs):
        self.instance = instance
        self._udt = kwargs.pop('udt', False)
        self.rootkeys = args
        self._rootnode = None
        self._update_elems()
        self._prepare_lookup()
        self.location = 0

    @property
    def rootnode(self):
        if self._rootnode is None:
            self._rootnode = self.instance.root
            for rootkey in self.rootkeys:
                self._rootnode = self._rootnode.find(rootkey)
        return self._rootnode

    def get_udt(self):
        if self._udt == True:
            return None
        else:
            return self._udt

    def set_udt(self, name):
        assert isinstance(name, str)
        if not self._udt:
            raise AttributeError('cannot set name for a UDF dictionary')
        self._udt = name
        elem = self.rootnode.find(nsmap('udf:type'))
        assert elem is not None
        elem.set('name', name)

    udt = property(get_udt, set_udt)

    def _update_elems(self):
        self._elems = []
        if self._udt:
            elem = self.rootnode.find(nsmap('udf:type'))
            if elem is not None:
                self._udt = elem.attrib['name']
                self._elems = elem.findall(nsmap('udf:field'))
        else:
            tag = nsmap('udf:field')
            for elem in self.rootnode.getchildren():
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

    def __contains__(self, key):
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
            vtype = node.attrib['type'].lower()

            if value is None:
                value=''
            elif vtype == 'string':
                if not self._is_string(value):
                    raise TypeError('String UDF requires str or unicode value')
            elif vtype == 'str':
                if not self._is_string(value):
                    raise TypeError('String UDF requires str or unicode value')
            elif vtype == 'text':
                if not self._is_string(value):
                    raise TypeError('Text UDF requires str or unicode value')
            elif vtype == 'numeric':
                if not isinstance(value, (int, float, Decimal)) and value != '':
                    raise TypeError('Numeric UDF requires int or float value')
                else:
                    value = str(value)
            elif vtype == 'boolean':
                if not isinstance(value, bool):
                    raise TypeError('Boolean UDF requires bool value')
                value = value and 'true' or 'false'
            elif vtype == 'date':
                if not isinstance(value, datetime.date):  # Too restrictive?
                    raise TypeError('Date UDF requires datetime.date value')
                value = str(value)
            elif vtype == 'uri':
                if not self._is_string(value):
                    raise TypeError('URI UDF requires str or punycode (unicode) value')
                value = str(value)
            else:
                raise NotImplemented("UDF type '%s'" % vtype)
	    if value is None:
	        node.text = ''
	    else:
		if not isinstance(value, str):
		    if not self._is_string(value):
			value = str(value).encode('UTF-8')
		node.text = value
            break
        else:  # Create new entry; heuristics for type
            if self._is_string(value):
                vtype = '\n' in value and 'Text' or 'String'
            elif isinstance(value, bool):
                vtype = 'Boolean'
                value = value and 'true' or 'false'
            elif isinstance(value, (int, float, Decimal)):
                vtype = 'Numeric'
                value = str(value)
            elif isinstance(value, datetime.date):
                vtype = 'Date'
                value = str(value)
            else:
                raise NotImplementedError("Cannot handle value of type '%s'"
                                          " for UDF" % type(value))
            if self._udt:
                root = self.rootnode.find(nsmap('udf:type'))
            else:
                root = self.rootnode
            elem = ElementTree.SubElement(root,
                                          nsmap('udf:field'),
                                          type=vtype,
                                          name=key)
            if not isinstance(value, str):
                if not self._is_string(value):
                    value = str(value).encode('UTF-8')

            elem.text = value

            #update the internal elements and lookup with new values
            self._update_elems()
            self._prepare_lookup()

    def __delitem__(self, key):
        del self._lookup[key]
        for node in self._elems:
            if node.attrib['name'] == key:
                self.rootnode.remove(node)
                break

    def items(self):
        return list(self._lookup.items())

    def clear(self):
        for elem in self._elems:
            self.rootnode.remove(elem)
        self._update_elems()

    def __iter__(self):
        return self

    def __next__(self):
        return self.__next__()

    def __next__(self):
        try:
            ret = list(self._lookup.keys())[self.location]
        except IndexError:
            raise StopIteration()
        self.location = self.location + 1
        return ret

    def get(self, key, default=None):
        return self._lookup.get(key, default)


class UdfDictionaryDescriptor(BaseDescriptor):
    """An instance attribute containing a dictionary of UDF values
    represented by multiple XML elements.
    """
    _UDT = False

    def __init__(self, *args):
        super(BaseDescriptor, self).__init__()
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        self.value = UdfDictionary(instance, *self.rootkeys, udt=self._UDT)
        return self.value

    def __set__(self, instance, dict_value):
        instance.get()
        udf_dict = UdfDictionary(instance, *self.rootkeys, udt=self._UDT)
        udf_dict.clear()
        for k in dict_value:
            udf_dict[k] = dict_value[k]


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
        from genologics.entities import Artifact
        instance.get()
        self.value = dict()
        for node in instance.root.findall(self.tag):
            key = node.find('value').text
            self.value[key] = Artifact(instance.lims, uri=node.attrib['uri'])
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

    def __set__(self, instance, value):
        instance.get()
        node = self.get_node(instance)
        if node is None:
            # create the new tag
            node = ElementTree.Element(self.tag)
            instance.root.append(node)
        node.attrib['uri'] = value.uri
        if value._TAG in ['project', 'sample', 'artifact', 'container']:
            node.attrib['limsid'] = value.id


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

class NestedBooleanDescriptor(TagDescriptor):
    def __init__(self, tag, *args):
        super(NestedBooleanDescriptor, self).__init__(tag)
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        result = None
        rootnode = instance.root
        for rootkey in self.rootkeys:
            rootnode = rootnode.find(rootkey)
        result = rootnode.find(self.tag).text.lower() == 'true'
        return result

    def __set__(self, instance, value):
        rootnode = instance.root
        for rootkey in self.rootkeys:
            rootnode = rootnode.find(rootkey)
        rootnode.find(self.tag).text = str(value).lower()

class NestedStringDescriptor(TagDescriptor):
    def __init__(self, tag, *args):
        super(NestedStringDescriptor, self).__init__(tag)
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        result = None
        rootnode = instance.root
        for rootkey in self.rootkeys:
            rootnode = rootnode.find(rootkey)
        result = rootnode.find(self.tag).text
        return result

    def __set__(self, instance, value):
        rootnode = instance.root
        for rootkey in self.rootkeys:
            rootnode = rootnode.find(rootkey)
        rootnode.find(self.tag).text = value

class NestedAttributeListDescriptor(StringAttributeDescriptor):
    """An instance yielding a list of dictionnaries of attributes
       for a nested xml list of XML elements"""

    def __init__(self, tag, *args):
        super(StringAttributeDescriptor, self).__init__(tag)
        self.tag = tag
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        result = []
        rootnode = instance.root
        for rootkey in self.rootkeys:
            rootnode = rootnode.find(rootkey)
        for node in rootnode.findall(self.tag):
            result.append(node.attrib)
        return result


class NestedStringListDescriptor(StringListDescriptor):
    """An instance yielding a list of strings
        for a nested list of xml elements"""

    def __init__(self, tag, *args):
        super(StringListDescriptor, self).__init__(tag)
        self.tag = tag
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        result = []
        rootnode = instance.root
        for rootkey in self.rootkeys:
            rootnode = rootnode.find(rootkey)
        for node in rootnode.findall(self.tag):
            result.append(node.text)
        return result


class NestedEntityListDescriptor(EntityListDescriptor):
    """same as EntityListDescriptor, but works on nested elements"""

    def __init__(self, tag, klass, rootkey=None, extra=[]):
        super(EntityListDescriptor, self).__init__(tag, klass)
        self.klass = klass
        self.tag = tag
        self.rootkey = rootkey
        self.extra_meta = extra

    def __get__(self, instance, cls):
        instance.get()
        result = []
        rootnode = instance.root
        if self.rootkey:
            rootnode = rootnode.find(self.rootkey)
        for node in rootnode.findall(self.tag):
            # NOTE: The name should correspond to the name on the object, not necessarily the same
            # as the name of the attribute.
            extra = {extra_name: node.attrib[extra_name] for extra_name in self.extra_meta}
            result.append(self.klass(instance.lims, uri=node.attrib['uri'], extra=extra))
        return result


class MultiPageNestedEntityListDescriptor(EntityListDescriptor):
    """same as NestedEntityListDescriptor, but works on multiple pages, for Queues"""

    def __init__(self, tag, klass, *args):
        super(EntityListDescriptor, self).__init__(tag, klass)
        self.klass = klass
        self.tag = tag
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        result = []
        rootnode = instance.root
        for rootkey in self.rootkeys:
            rootnode = rootnode.find(rootkey)
        for node in rootnode.findall(self.tag):
            result.append(self.klass(instance.lims, uri=node.attrib['uri']))

        if instance.root.find('next-page') is not None:
            next_queue_page = instance.__class__(instance.lims, uri=instance.root.find('next-page').attrib.get('uri'))
            result.extend(next_queue_page.artifacts)
        return result



class DimensionDescriptor(TagDescriptor):
    """An instance attribute containing a dictionary specifying
    the properties of a dimension of a container type.
    """

    def __get__(self, instance, cls):
        instance.get()
        node = instance.root.find(self.tag)
        return dict(is_alpha=node.find('is-alpha').text.lower() == 'true',
                    offset=int(node.find('offset').text),
                    size=int(node.find('size').text)
                    )


class LocationDescriptor(TagDescriptor):
    """An instance attribute containing a tuple (container, value)
    specifying the location of an analyte in a container.
    """

    def __get__(self, instance, cls):
        from genologics.entities import Container
        instance.get()
        node = instance.root.find(self.tag)
        if node is None:
            return (None,None)
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

    def __set__(self, instance, values):
        instance.get()
        nodes = instance.root.findall('reagent-label')
        if not nodes:
            root = instance.root
            for value in values:
                ElementTree.SubElement(root, 'reagent-label', name=value)

        elif len(values) != len(nodes):
            raise ValueError("Mismatching number of reagent labels")
        else:
            for node, value in zip(nodes, values):
                node.attrib['name'] = value


class OutputReagentList(BaseDescriptor):
    """
    Instance attribute depicting output reagents as :

    {
      output_artifact_1:[reagent_label_name_1, reagent_label_name_2,...]
      output_artifact_2:[reagent_label_name_3, reagent_label_name_4,...]
    }
    """
    def __init__(self, artifact_class):
        self.klass = artifact_class

    def __get__(self, instance, cls):
        instance.get()
        self.value = {}
        for node in instance.root.iter('output'):
            self.value[self.klass(instance.lims, uri=node.attrib['uri'])] = [subnode.attrib['name'] for subnode in node.findall('reagent-label')]

        return self.value

    def __set__(self, instance, value):
        out_r = ElementTree.Element('output-reagents')
        for artifact in value:
            out_a = ElementTree.SubElement(out_r, 'output', attrib={'uri':artifact.uri})
            for reagent_label_name in value[artifact]:
                rea_l = ElementTree.SubElement(out_a, 'reagent-label', attrib={'name':reagent_label_name})

        instance.root.remove(instance.root.find('output-reagents'))
        instance.root.append(out_r)




class InputOutputMapList(BaseDescriptor):
    """An instance attribute yielding a list of tuples (input, output)
    where each item is a dictionary, representing the input/output
    maps of a Process instance.
    """

    def __init__(self, *args):
        super(BaseDescriptor, self).__init__()
        self.rootkeys = args

    def __get__(self, instance, cls):
        instance.get()
        self.value = []
        rootnode = instance.root
        for rootkey in self.rootkeys:
            rootnode = rootnode.find(rootkey)
        for node in rootnode.findall('input-output-map'):
            input = self.get_dict(instance.lims, node.find('input'))
            output = self.get_dict(instance.lims, node.find('output'))
            self.value.append((input, output))
        return self.value

    def get_dict(self, lims, node):
        from genologics.entities import Artifact, Process
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



class ProcessTypeParametersDescriptor(object):
    def __getitem__(self, index):
        return self.params[index]

    def __setitem__(self, index, value):
        self.params[index] = value

    def __delitem__(self, index):
        del(self.params[index])

    def __init__(self, pt_instance):
        from genologics.internal_classes import ProcessTypeParameter
        pt_instance.get()
        self.tag = 'parameter'
        self.params = []
        for node in pt_instance.root.findall(self.tag):
            self.params.append(ProcessTypeParameter(pt_instance, node))

    def __repr__(self):
        return str(self._params)


class ProcessTypeProcessInputDescriptor(TagDescriptor):

    def __getitem__(self, index):
        return self._inputs[index]

    def __setitem__(self, index, value):
        self._inputs[index] = value

    def __delitem__(self, index):
        del(self._inputs[index])

    def __init__(self):
        self._inputs=[]
        self.tag = 'process-input'
        super(ProcessTypeProcessInputDescriptor, self).__init__(tag=self.tag)

    def __get__(self, instance, owner):
        from genologics.internal_classes import ProcessTypeProcessInput
        for node in  instance.root.findall(self.tag):
            self._inputs.append(ProcessTypeProcessInput(instance, node))
        return self

    def __repr__(self):
        return str(self._inputs)


class ProcessTypeProcessOutputDescriptor(TagDescriptor):

    def __getitem__(self, index):
        return self._inputs[index]

    def __setitem__(self, index, value):
        self._inputs[index] = value

    def __delitem__(self, index):
        del(self._inputs[index])

    def __init__(self):
        self._inputs=[]
        self.tag = 'process-output'
        super(ProcessTypeProcessOutputDescriptor, self).__init__(tag=self.tag)

    def __get__(self, instance, owner):
        from genologics.internal_classes import ProcessTypeProcessOutput
        for node in instance.root.findall(self.tag):
            self._inputs.append(ProcessTypeProcessOutput(instance, node))
        return self

    def __repr__(self):
        return str(self._inputs)


class NamedStringDescriptor(TagDescriptor):

    def __get__(self, instance, owner):
        self._internals={}
        for node in instance.root.findall(self.tag):
            self._internals[node.attrib['name']] = node.text
        return self._internals
