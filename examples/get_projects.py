"""Python interface to GenoLogics LIMS via its REST API.

Usage example: Get some projects.



Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
"""

# Login parameters for connecting to a LIMS instance.
from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.lims import Lims, Project

# Create the LIMS interface instance, and check the connection and version.
lims = Lims(BASEURI, USERNAME, PASSWORD)
lims.check_version()

# Get the list of all projects.
projects = lims.get_projects()
print(len(projects), "projects in total")

# Get the list of all projects opened since May 30th 2012.
day = "2012-05-30"
projects = lims.get_projects(open_date=day)
print(len(projects), "projects opened since", day)

# Get the project with the specified LIMS id, and print some info.
project = Project(lims, id="P193")
print(project, project.name, project.open_date, project.close_date)

print("    UDFs:")
for key, value in project.udf.items():
    print(" ", key, "=", value)

udt = project.udt
print("    UDT:", udt.udt)
for key, value in udt.items():
    print(" ", key, "=", value)

print("    files:")
for file in project.files:
    print(file.id)
    print(file.content_location)
    print(file.original_location)
