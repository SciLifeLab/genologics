from io import BytesIO
from sys import version_info
from unittest import TestCase
from xml.etree import ElementTree

from genologics.descriptors import StringDescriptor, StringAttributeDescriptor, StringListDescriptor, \
    StringDictionaryDescriptor, IntegerDescriptor, BooleanDescriptor, UdfDictionary, EntityDescriptor, \
    InputOutputMapList, EntityListDescriptor
from genologics.entities import Artifact, Process
from genologics.lims import Lims

if version_info[0] == 2:
    from mock import Mock
else:
    from unittest.mock import Mock


class TestDescriptor(TestCase):
    def _make_desc(self, klass, *args, **kwargs):
        return klass(*args, **kwargs)

    def _tostring(self, e):
        outfile = BytesIO()
        ElementTree.ElementTree(e).write(outfile, encoding='utf-8', xml_declaration=True)
        return outfile.getvalue()

def print_etree(etree):
    import sys
    outfile = BytesIO()
    ElementTree.ElementTree(etree).write(outfile, encoding='utf-8', xml_declaration=True)
    sys.stdout.buffer.write(outfile.getvalue())

class TestStringDescriptor(TestDescriptor):
    def setUp(self):
        self.et = ElementTree.fromstring("""<?xml version="1.0" encoding="utf-8"?>
<test-entry>
<name>test name</name>
</test-entry>
""")
        self.instance = Mock(root=self.et)

    def test__get__(self):
        sd = self._make_desc(StringDescriptor, 'name')
        assert sd.__get__(self.instance, None) == "test name"

    def test__set__(self):
        sd = self._make_desc(StringDescriptor, 'name')
        sd.__set__(self.instance, "new test name")
        assert self.et.find('name').text == "new test name"

    def test_create(self):
        instance_new = Mock(root=ElementTree.Element('test-entry'))
        sd = self._make_desc(StringDescriptor, 'name')
        sd.__set__(instance_new, "test name")
        assert instance_new.root.find('name').text == 'test name'


class TestIntegerDescriptor(TestDescriptor):
    def setUp(self):
        self.et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry>
<count>32</count>
</test-entry>
""")
        self.instance = Mock(root=self.et)

    def test__get__(self):
        sd = self._make_desc(IntegerDescriptor, 'count')
        assert sd.__get__(self.instance, None) == 32

    def test__set__(self):
        sd = self._make_desc(IntegerDescriptor, 'count')
        sd.__set__(self.instance, 23)
        assert self.et.find('count').text == '23'
        sd.__set__(self.instance, '23')
        assert self.et.find('count').text == '23'

    def test_create(self):
        instance_new = Mock(root=ElementTree.Element('test-entry'))
        sd = self._make_desc(IntegerDescriptor, 'count')
        sd.__set__(instance_new, 23)
        assert instance_new.root.find('count').text == '23'


class TestBooleanDescriptor(TestDescriptor):
    def setUp(self):
        self.et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry>
<istest>true</istest>
</test-entry>
""")
        self.instance = Mock(root=self.et)

    def test__get__(self):
        bd = self._make_desc(BooleanDescriptor, 'istest')
        assert bd.__get__(self.instance, None) == True

    def test__set__(self):
        bd = self._make_desc(BooleanDescriptor, 'istest')
        bd.__set__(self.instance, False)
        assert self.et.find('istest').text == 'false'
        bd.__set__(self.instance, 'true')
        assert self.et.find('istest').text == 'true'

    def test_create(self):
        instance_new = Mock(root=ElementTree.Element('test-entry'))
        bd = self._make_desc(BooleanDescriptor, 'istest')
        bd.__set__(instance_new, True)
        assert instance_new.root.find('istest').text == 'true'


class TestEntityDescriptor(TestDescriptor):
    def setUp(self):
        self.et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry>
<artifact uri="http://testgenologics.com:4040/api/v2/artifacts/a1"></artifact>
</test-entry>
""")
        self.lims = Lims('http://testgenologics.com:4040', username='test', password='password')
        self.a1 = Artifact(self.lims, id='a1')
        self.a2 = Artifact(self.lims, id='a2')
        self.instance = Mock(root=self.et, lims=self.lims)

    def test__get__(self):
        ed = self._make_desc(EntityDescriptor, 'artifact', Artifact)
        assert ed.__get__(self.instance, None) == self.a1

    def test__set__(self):
        ed = self._make_desc(EntityDescriptor, 'artifact', Artifact)
        ed.__set__(self.instance, self.a2)
        assert self.et.find('artifact').attrib['uri'] == 'http://testgenologics.com:4040/api/v2/artifacts/a2'

    def test_create(self):
        instance_new = Mock(root=ElementTree.Element('test-entry'))
        ed = self._make_desc(EntityDescriptor, 'artifact', Artifact)
        ed.__set__(instance_new, self.a1)
        assert instance_new.root.find('artifact').attrib['uri'] == 'http://testgenologics.com:4040/api/v2/artifacts/a1'

class TestEntityListDescriptor(TestDescriptor):
    def setUp(self):
        et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry>
<artifact uri="http://testgenologics.com:4040/api/v2/artifacts/a1"></artifact>
<artifact uri="http://testgenologics.com:4040/api/v2/artifacts/a2"></artifact>
</test-entry>
""")
        self.lims = Lims('http://testgenologics.com:4040', username='test', password='password')
        self.a1 = Artifact(self.lims, id='a1')
        self.a2 = Artifact(self.lims, id='a2')
        self.instance1 = Mock(root=et, lims=self.lims)
        et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry>
<nesting>
<artifact uri="http://testgenologics.com:4040/api/v2/artifacts/a1"></artifact>
<artifact uri="http://testgenologics.com:4040/api/v2/artifacts/a2"></artifact>
</nesting>
</test-entry>
        """)
        self.instance2 = Mock(root=et, lims=self.lims)

    def test__get__(self):
        ed = self._make_desc(EntityListDescriptor, 'artifact', Artifact)
        assert ed.__get__(self.instance1, None) == [self.a1, self.a2]
        ed = self._make_desc(EntityListDescriptor, 'artifact', Artifact, nesting=['nesting'])
        assert ed.__get__(self.instance2, None) == [self.a1, self.a2]


class TestStringAttributeDescriptor(TestDescriptor):
    def setUp(self):
        self.et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry name="test name">
</test-entry>""")
        self.instance = Mock(root=self.et)

    def test__get__(self):
        sd = self._make_desc(StringAttributeDescriptor, 'name')
        assert sd.__get__(self.instance, None) == "test name"

    def test__set__(self):
        sd = self._make_desc(StringAttributeDescriptor, 'name')
        sd.__set__(self.instance, "test name2")
        assert self.et.attrib['name'] == "test name2"

    def test_create(self):
        instance_new = Mock(root=ElementTree.Element('test-entry'))
        bd = self._make_desc(StringAttributeDescriptor, 'name')
        bd.__set__(instance_new, "test name2")
        assert instance_new.root.attrib['name'] == "test name2"


class TestStringListDescriptor(TestDescriptor):
    def setUp(self):
        et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry>
<test-subentry>A01</test-subentry>
<test-subentry>B01</test-subentry>
</test-entry>""")
        self.instance1 = Mock(root=et)
        et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry>
<nesting>
<test-subentry>A01</test-subentry>
<test-subentry>B01</test-subentry>
</nesting>
</test-entry>""")
        self.instance2 = Mock(root=et)

    def test__get__(self):
        sd = self._make_desc(StringListDescriptor, 'test-subentry')
        assert sd.__get__(self.instance1, None) == ['A01', 'B01']
        sd = self._make_desc(StringListDescriptor, 'test-subentry', nesting=['nesting'])
        assert sd.__get__(self.instance2, None) == ['A01', 'B01']


class TestStringDictionaryDescriptor(TestDescriptor):
    def setUp(self):
        et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry>
<test-subentry>
<test-firstkey/>
<test-secondkey>second value</test-secondkey>
</test-subentry>
</test-entry>""")
        self.instance = Mock(root=et)
        et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry>
<test-subentry>
<test-firstkey/>
<test-secondkey>second value</test-secondkey>
</test-subentry>
</test-entry>""")
        self.instance = Mock(root=et)

    def test__get__(self):
        sd = self._make_desc(StringDictionaryDescriptor, 'test-subentry')
        res = sd.__get__(self.instance, None)
        assert type(res) == dict
        assert res['test-firstkey'] is None
        assert res['test-secondkey'] == 'second value'


class TestUdfDictionary(TestCase):
    def setUp(self):
        et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry xmlns:udf="http://genologics.com/ri/userdefined">
<udf:field type="String" name="test">stuff</udf:field>
<udf:field type="Numeric" name="how much">42</udf:field>
<udf:field type="Boolean" name="really?">true</udf:field>
</test-entry>""")
        self.instance1 = Mock(root=et)
        et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry xmlns:udf="http://genologics.com/ri/userdefined">
<nesting>
<udf:field type="String" name="test">stuff</udf:field>
<udf:field type="Numeric" name="how much">42</udf:field>
<udf:field type="Boolean" name="really?">true</udf:field>
</nesting>
</test-entry>""")
        self.instance2 = Mock(root=et)
        self.dict1 = UdfDictionary(self.instance1)
        self.dict2 = UdfDictionary(self.instance2, nesting=['nesting'])
        self.dict_fail = UdfDictionary(self.instance2)

        self.empty_et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <test-entry xmlns:udf="http://genologics.com/ri/userdefined">
        </test-entry>""")

    def _get_udf_value(self, udf_dict, key):
        for e in udf_dict._elems:
            if e.attrib['name'] != key:
                continue
            else:
                return e.text

    def test_get_udt(self):
        pass

    def test_set_udt(self):
        pass

    def test__update_elems(self):
        pass

    def test__prepare_lookup(self):
        pass

    def test___contains__(self):
        pass

    def test___getitem__(self):
        assert self.dict1.__getitem__('test') == self._get_udf_value(self.dict1, 'test')
        assert self.dict2.__getitem__('test') == self._get_udf_value(self.dict2, 'test')
        self.assertRaises(KeyError, self.dict_fail.__getitem__, 'test')

    def test___setitem__(self):
        assert self._get_udf_value(self.dict1, 'test') == 'stuff'
        self.dict1.__setitem__('test', 'other')
        assert self._get_udf_value(self.dict1, 'test') == 'other'

        assert self._get_udf_value(self.dict1, 'how much') == '42'
        self.dict1.__setitem__('how much', 21)
        assert self._get_udf_value(self.dict1, 'how much') == '21'

        assert self._get_udf_value(self.dict1, 'really?') == 'true'
        self.dict1.__setitem__('really?', False)
        assert self._get_udf_value(self.dict1, 'really?') == 'false'

        self.assertRaises(TypeError, self.dict1.__setitem__, 'how much', '433')

        # FIXME: I'm not sure if this is the expected behaviour
        self.dict1.__setitem__('how much', None)
        assert self._get_udf_value(self.dict1, 'how much') == b'None'

        assert self._get_udf_value(self.dict2, 'test') == 'stuff'
        self.dict2.__setitem__('test', 'other')
        assert self._get_udf_value(self.dict2, 'test') == 'other'


    def test___setitem__new(self):
        self.dict1.__setitem__('new string', 'new stuff')
        assert self._get_udf_value(self.dict1, 'new string') == 'new stuff'

        self.dict1.__setitem__('new numeric', 21)
        assert self._get_udf_value(self.dict1, 'new numeric') == '21'

        self.dict1.__setitem__('new bool', False)
        assert self._get_udf_value(self.dict1, 'new bool') == 'false'

        self.dict2.__setitem__('new string', 'new stuff')
        assert self._get_udf_value(self.dict2, 'new string') == 'new stuff'


    def test___setitem__unicode(self):
        assert self._get_udf_value(self.dict1, 'test') == 'stuff'
        self.dict1.__setitem__('test', u'unicode')
        assert self._get_udf_value(self.dict1, 'test') == 'unicode'

        self.dict1.__setitem__(u'test', 'unicode2')
        assert self._get_udf_value(self.dict1, 'test') == 'unicode2'

    def test_create(self):
        instance = Mock(root=self.empty_et)
        dict1 = UdfDictionary(instance)
        dict1['test'] = 'value1'
        assert self._get_udf_value(dict1, 'test') == 'value1'

    def test_create_with_nesting(self):
        instance = Mock(root=self.empty_et)
        dict1 = UdfDictionary(instance, nesting=['cocoon'])
        dict1['test'] = 'value1'
        assert self._get_udf_value(dict1, 'test') == 'value1'

    def test___delitem__(self):
        pass

    def test_items(self):
        pass

    def test_clear(self):
        pass

    def test___iter__(self):
        pass

    def test___next__(self):
        pass

    def test_get(self):
        pass



class TestInputOutputMapList(TestCase):
    def setUp(self):
        et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry xmlns:udf="http://genologics.com/ri/userdefined">
<input-output-map>
<input uri="http://testgenologics.com:4040/api/v2/artifacts/1" limsid="1">
<parent-process uri="http://testgenologics.com:4040//api/v2/processes/1" limsid="1"/>
</input>
<output uri="http://testgenologics.com:4040/api/v2/artifacts/2" output-generation-type="PerAllInputs" output-type="ResultFile" limsid="2"/>
</input-output-map>
</test-entry>""")
        self.instance1 = Mock(root=et, lims=Mock(cache={}))
        self.IO_map = InputOutputMapList()

    def test___get__(self):
        expected_keys_input  = ['limsid', 'parent-process','uri']
        expected_keys_ouput  = ['limsid', 'output-type', 'output-generation-type', 'uri']
        res = self.IO_map.__get__(self.instance1, None)
        assert sorted(res[0][0].keys()) == sorted(expected_keys_input)
        assert sorted(res[0][1].keys()) == sorted(expected_keys_ouput)