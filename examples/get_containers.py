"""Python interface to GenoLogics LIMS via its REST API.

Usage example: Get some containers.



Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
"""

import codecs

from genologics.lims import *

# Login parameters for connecting to a LIMS instance.
from genologics.config import BASEURI, USERNAME, PASSWORD

# Create the LIMS interface instance, and check the connection and version.
lims = Lims(BASEURI, USERNAME, PASSWORD)
lims.check_version()

# Get the list of all containers.
## containers = lims.get_containers()
## print len(containers), 'containers in total'

## for state in ['Empty', 'Reagent-Only', 'Discarded', 'Populated']:
##     containers = lims.get_containers(state=state)
##     print len(containers), state, 'containers'

containers = lims.get_containers(type='96 well plate')
print(len(containers))

container = containers[2]
print(container, container.occupied_wells)

placements = container.get_placements()
for location, artifact in sorted(placements.items()):
    print(location, artifact.name, id(artifact), repr(artifact), artifact.root)

containertype = container.type
print(containertype, containertype.name, containertype.x_dimension, containertype.y_dimension)



containers = lims.get_containers(type='Illumina Flow Cell',state='Populated')
for container in containers:
	print(container.name)
	print(container.id)
	print(list(container.placements.keys()))
	arts=lims.get_artifacts(containername=container.name)
	for art in arts:
		print(art.name)
		print(art.type)
		print(list(art.udf.items()))
		print(art.parent_process.type.name)
