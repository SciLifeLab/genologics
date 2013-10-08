#!/usr/bin/env python
import os
import subprocess
from argparse import ArgumentParser

TEMPLATE = """
Scripts in the Genologics Package
=================================
Short usage descriptions for the scripts in the Genologics Package.

"""

def indent(s):
    return "\n".join(map(lambda w: '\t'+w, s.splitlines()))


def help_doc_rst(script,file_path):
    """ Fetch the --help info from the script, outputs rst formatted string """
    script_path = os.path.join(file_path,script)
    sp = subprocess.Popen(["python",script_path,"--help"],
                          stdout=subprocess.PIPE)
    stdout,stderr = sp.communicate()
    
    # Add help message to template
    header = ("{0}\n{1}\nAutomated help message generated from running {0} "
              "with the --help flag::\n\n").format(script,'-'*len(script))

    return header + "{0}\n\n".format(indent(stdout))
    

if __name__ == "__main__":
    # Argumentparser only to add --help option
    args = ArgumentParser(description=("Generates basic documentation on all scripts "
                                       "contained in the scripts folder. Used instead "
                                       "of sphinx extension since readthedocs build "
                                       "failed on genologics imports. ")).parse_args()

    file_path = os.path.dirname(os.path.realpath(__file__))
    this_file = os.path.basename(__file__)

    # Fetch all python scripts in the scripts folder
    file_list = os.listdir(file_path)
    scripts = filter(lambda fn: fn[-3:]=='.py' and fn != this_file, file_list)
    scripts = sorted(scripts)

    for script in scripts:
        TEMPLATE += help_doc_rst(script, file_path)

    # This script added last:
    TEMPLATE += help_doc_rst(this_file, file_path)

    # Print all help messages to a sphinx (restructured text) markup file
    docs_path = os.path.join(file_path,'..','docs','scripts.rst')
    with open(docs_path,'w') as doc_f:
        doc_f.write(TEMPLATE)
    
