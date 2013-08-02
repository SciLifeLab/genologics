#!/usr/bin/env python
"""Python script to upload Caliper image files, triggered as a EPP script.

Command to trigger this script:
bash -c "PATH/TO/INSTALLED/SCRIPT
--pluid {processLuid} 
--path PATH_TO_CURRENT_IMAGE_STORAGE
--log {compoundOutputFileLuidN}"


Johannes Alneberg, Science for Life Laboratory, Stockholm, Sweden.
"""

from genologics.lims import Lims
from genologics.entities import Artifact, Process,Container, Sample
from genologics.config import BASEURI,USERNAME,PASSWORD

from argparse import ArgumentParser
import os
import re

from genologics.epp import attach_file,configure_logging, unique_check
    
def main(lims,pluid,path):
    """Uploads images found in path, for each input artifact for a process

    lims: The lims instance
    pluid: Process Lims id
    path: The path to the directory where images are stored

    """
    p = Process(lims,id=args.pluid)
    
    file_list = os.listdir(args.path)
    
    # Find all output artifacts that are of the correct type
    io = p.input_output_maps
    io_filtered = filter(lambda (x,y): y['output-generation-type']=='PerInput',io)
    
    for input,output in io_filtered:
        i_a = Artifact(lims,id=input['limsid'])
        o_a = Artifact(lims,id=output['limsid'])
        unique_check(i_a.samples,
                     "samples connected to artifact {0}".format(i_a.id))
        i_s,i_c=i_a.samples[0],i_a.location[0]
        
        # Use a reguluar expression to find the file name given
        # the container and sample
        re_str = '.+{sample}.+{container}.+\.(png|pdf|PNG)'\
                                   .format(sample=i_s.name,container=i_c.id)
        im_file_r = re.compile(re_str)
        fns = filter(im_file_r.match,file_list)
        print "Looking for files with container id {0} and sample name {1}"\
            .format(i_c.id,i_s.name)
        unique_check(fns,"files connected to container {0} and sample {1}"\
                         .format(i_c.id,i_s.name))
        fn = fns[0]
        print "Found image file {0}".format(fn)
        fp = os.path.join(args.path,fn)

        # Attach file to the LIMS
        attach_file(fp,o_a)
    

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--pluid',
                        help='Process Lims Id')
    parser.add_argument('--path',
                        help='Path where image files are located')
    parser.add_argument('-l','--log',default=None,
                        help='Log file')
    args = parser.parse_args()
 
    if args.log:
        configure_logging(args.log)

    lims = Lims(BASEURI,USERNAME,PASSWORD)
    lims.check_version()

    main(lims,args.pluid,args.path)
