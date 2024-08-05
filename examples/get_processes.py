"""Python interface to GenoLogics LIMS via its REST API.

Usage example: Get some processes.



Per Kraulis, Science for Life Laboratory, Stockholm, Sweden.
"""

# Login parameters for connecting to a LIMS instance.
from genologics.config import BASEURI, PASSWORD, USERNAME
from genologics.lims import Lims, Process

# Create the LIMS interface instance, and check the connection and version.
lims = Lims(BASEURI, USERNAME, PASSWORD)
lims.check_version()

# Get the list of all processes.
processes = lims.get_processes()
print(len(processes), "processes in total")

process = Process(lims, id="QCF-PJK-120703-24-1140")
print(process, process.id, process.type, process.type.name)
for input, output in process.input_output_maps:
    if input:
        print("input:", list(input.items()))
    if output:
        print("output:", list(output.items()))
