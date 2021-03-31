"""Python interface to GenoLogics LIMS via its REST API.

Usage example: Attach customer delivery report to LIMS



Roman Valls Guimera, Science for Life Laboratory, Stockholm, Sweden.
"""

import codecs
from pprint import pprint
from genologics.lims import *

# Login parameters for connecting to a LIMS instance.
from genologics.config import BASEURI, USERNAME, PASSWORD

# Create the LIMS interface instance, and check the connection and version.
lims = Lims(BASEURI, USERNAME, PASSWORD)
lims.check_version()

project = Project(lims, id="P193")

print('UDFs:')
pprint(list(project.udf.items()))

print('files:')
for file in project.files:
    print(file.content_location)

project.udf['Delivery Report'] = "http://example.com/delivery_note.pdf"
project.put()
