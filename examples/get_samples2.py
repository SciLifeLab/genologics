"""Python interface to GenoLogics LIMS via its REST API.

Usage examples: Get some samples, and sample info.



Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
"""

from genologics.lims import *

from genologics.config import BASEURI, USERNAME, PASSWORD
lims = Lims(BASEURI, USERNAME, PASSWORD)
lims.check_version()

project = Project(lims, id='KRA61')
samples = lims.get_samples(projectlimsid=project.id)
print(len(samples), 'samples in', project)

for sample in samples:
    print(sample, sample.name, sample.date_received, sample.artifact)

name = 'spruce_a'
artifacts = lims.get_artifacts(sample_name=name)
print(len(artifacts), 'artifacts for sample', name)
for artifact in artifacts:
    print(artifact, artifact.name, artifact.qc_flag)
