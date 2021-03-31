#!/usr/bin/env python

from xml.etree import ElementTree
import requests


"""
In order to use the patched get : 
1 - import this module and set XML_DICT to your own XML dict. 
    The expected format is { "$entity_uri_1" : "$entity_xml_1",
                             "$entity_uri_2" : "$entity_xml_2",
                              ...}
2 - Set up a test case and use the Mock's library path function to patch "genologics.lims.Lims.get" with this module's "patched get"
    This will replace http calls to your lims by the XML you prepared. You can find an example of this in tests/test_example.py.

"""



XML_DICT = {}


def patched_get(*args, **kwargs):
    params=None
    if 'uri' in kwargs:
        uri=kwargs['uri']
    else:
        for arg in args:
            if isinstance(arg, str) or isinstance(arg, str):
                uri = arg
    if 'params' in kwargs:
        params=kwargs['params']
    else:
        for arg in args:
            if isinstance(arg, dict):
                params = arg
    r = requests.Request(method='GET', url=uri, params=params)
    r = r.prepare()
    if not XML_DICT:
        raise Exception("You need to update genologics.test_utils.XML_DICT before using this function")
    try:
        return ElementTree.fromstring(XML_DICT[r.url])
    except KeyError:
        raise Exception("Cannot find mocked xml for uri {0}".format(r.url))

def dump_source_xml(lims):
    """After using a LIMS object, using this method on it will dump all the cached XML in a serialized dictionnary form,
    to be used with patched_get"""
    final_string = []
    final_string.append('{')
    for k, v in lims.cache.items():
        final_string.append("'{0}':".format(k))
        v.get()
        final_string.append('"""{0}""",'.format(v.xml().replace('\n', "\n")))
    final_string.append('}')

    return '\n'.join(final_string)
