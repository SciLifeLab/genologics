from io import BytesIO
from sys import version_info
from unittest import TestCase
from xml.etree import ElementTree

import pytest

from genologics.constants import nsmap
from genologics.descriptors import StringDescriptor, StringAttributeDescriptor, StringListDescriptor, \
    StringDictionaryDescriptor, IntegerDescriptor, BooleanDescriptor, UdfDictionary, EntityDescriptor, \
    InputOutputMapList, EntityListDescriptor, PlacementDictionary, EntityList, SubTagDictionary, ExternalidList
from genologics.entities import Artifact
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

    def test__set__(self):
        sd = self._make_desc(StringListDescriptor, 'test-subentry')
        sd.__set__(self.instance1, ['A02', 'B02'])
        res = sd.__get__(self.instance1, None)
        assert isinstance(res, list)
        assert res == ['A02', 'B02']


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

    def test__get__(self):
        sd = self._make_desc(StringDictionaryDescriptor, 'test-subentry')
        res = sd.__get__(self.instance, None)
        assert isinstance(res, dict)
        assert res['test-firstkey'] is None
        assert res['test-secondkey'] == 'second value'

    def test__set__(self):
        sd = self._make_desc(StringDictionaryDescriptor, 'test-subentry')
        sd.__set__(self.instance, {'mykey1': 'myvalue1'})
        res = sd.__get__(self.instance, None)
        assert isinstance(res, dict)
        assert res['mykey1'] == 'myvalue1'

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
        assert self.dict1['test'] == self._get_udf_value(self.dict1, 'test')
        del self.dict1['test']
        with pytest.raises(KeyError):
            self.dict1['test']
        assert self._get_udf_value(self.dict1, 'test') == None


    def test_items(self):
        pass

    def test_clear(self):
        assert self.dict1
        self.dict1.clear()
        assert not self.dict1
        assert len(self.dict1) == 0

    def test___iter__(self):
        expected_content = [
            ("test", "stuff"),
            ("really?", True),
            ("how much", 42)
        ]
        for k in self.dict1:
            assert (k, self.dict1[k]) in expected_content


class TestPlacementDictionary(TestCase):

    def setUp(self):
        et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry xmlns:udf="http://genologics.com/ri/userdefined">
<placement uri="http://testgenologics.com:4040/api/v2/artifacts/a1" limsid="a1">
<value>A:1</value>
</placement>
</test-entry>""")
        self.lims = Lims('http://testgenologics.com:4040', username='test', password='password')
        self.instance1 = Mock(root=et, lims=self.lims)
        self.dict1 = PlacementDictionary(self.instance1)
        self.art1 = Artifact(lims=self.lims, id='a1')

    def test___getitem__(self):
        assert self.dict1['A:1'] == self.art1

    def test___setitem__(self):
        assert len(self.dict1.rootnode(self.dict1.instance).findall('placement')) == 1
        art2 = Artifact(lims=self.lims, id='a2')
        self.dict1['A:2'] = art2
        assert len(self.dict1.rootnode(self.dict1.instance).findall('placement')) == 2
        assert self.dict1['A:2'] == art2


class TestSubTagDictionary(TestCase):

    def setUp(self):
        et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry xmlns:udf="http://genologics.com/ri/userdefined">
<test-tag>
<key1>value1</key1>
</test-tag>
</test-entry>""")
        self.lims = Lims('http://testgenologics.com:4040', username='test', password='password')
        self.instance1 = Mock(root=et, lims=self.lims)
        self.dict1 = SubTagDictionary(self.instance1, tag='test-tag')

    def test___getitem__(self):
        assert self.dict1['key1'] == 'value1'

    def test___setitem__(self):
        assert len(self.dict1.rootnode(self.dict1.instance).find('test-tag')) == 1
        art2 = Artifact(lims=self.lims, id='a2')
        self.dict1['key2'] = 'value2'
        assert len(self.dict1.rootnode(self.dict1.instance).find('test-tag')) == 2
        assert self.dict1['key2'] == 'value2'


class TestEntityList(TestCase):

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
        el = EntityList(self.instance1, 'artifact', Artifact)
        assert el[0] == self.a1
        assert el[1] == self.a2
        el = EntityList(self.instance2, 'artifact', Artifact, nesting=['nesting'])
        assert el[0] == self.a1
        assert el[1] == self.a2

    def test_append(self):
        el = EntityList(self.instance1, 'artifact', Artifact)
        assert len(el) == 2
        assert len(el.instance.root.findall('artifact')) == 2
        a3 = Artifact(self.lims, id='a3')
        el.append(a3)
        assert len(el) == 3
        assert el[2] == a3
        assert len(el._elems) == 3
        assert len(el.instance.root.findall('artifact')) == 3

    def test_insert(self):
        el = EntityList(self.instance1, 'artifact', Artifact)
        assert len(el) == 2
        assert len(el.instance.root.findall('artifact')) == 2
        a3 = Artifact(self.lims, id='a3')
        el.insert(1, a3)
        assert len(el) == 3
        assert el[1] == a3
        assert len(el._elems) == 3
        assert len(el.instance.root.findall('artifact')) == 3

    def test_set(self):
        el = EntityList(self.instance1, 'artifact', Artifact)
        assert len(el) == 2
        assert len(el.instance.root.findall('artifact')) == 2
        a3 = Artifact(self.lims, id='a3')
        el[1] = a3
        assert len(el) == 2
        assert el[1] == a3
        assert len(el._elems) == 2
        assert el.instance.root.findall('artifact')[1].attrib['uri'] == 'http://testgenologics.com:4040/api/v2/artifacts/a3'


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



class TestExternalidList(TestCase):

    def setUp(self):
        et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <test-entry>
    <ri:externalid xmlns:ri="http://genologics.com/ri" id="1" uri="http://testgenologics.com:4040/api/v2/external/1" />
    <ri:externalid xmlns:ri="http://genologics.com/ri" id="2" uri="http://testgenologics.com:4040/api/v2/external/2" />
    </test-entry>
    """)
        self.lims = Lims('http://testgenologics.com:4040', username='test', password='password')
        self.instance1 = Mock(root=et, lims=self.lims)

    def test_get(self):
        el = ExternalidList(self.instance1)
        assert len(el) == 2
        assert el[0] == ("1", "http://testgenologics.com:4040/api/v2/external/1")
        assert el[1] == ("2", "http://testgenologics.com:4040/api/v2/external/2")

    def test_append(self):
        el = ExternalidList(self.instance1)
        assert len(el) == 2
        el.append(("3", "http://testgenologics.com:4040/api/v2/external/3"))
        assert len(el) == 3
        assert el[2] == ("3", "http://testgenologics.com:4040/api/v2/external/3")
        assert len(el._elems) == 3
        elem = el.instance.root.findall(nsmap('ri:externalid'))
        assert elem[2].attrib['id'] == '3'
        assert elem[2].attrib['uri'] == 'http://testgenologics.com:4040/api/v2/external/3'


