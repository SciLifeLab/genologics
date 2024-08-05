"""Python interface to GenoLogics LIMS via its REST API.

Usage example: Get labs and lab info.



Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
"""

# Login parameters for connecting to a LIMS instance.
from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.lims import Lab, Lims

# Create the LIMS interface instance, and check the connection and version.
lims = Lims(BASEURI, USERNAME, PASSWORD)
lims.check_version()

# Get the list of all projects.
labs = lims.get_labs(name="SciLifeLab")
print(len(labs), "labs in total")
for lab in labs:
    print(lab, id(lab), lab.name, lab.uri, lab.id)
    print(list(lab.shipping_address.items()))
    for key, value in lab.udf.items():
        print(" ", key, "=", value)
    udt = lab.udt
    if udt:
        print("UDT:", udt.udt)
        for key, value in udt.items():
            print(" ", key, "=", value)

lab = Lab(lims, id="2")
print(lab, id(lab), lab.name, lab.uri, lab.id)
