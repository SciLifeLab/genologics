"""Python interface to GenoLogics LIMS via its REST API.

Example usage: Set the name and a UDF of a sample.



Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
"""

# Login parameters for connecting to a LIMS instance.
from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.lims import Lims, Sample

# Create the LIMS interface instance, and check the connection and version.
lims = Lims(BASEURI, USERNAME, PASSWORD)
lims.check_version()

# Get the sample with the given LIMS identifier, and output its current name.
sample = Sample(lims, id="JGR58A21")
print(sample, sample.name)

sample.name = "Joels extra-proper sample-20"

# Set the value of one of the UDFs
sample.udf["Emmas field 2"] = 5
for key, value in sample.udf.items():
    print(" ", key, "=", value)

sample.put()
print("Updated sample", sample)
