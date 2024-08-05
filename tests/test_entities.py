from unittest import TestCase
from unittest.mock import Mock, patch
from xml.etree import ElementTree

from genologics.entities import (
    Artifact,
    Container,
    Project,
    ReagentKit,
    ReagentLot,
    Researcher,
    Sample,
    Stage,
    Step,
    StepActions,
    StepPlacements,
    StepPools,
)
from genologics.lims import Lims

url = "http://testgenologics.com:4040"

########
# Entities in XML
generic_artifact_xml = """<?xml version='1.0' encoding='utf-8'?>
<art:artifact xmlns:art="http://genologics.com/ri/artifact"  xmlns:file="http://genologics.com/ri/file" xmlns:udf="http://genologics.com/ri/userdefined"  uri="{url}/api/v2/artifacts/a1" limsid="a1">
<name>test_sample1</name>
<type>Analyte</type>
<output-type>Analyte</output-type>
<qc-flag>PASSED</qc-flag>
<location>
  <container uri="{url}/api/v2/containers/c1" limsid="c1"/>
  <value>A:1</value>
</location>
<working-flag>true</working-flag>
<sample uri="{url}/api/v2/samples/s1" limsid="s1"/>
<udf:field type="Numeric" name="Ave. Conc. (ng/uL)">1</udf:field>
<udf:field type="String" name="Workflow Desired">TruSeq Nano DNA Sample Prep</udf:field>
<workflow-stages>
<workflow-stage status="QUEUED" name="Test workflow s2" uri="{url}/api/v2/configuration/workflows/1/stages/2"/>
<workflow-stage status="COMPLETE" name="Test workflow s1" uri="{url}/api/v2/configuration/workflows/1/stages/1"/>
</workflow-stages>
</art:artifact>"""

generic_step_pools_xml = """<?xml version='1.0' encoding='utf-8'?>
<stp:pools xmlns:stp="http://genologics.com/ri/step" uri="{url}/steps/s1/pools">
<step uri="{url}/api/v2/steps/122-28760" rel="steps"/>
<configuration uri="{url}/api/v2/configuration/protocols/467/steps/619">
Step name
</configuration>
<pooled-inputs>
<pool output-uri="{url}/api/v2/artifacts/o1" name="Pool #1">
<input uri="{url}/api/v2/artifacts/a1"/>
<input uri="{url}/api/v2/artifacts/a2"/>
</pool>
</pooled-inputs>
<available-inputs>
<input replicates="1" uri="{url}/api/v2/artifacts/a3"/>
<input replicates="1" uri="{url}/api/v2/artifacts/a4"/>
<input replicates="1" uri="{url}/api/v2/artifacts/a5"/>
</available-inputs>
</stp:pools>
"""
generic_step_placements_xml = """<?xml version='1.0' encoding='utf-8'?>
<stp:placements xmlns:stp="http://genologics.com/ri/step" uri="{url}/steps/s1/placements">
  <step uri="{url}/steps/s1" />
  <configuration uri="{url}/configuration/protocols/1/steps/1">Step name</configuration>
  <selected-containers>
    <container uri="{url}/containers/{container}" />
  </selected-containers>
  <output-placements>
    <output-placement uri="{url}/artifacts/a1">
      <location>
        <container limsid="{container}" uri="{url}/containers/{container}" />
        <value>{loc1}</value>
      </location>
    </output-placement>
    <output-placement uri="{url}/artifacts/a2">
      <location>
        <container limsid="{container}" uri="{url}/containers/{container}" />
        <value>{loc2}</value>
      </location>
    </output-placement>
  </output-placements>
</stp:placements>"""

generic_reagentkit_xml = """<?xml version='1.0' encoding='utf-8'?>
<kit:reagent-kit xmlns:kit="http://genologics.com/ri/reagentkit" uri="{url}:8080/api/v2/reagentkits/r1">
<name>regaentkitname</name>
<supplier>reagentProvider</supplier>
<website>www.reagentprovider.com</website>
<archived>false</archived>
</kit:reagent-kit>"""

generic_reagentlot_xml = """<?xml version='1.0' encoding='utf-8'?>
<lot:reagent-lot xmlns:lot="http://genologics.com/ri/reagentlot" limsid="l1" uri="{url}/api/v2/reagentlots/l1">
<reagent-kit uri="{url}/api/v2/reagentkits/r1" name="kitname"/>
<name>kitname</name>
<lot-number>100</lot-number>
<created-date>2015-07-16</created-date>
<last-modified-date>2015-08-17</last-modified-date>
<expiry-date>2022-08-16</expiry-date>
<created-by uri="{url}/api/v2/researchers/1"/>
<last-modified-by uri="{url}/api/v2/researchers/1"/>
<status>ARCHIVED</status>
<usage-count>1</usage-count>
</lot:reagent-lot>"""

generic_step_actions_xml = """<stp:actions xmlns:stp="http://genologics.com/ri/step" uri="...">
  <step rel="..." uri="{url}/steps/s1">
  </step>
  <configuration uri="{url}/config/1">...</configuration>
  <next-actions>
    <next-action artifact-uri="{url}/artifacts/a1" action="requeue" step-uri="..." rework-step-uri="...">
    </next-action>
  </next-actions>
  <escalation>
    <request>
      <author uri="{url}/researchers/r1">
        <first-name>foo</first-name>
        <last-name>bar</last-name>
      </author>
      <reviewer uri="{url}/researchers/r1">
        <first-name>foo</first-name>
        <last-name>bar</last-name>
      </reviewer>
      <date>01-01-1970</date>
      <comment>no comments</comment>
    </request>
    <review>
      <author uri="{url}/researchers/r1">
        <first-name>foo</first-name>
        <last-name>bar</last-name>
      </author>
      <date>01-01-1970</date>
      <comment>no comments</comment>
    </review>
    <escalated-artifacts>
      <escalated-artifact uri="{url}/artifacts/r1">
      </escalated-artifact>
    </escalated-artifacts>
  </escalation>
</stp:actions>"""

generic_step_actions_no_escalation_xml = """<stp:actions xmlns:stp="http://genologics.com/ri/step" uri="...">
  <step rel="..." uri="{url}/steps/s1">
  </step>
  <configuration uri="{url}/config/1">...</configuration>
  <next-actions>
    <next-action artifact-uri="{url}/artifacts/a1" action="requeue" step-uri="{url}/steps/s1" rework-step-uri="{url}/steps/s2">
    </next-action>
  </next-actions>
</stp:actions>"""

generic_sample_creation_xml = """
<smp:samplecreation xmlns:smp="http://genologics.com/ri/sample" limsid="s1" uri="{url}/api/v2/samples/s1">
  <location>
    <container limsid="cont1" uri="{url}/api/v2/containers/cont1">
    </container>
    <value>1:1</value>
  </location>
  <name>
    sample1
  </name>
  <project uri="{url}/api/v2/projects/p1" limsid="p1">
  </project>
</smp:samplecreation>
"""


def elements_equal(e1, e2):
    if e1.tag != e2.tag:
        print(f"Tag: {e1.tag} != {e2.tag}")
        return False
    if e1.text and e2.text and e1.text.strip() != e2.text.strip():
        print(f"Text: {e1.text.strip()} != {e2.text.strip()}")
        return False
    if e1.tail and e2.tail and e1.tail.strip() != e2.tail.strip():
        print(f"Tail: {e1.tail.strip()} != {e2.tail.strip()}")
        return False
    if e1.attrib != e2.attrib:
        print(f"Attrib: {e1.attrib} != {e2.attrib}")
        return False
    if len(e1) != len(e2):
        print(f"length {e1.tag} ({len(e1)}) != length ({e2.tag}) ")
        return False
    return all(
        elements_equal(c1, c2)
        for c1, c2 in zip(
            sorted(e1, key=lambda x: x.tag), sorted(e2, key=lambda x: x.tag)
        )
    )


class TestEntities(TestCase):
    dummy_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <dummy></dummy>"""

    def setUp(self):
        self.lims = Lims(url, username="test", password="password")

    def _tostring(self, entity):
        return self.lims.tostring(ElementTree.ElementTree(entity.root)).decode("utf-8")


class TestStepActions(TestEntities):
    step_actions_xml = generic_step_actions_xml.format(url=url)
    step_actions_no_escalation_xml = generic_step_actions_no_escalation_xml.format(
        url=url
    )

    def test_escalation(self):
        s = StepActions(
            uri=self.lims.get_uri("steps", "step_id", "actions"), lims=self.lims
        )
        with patch(
            "requests.Session.get",
            return_value=Mock(content=self.step_actions_xml, status_code=200),
        ):
            with patch(
                "requests.post",
                return_value=Mock(content=self.dummy_xml, status_code=200),
            ):
                r = Researcher(
                    uri="http://testgenologics.com:4040/researchers/r1", lims=self.lims
                )
                a = Artifact(
                    uri="http://testgenologics.com:4040/artifacts/r1", lims=self.lims
                )
                expected_escalation = {
                    "status": "Reviewed",
                    "author": r,
                    "artifacts": [a],
                    "request": "no comments",
                    "answer": "no comments",
                    "reviewer": r,
                }

                assert s.escalation == expected_escalation

    def test_next_actions(self):
        s = StepActions(
            uri=self.lims.get_uri("steps", "step_id", "actions"), lims=self.lims
        )
        with patch(
            "requests.Session.get",
            return_value=Mock(
                content=self.step_actions_no_escalation_xml, status_code=200
            ),
        ):
            step1 = Step(self.lims, uri="http://testgenologics.com:4040/steps/s1")
            step2 = Step(self.lims, uri="http://testgenologics.com:4040/steps/s2")
            artifact = Artifact(
                self.lims, uri="http://testgenologics.com:4040/artifacts/a1"
            )
            expected_next_actions = [
                {
                    "artifact": artifact,
                    "action": "requeue",
                    "step": step1,
                    "rework-step": step2,
                }
            ]
            assert s.next_actions == expected_next_actions


class TestStepPools(TestEntities):
    initial_step_pools = generic_step_pools_xml.format(url=url)

    def test_get_pool_list(self):
        s = StepPools(uri=self.lims.get_uri("steps", "s1", "pools"), lims=self.lims)
        with patch(
            "requests.Session.get",
            return_value=Mock(content=self.initial_step_pools, status_code=200),
        ):
            output = Artifact(
                lims=self.lims, uri="http://testgenologics.com:4040/api/v2/artifacts/o1"
            )
            i1 = Artifact(
                lims=self.lims, uri="http://testgenologics.com:4040/api/v2/artifacts/a1"
            )
            i2 = Artifact(
                lims=self.lims, uri="http://testgenologics.com:4040/api/v2/artifacts/a2"
            )
            i3 = Artifact(
                lims=self.lims, uri="http://testgenologics.com:4040/api/v2/artifacts/a3"
            )
            i4 = Artifact(
                lims=self.lims, uri="http://testgenologics.com:4040/api/v2/artifacts/a4"
            )
            i5 = Artifact(
                lims=self.lims, uri="http://testgenologics.com:4040/api/v2/artifacts/a5"
            )
            assert s.pools[0]["output"] == output
            assert s.pools[0]["name"] == "Pool #1"
            assert len(s.pools[0]["inputs"]) == 2
            assert s.pools[0]["inputs"][0] == i1
            assert s.pools[0]["inputs"][1] == i2
            assert i3 in s.available_inputs
            assert i4 in s.available_inputs
            assert i5 in s.available_inputs


class TestStepPlacements(TestEntities):
    original_step_placements_xml = generic_step_placements_xml.format(
        url=url, container="c1", loc1="1:1", loc2="2:1"
    )
    modloc_step_placements_xml = generic_step_placements_xml.format(
        url=url, container="c1", loc1="3:1", loc2="4:1"
    )
    modcont_step_placements_xml = generic_step_placements_xml.format(
        url=url, container="c2", loc1="1:1", loc2="1:1"
    )

    def test_get_placements_list(self):
        s = StepPlacements(
            uri=self.lims.get_uri("steps", "s1", "placements"), lims=self.lims
        )
        with patch(
            "requests.Session.get",
            return_value=Mock(
                content=self.original_step_placements_xml, status_code=200
            ),
        ):
            a1 = Artifact(
                uri="http://testgenologics.com:4040/artifacts/a1", lims=self.lims
            )
            a2 = Artifact(
                uri="http://testgenologics.com:4040/artifacts/a2", lims=self.lims
            )
            c1 = Container(
                uri="http://testgenologics.com:4040/containers/c1", lims=self.lims
            )
            expected_placements = [[a1, (c1, "1:1")], [a2, (c1, "2:1")]]
            assert s.get_placement_list() == expected_placements

    def test_set_placements_list(self):
        a1 = Artifact(uri="http://testgenologics.com:4040/artifacts/a1", lims=self.lims)
        a2 = Artifact(uri="http://testgenologics.com:4040/artifacts/a2", lims=self.lims)
        c1 = Container(
            uri="http://testgenologics.com:4040/containers/c1", lims=self.lims
        )
        Container(uri="http://testgenologics.com:4040/containers/c2", lims=self.lims)

        s = StepPlacements(
            uri=self.lims.get_uri("steps", "s1", "placements"), lims=self.lims
        )
        with patch(
            "requests.Session.get",
            return_value=Mock(
                content=self.original_step_placements_xml, status_code=200
            ),
        ):
            new_placements = [[a1, (c1, "3:1")], [a2, (c1, "4:1")]]
            s.set_placement_list(new_placements)
            assert elements_equal(
                s.root, ElementTree.fromstring(self.modloc_step_placements_xml)
            )

    def test_set_placements_list_fail(self):
        a1 = Artifact(uri="http://testgenologics.com:4040/artifacts/a1", lims=self.lims)
        a2 = Artifact(uri="http://testgenologics.com:4040/artifacts/a2", lims=self.lims)
        c2 = Container(
            uri="http://testgenologics.com:4040/containers/c2", lims=self.lims
        )

        s = StepPlacements(
            uri=self.lims.get_uri("steps", "s1", "placements"), lims=self.lims
        )
        with patch(
            "requests.Session.get",
            return_value=Mock(
                content=self.original_step_placements_xml, status_code=200
            ),
        ):
            new_placements = [[a1, (c2, "1:1")], [a2, (c2, "1:1")]]
            s.set_placement_list(new_placements)
            assert elements_equal(
                s.root, ElementTree.fromstring(self.modcont_step_placements_xml)
            )


class TestArtifacts(TestEntities):
    root_artifact_xml = generic_artifact_xml.format(url=url)

    def test_input_artifact_list(self):
        a = Artifact(uri=self.lims.get_uri("artifacts", "a1"), lims=self.lims)
        with patch(
            "requests.Session.get",
            return_value=Mock(content=self.root_artifact_xml, status_code=200),
        ):
            assert a.input_artifact_list() == []

    def test_workflow_stages_and_statuses(self):
        a = Artifact(uri=self.lims.get_uri("artifacts", "a1"), lims=self.lims)
        expected_wf_stage = [
            (
                Stage(
                    self.lims, uri=url + "/api/v2/configuration/workflows/1/stages/2"
                ),
                "QUEUED",
                "Test workflow s2",
            ),
            (
                Stage(
                    self.lims, uri=url + "/api/v2/configuration/workflows/1/stages/1"
                ),
                "COMPLETE",
                "Test workflow s1",
            ),
        ]
        with patch(
            "requests.Session.get",
            return_value=Mock(content=self.root_artifact_xml, status_code=200),
        ):
            assert a.workflow_stages_and_statuses == expected_wf_stage


class TestReagentKits(TestEntities):
    url = "http://testgenologics.com:4040"
    reagentkit_xml = generic_reagentkit_xml.format(url=url)

    def test_parse_entity(self):
        r = ReagentKit(uri=self.lims.get_uri("reagentkits", "r1"), lims=self.lims)
        with patch(
            "requests.Session.get",
            return_value=Mock(content=self.reagentkit_xml, status_code=200),
        ):
            assert r.name == "regaentkitname"
            assert r.supplier == "reagentProvider"
            assert r.website == "www.reagentprovider.com"
            assert r.archived is False

    def test_create_entity(self):
        with patch(
            "genologics.lims.requests.post",
            return_value=Mock(content=self.reagentkit_xml, status_code=201),
        ):
            ReagentKit.create(
                self.lims,
                name="regaentkitname",
                supplier="reagentProvider",
                website="www.reagentprovider.com",
                archived=False,
            )
        self.assertRaises(TypeError, ReagentKit.create, self.lims, error="test")


class TestReagentLots(TestEntities):
    reagentlot_xml = generic_reagentlot_xml.format(url=url)
    reagentkit_xml = generic_reagentkit_xml.format(url=url)

    def test_parse_entity(self):
        l = ReagentLot(uri=self.lims.get_uri("reagentkits", "r1"), lims=self.lims)
        with patch(
            "requests.Session.get",
            return_value=Mock(content=self.reagentlot_xml, status_code=200),
        ):
            assert l.uri
            assert l.name == "kitname"
            assert l.lot_number == "100"
            assert l.status == "ARCHIVED"

    def test_create_entity(self):
        with patch(
            "requests.Session.get",
            return_value=Mock(content=self.reagentkit_xml, status_code=200),
        ):
            r = ReagentKit(uri=self.lims.get_uri("reagentkits", "r1"), lims=self.lims)
        with patch(
            "genologics.lims.requests.post",
            return_value=Mock(content=self.reagentlot_xml, status_code=201),
        ):
            l = ReagentLot.create(
                self.lims,
                reagent_kit=r,
                name="kitname",
                lot_number="100",
                expiry_date="2020-05-01",
                status="ACTIVE",
            )
            assert l.uri
            assert l.name == "kitname"
            assert l.lot_number == "100"


class TestSample(TestEntities):
    sample_creation = generic_sample_creation_xml.format(url=url)

    def test_create_entity(self):
        with patch(
            "genologics.lims.requests.post",
            return_value=Mock(content=self.sample_creation, status_code=201),
        ) as patch_post:
            Sample.create(
                self.lims,
                project=Project(self.lims, uri="project"),
                container=Container(self.lims, uri="container"),
                position="1:1",
                name="s1",
            )
            data = """<?xml version=\'1.0\' encoding=\'utf-8\'?>
            <smp:samplecreation xmlns:smp="http://genologics.com/ri/sample">
            <name>s1</name>
            <project uri="project" limsid="project" />
            <location>
              <container uri="container" />
              <value>1:1</value>
            </location>
            </smp:samplecreation>"""
            assert elements_equal(
                ElementTree.fromstring(patch_post.call_args_list[0][1]["data"]),
                ElementTree.fromstring(data),
            )
