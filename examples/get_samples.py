"""Python interface to GenoLogics LIMS via its REST API.

Usage examples: Get some samples, and sample info.



Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
"""

from genologics.lims import *

# Login parameters for connecting to a LIMS instance.

from genologics.config import BASEURI, USERNAME, PASSWORD

# Create the LIMS interface instance, and check the connection and version.
lims = Lims(BASEURI, USERNAME, PASSWORD)
lims.check_version()

# Get the list of all samples.
samples = lims.get_samples()
print(len(samples), 'samples in total')

# Get the list of samples in the project with the LIMS id KLL60.
project = Project(lims, id='KRA61')
samples = lims.get_samples(projectlimsid=project.id)
print(len(samples), 'samples in', project)

print()
# Get the sample with the LIMS id KRA61A1
sample = Sample(lims, id='KRA61A1')
print(sample.id, sample.name, sample.date_received, sample.uri, end=' ')
for key, value in list(sample.udf.items()):
    print(' ', key, '=', value)
for note in sample.notes:
    print('Note', note.uri, note.content)
for file in sample.files:
    print('File', file.content_location)

# Get the sample with the name 'spruce_a'.
# Check that it is the sample as the previously obtained sample;
# not just equal, but exactly the same instance, courtesy of the Lims cache.
samples = lims.get_samples(name='spruce_a')
print(samples[0].name, samples[0] is sample)

## # Get the samples having a UDF Color with values Blue or Orange.
samples = lims.get_samples(udf={'Color': ['Blue', 'Orange']})
print(len(samples))
for sample in samples:
    print(sample, sample.name, sample.udf['Color'])

sample = samples[0]

print()
# Print the submitter (researcher) for the sample.
submitter = sample.submitter
print(submitter, submitter.email, submitter.initials, submitter.lab)

print()
# Print the artifact of the sample.
artifact = sample.artifact
print(artifact, artifact.state, artifact.type, artifact.qc_flag)
