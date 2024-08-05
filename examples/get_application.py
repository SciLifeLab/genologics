"""Python interface to GenoLogics LIMS via its REST API.

Usage example: Attach customer delivery report to LIMS



Roman Valls Guimera, Science for Life Laboratory, Stockholm, Sweden.
"""

from pprint import pprint

# Login parameters for connecting to a LIMS instance.
from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.lims import Lims, Project

# Create the LIMS interface instance, and check the connection and version.
lims = Lims(BASEURI, USERNAME, PASSWORD)
lims.check_version()

project = Project(lims, id="P193")

print("UDFs:")
pprint(list(project.udf.items()))

print(project.udf["Application"])
