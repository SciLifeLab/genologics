
from sys import version_info
from unittest import TestCase, main

from genologics import test_utils
from genologics.lims import Lims
from genologics.entities import Project

if version_info[0] == 2:
    from mock import patch
else:
    from unittest.mock import patch



test_utils.XML_DICT={"https://test.claritylims.com/api/v2/projects/BLA1":"""
<prj:project xmlns:udf="http://genologics.com/ri/userdefined" xmlns:ri="http://genologics.com/ri" xmlns:file="http://genologics.com/ri/file" xmlns:prj="http://genologics.com/ri/project" uri="https://test.claritylims.com/api/v2/projects/BLA1" limsid="BLA1">
<name>Test</name>
<open-date>2016-04-20</open-date>
<close-date>2016-08-09</close-date>
<researcher uri="https://test.claritylims.com/api/v2/researchers/7"/>
<file:file limsid="40-1" uri="https://test.claritylims.com/api/v2/files/40-1"/>
<file:file limsid="40-4264" uri="https://test.claritylims.com/api/v2/files/40-4264"/>
</prj:project>"""}

class TestExample(TestCase):
    def __init__(self, *args, **kwargs):
        self.lims = Lims('https://test.claritylims.com', 'user', 'password')
        super(TestExample, self).__init__(*args, **kwargs)

    def test_project_example(self):
        with patch("genologics.lims.Lims.get", side_effect=test_utils.patched_get):
            pj = Project(self.lims, id='BLA1')
            self.assertEqual(pj.name, 'Test')


if __name__ == '__main__':
    main()

