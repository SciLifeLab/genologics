from io import BytesIO
from unittest import TestCase
from unittest.mock import Mock
from xml.etree import ElementTree

from genologics.descriptors import (
    BooleanDescriptor,
    EntityDescriptor,
    IntegerDescriptor,
    StringAttributeDescriptor,
    StringDescriptor,
    StringDictionaryDescriptor,
    StringListDescriptor,
    UdfDictionary,
)
from genologics.entities import Artifact
from genologics.lims import Lims


class TestDescriptor(TestCase):
    def _make_desc(self, klass, *args, **kwargs):
        return klass(*args, **kwargs)

    def _tostring(self, e):
        outfile = BytesIO()
        ElementTree.ElementTree(e).write(
            outfile, encoding="utf-8", xml_declaration=True
        )
        return outfile.getvalue()


class TestStringDescriptor(TestDescriptor):
    def setUp(self):
        self.et = ElementTree.fromstring("""<?xml version="1.0" encoding="utf-8"?>
<test-entry>
<name>test name</name>
</test-entry>
""")
        self.instance = Mock(root=self.et)

    def test__get__(self):
        sd = self._make_desc(StringDescriptor, "name")
        assert sd.__get__(self.instance, None) == "test name"

    def test__set__(self):
        sd = self._make_desc(StringDescriptor, "name")
        sd.__set__(self.instance, "new test name")
        assert self.et.find("name").text == "new test name"

    def test_create(self):
        instance_new = Mock(root=ElementTree.Element("test-entry"))
        sd = self._make_desc(StringDescriptor, "name")
        sd.__set__(instance_new, "test name")
        assert instance_new.root.find("name").text == "test name"


class TestIntegerDescriptor(TestDescriptor):
    def setUp(self):
        self.et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry>
<count>32</count>
</test-entry>
""")
        self.instance = Mock(root=self.et)

    def test__get__(self):
        sd = self._make_desc(IntegerDescriptor, "count")
        assert sd.__get__(self.instance, None) == 32

    def test__set__(self):
        sd = self._make_desc(IntegerDescriptor, "count")
        sd.__set__(self.instance, 23)
        assert self.et.find("count").text == "23"
        sd.__set__(self.instance, "23")
        assert self.et.find("count").text == "23"

    def test_create(self):
        instance_new = Mock(root=ElementTree.Element("test-entry"))
        sd = self._make_desc(IntegerDescriptor, "count")
        sd.__set__(instance_new, 23)
        assert instance_new.root.find("count").text == "23"


class TestBooleanDescriptor(TestDescriptor):
    def setUp(self):
        self.et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry>
<istest>true</istest>
</test-entry>
""")
        self.instance = Mock(root=self.et)

    def test__get__(self):
        bd = self._make_desc(BooleanDescriptor, "istest")
        assert bd.__get__(self.instance, None) is True

    def test__set__(self):
        bd = self._make_desc(BooleanDescriptor, "istest")
        bd.__set__(self.instance, False)
        assert self.et.find("istest").text == "false"
        bd.__set__(self.instance, "true")
        assert self.et.find("istest").text == "true"

    def test_create(self):
        instance_new = Mock(root=ElementTree.Element("test-entry"))
        bd = self._make_desc(BooleanDescriptor, "istest")
        bd.__set__(instance_new, True)
        assert instance_new.root.find("istest").text == "true"


class TestEntityDescriptor(TestDescriptor):
    def setUp(self):
        self.et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry>
<artifact uri="http://testgenologics.com:4040/api/v2/artifacts/a1"></artifact>
</test-entry>
""")
        self.lims = Lims(
            "http://testgenologics.com:4040", username="test", password="password"
        )
        self.a1 = Artifact(self.lims, id="a1")
        self.a2 = Artifact(self.lims, id="a2")
        self.instance = Mock(root=self.et, lims=self.lims)

    def test__get__(self):
        ed = self._make_desc(EntityDescriptor, "artifact", Artifact)
        assert ed.__get__(self.instance, None) == self.a1

    def test__set__(self):
        ed = self._make_desc(EntityDescriptor, "artifact", Artifact)
        ed.__set__(self.instance, self.a2)
        assert (
            self.et.find("artifact").attrib["uri"]
            == "http://testgenologics.com:4040/api/v2/artifacts/a2"
        )

    def test_create(self):
        instance_new = Mock(root=ElementTree.Element("test-entry"))
        ed = self._make_desc(EntityDescriptor, "artifact", Artifact)
        ed.__set__(instance_new, self.a1)
        assert (
            instance_new.root.find("artifact").attrib["uri"]
            == "http://testgenologics.com:4040/api/v2/artifacts/a1"
        )


class TestStringAttributeDescriptor(TestDescriptor):
    def setUp(self):
        self.et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry name="test name">
</test-entry>""")
        self.instance = Mock(root=self.et)

    def test__get__(self):
        sd = self._make_desc(StringAttributeDescriptor, "name")
        assert sd.__get__(self.instance, None) == "test name"

    def test__set__(self):
        sd = self._make_desc(StringAttributeDescriptor, "name")
        sd.__set__(self.instance, "test name2")
        assert self.et.attrib["name"] == "test name2"

    def test_create(self):
        instance_new = Mock(root=ElementTree.Element("test-entry"))
        bd = self._make_desc(StringAttributeDescriptor, "name")
        bd.__set__(instance_new, "test name2")
        assert instance_new.root.attrib["name"] == "test name2"


class TestStringListDescriptor(TestDescriptor):
    def setUp(self):
        self.et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry>
<test-subentry>A01</test-subentry>
<test-subentry>B01</test-subentry>
</test-entry>""")
        self.instance = Mock(root=self.et)

    def test__get__(self):
        sd = self._make_desc(StringListDescriptor, "test-subentry")
        assert sd.__get__(self.instance, None) == ["A01", "B01"]


class TestStringDictionaryDescriptor(TestDescriptor):
    def setUp(self):
        self.et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry>
<test-subentry>
<test-firstkey/>
<test-secondkey>second value</test-secondkey>
</test-subentry>
</test-entry>""")
        self.instance = Mock(root=self.et)

    def test__get__(self):
        sd = self._make_desc(StringDictionaryDescriptor, "test-subentry")
        res = sd.__get__(self.instance, None)
        assert isinstance(res, dict)
        assert res["test-firstkey"] is None
        assert res["test-secondkey"] == "second value"


class TestUdfDictionary(TestCase):
    def setUp(self):
        self.et = ElementTree.fromstring("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<test-entry xmlns:udf="http://genologics.com/ri/userdefined">
<udf:field type="String" name="test">stuff</udf:field>
<udf:field type="Numeric" name="how much">42</udf:field>
<udf:field type="Boolean" name="really?">true</udf:field>
</test-entry>""")
        self.instance = Mock(root=self.et)
        self.dict1 = UdfDictionary(self.instance)
        self.dict2 = UdfDictionary(self.instance, udt=True)

    def _get_udf_value(self, udf_dict, key):
        for e in udf_dict._elems:
            if e.attrib["name"] != key:
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
        pass

    def test___setitem__(self):
        assert self._get_udf_value(self.dict1, "test") == "stuff"
        self.dict1.__setitem__("test", "other")
        assert self._get_udf_value(self.dict1, "test") == "other"

        assert self._get_udf_value(self.dict1, "how much") == "42"
        self.dict1.__setitem__("how much", 21)
        assert self._get_udf_value(self.dict1, "how much") == "21"

        assert self._get_udf_value(self.dict1, "really?") == "true"
        self.dict1.__setitem__("really?", False)
        assert self._get_udf_value(self.dict1, "really?") == "false"

        self.assertRaises(TypeError, self.dict1.__setitem__, "how much", "433")

        # FIXME: I'm not sure if this is the expected behaviour
        self.dict1.__setitem__("how much", None)
        assert self._get_udf_value(self.dict1, "how much") == ""

    def test___setitem__new(self):
        self.dict1.__setitem__("new string", "new stuff")
        assert self._get_udf_value(self.dict1, "new string") == "new stuff"

        self.dict1.__setitem__("new numeric", 21)
        assert self._get_udf_value(self.dict1, "new numeric") == "21"

        self.dict1.__setitem__("new bool", False)
        assert self._get_udf_value(self.dict1, "new bool") == "false"

    def test___setitem__unicode(self):
        assert self._get_udf_value(self.dict1, "test") == "stuff"
        self.dict1.__setitem__("test", "unicode")
        assert self._get_udf_value(self.dict1, "test") == "unicode"

        self.dict1.__setitem__("test", "unicode2")
        assert self._get_udf_value(self.dict1, "test") == "unicode2"

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
