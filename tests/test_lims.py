import xml
from unittest import TestCase

from requests.exceptions import HTTPError

from genologics.lims import Lims
try:
    callable(1)
except NameError: # callable() doesn't exist in Python 3.0 and 3.1
    import collections
    callable = lambda obj: isinstance(obj, collections.Callable)


from sys import version_info
if version_info[0] == 2:
    from mock import patch, Mock
    import builtins as builtins
else:
    from unittest.mock import patch, Mock
    import builtins

class TestLims(TestCase):
    url = 'http://testgenologics.com:4040'
    username = 'test'
    password = 'password'
    sample_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<smp:samples xmlns:smp="http://genologics.com/ri/sample">
    <sample uri="{url}/api/v2/samples/test_sample" limsid="test_id"/>
</smp:samples>
""".format(url=url)
    error_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<exc:exception xmlns:exc="http://genologics.com/ri/exception">
    <message>Generic error message</message>
</exc:exception>"""
    error_no_msg_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<exc:exception xmlns:exc="http://genologics.com/ri/exception">
</exc:exception>"""


    def test_get_uri(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        assert lims.get_uri('artifacts',sample_name='test_sample') == '{url}/api/v2/artifacts?sample_name=test_sample'.format(url=self.url)


    def test_parse_response(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        r = Mock(content = self.sample_xml, status_code=200)
        pr = lims.parse_response(r)
        assert pr is not None
        assert callable(pr.find)
        assert hasattr(pr.attrib, '__getitem__')

        r = Mock(content = self.error_xml, status_code=400)
        self.assertRaises(HTTPError, lims.parse_response, r)

        r = Mock(content = self.error_no_msg_xml, status_code=400)
        self.assertRaises(HTTPError, lims.parse_response, r)


    @patch('requests.Session.get',return_value=Mock(content = sample_xml, status_code=200))
    def test_get(self, mocked_instance):
        lims = Lims(self.url, username=self.username, password=self.password)
        r = lims.get('{url}/api/v2/artifacts?sample_name=test_sample'.format(url=self.url))
        assert r is not None
        assert callable(r.find)
        assert hasattr(r.attrib, '__getitem__')
        assert mocked_instance.call_count == 1
        mocked_instance.assert_called_with('http://testgenologics.com:4040/api/v2/artifacts?sample_name=test_sample', timeout=16,
                                  headers={'accept': 'application/xml'}, params={}, auth=('test', 'password'))

    def test_put(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        uri = '{url}/api/v2/samples/test_sample'.format(url=self.url)
        with patch('requests.put', return_value=Mock(content = self.sample_xml, status_code=200)) as mocked_put:
            response = lims.put(uri=uri, data=self.sample_xml)
            assert mocked_put.call_count == 1
        with patch('requests.put', return_value=Mock(content = self.error_xml, status_code=400)) as mocked_put:
            self.assertRaises(HTTPError, lims.put, uri=uri, data=self.sample_xml)
            assert mocked_put.call_count == 1


    def test_post(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        uri = '{url}/api/v2/samples'.format(url=self.url)
        with patch('requests.post', return_value=Mock(content = self.sample_xml, status_code=200)) as mocked_put:
            response = lims.post(uri=uri, data=self.sample_xml)
            assert mocked_put.call_count == 1
        with patch('requests.post', return_value=Mock(content = self.error_xml, status_code=400)) as mocked_put:
            self.assertRaises(HTTPError, lims.post, uri=uri, data=self.sample_xml)
            assert mocked_put.call_count == 1


    @patch('os.path.isfile', return_value=True)
    @patch.object(builtins, 'open')
    def test_upload_new_file(self, mocked_open, mocked_isfile):
        lims = Lims(self.url, username=self.username, password=self.password)
        xml_intro = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>"""
        file_start = """<file:file xmlns:file="http://genologics.com/ri/file">"""
        file_start2 = """<file:file xmlns:file="http://genologics.com/ri/file" uri="{url}/api/v2/files/40-3501" limsid="40-3501">"""
        attached = """    <attached-to>{url}/api/v2/samples/test_sample</attached-to>"""
        upload = """    <original-location>filename_to_upload</original-location>"""
        content_loc = """    <content-location>sftp://{url}/opt/gls/clarity/users/glsftp/clarity/samples/test_sample/test</content-location>"""
        file_end = """</file:file>"""
        glsstorage_xml = '\n'.join([xml_intro,file_start, attached, upload, content_loc, file_end]).format(url=self.url)
        file_post_xml = '\n'.join([xml_intro, file_start2, attached, upload, content_loc, file_end]).format(url=self.url)
        with patch('requests.post', side_effect=[Mock(content=glsstorage_xml, status_code=200),
                                                 Mock(content=file_post_xml, status_code=200),
                                                 Mock(content="", status_code=200)]):

            file = lims.upload_new_file(Mock(uri=self.url+"/api/v2/samples/test_sample"),
                                        'filename_to_upload')
            assert file.id == "40-3501"

        with patch('requests.post', side_effect=[Mock(content=self.error_xml, status_code=400)]):

          self.assertRaises(HTTPError,
                            lims.upload_new_file,
                            Mock(uri=self.url+"/api/v2/samples/test_sample"),
                            'filename_to_upload')

    @patch('requests.post', return_value=Mock(content = sample_xml, status_code=200))
    def test_route_artifact(self, mocked_post):
        lims = Lims(self.url, username=self.username, password=self.password)
        artifact = Mock(uri=self.url+"/artifact/2")
        lims.route_artifacts(artifact_list=[artifact], workflow_uri=self.url+'/api/v2/configuration/workflows/1')
        assert mocked_post.call_count == 1



    def test_tostring(self):
        lims = Lims(self.url, username=self.username, password=self.password)
        from xml.etree import ElementTree as ET
        a = ET.Element('a')
        b = ET.SubElement(a, 'b')
        c = ET.SubElement(a, 'c')
        d = ET.SubElement(c, 'd')
        etree = ET.ElementTree(a)
        expected_string=b"""<?xml version='1.0' encoding='utf-8'?>
<a><b /><c><d /></c></a>"""
        string = lims.tostring(etree)
        assert string == expected_string



