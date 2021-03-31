"""Python interface to GenoLogics LIMS via its REST API.

Usage example: Get labs and lab info.



Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
"""

import codecs
from genologics.lims import *

# Login parameters for connecting to a LIMS instance.
from genologics.config import BASEURI, USERNAME, PASSWORD

# Create the LIMS interface instance, and check the connection and version.
lims = Lims(BASEURI, USERNAME, PASSWORD)
lims.check_version()

# Get the list of all projects.
labs = lims.get_labs(name='SciLifeLab')
print(len(labs), 'labs in total')
for lab in labs:
    print(lab, id(lab), lab.name, lab.uri, lab.id)
    print(list(lab.shipping_address.items()))
    for key, value in list(lab.udf.items()):
        if isinstance(value, str):
            value = codecs.encode(value, 'UTF-8')
        print(' ', key, '=', value)
    udt = lab.udt
    if udt:
        print('UDT:', udt.udt)
        for key, value in list(udt.items()):
            if isinstance(value, str):
                value = codecs.encode(value, 'UTF-8')
            print(' ', key, '=', value)

lab = Lab(lims, id='2')
print(lab, id(lab), lab.name, lab.uri, lab.id)
