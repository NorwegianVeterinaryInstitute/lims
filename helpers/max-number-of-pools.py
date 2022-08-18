# Check for multiple pools
# Only one pool at the time allowed for the step

import sys
from genologics.lims import *
from genologics import config
import re

def main(process_id):
    lims = Lims(config.BASEURI, config.USERNAME, config.PASSWORD)
    
    #load process data
    process = Process(lims, id=process_id)
    
    #load input and output data
    inputs = []
    outputs = []
    for i,o in process.input_output_maps:
        output = o['uri']
        if o and o['output-type'] == 'Analyte' and o['output-generation-type'] == 'PerAllInputs':
            input = i['uri']
            inputs.append(input)
            outputs.append(output)
    lims.get_batch(inputs + outputs)
    
    #find number of unique pools
    sample_name_out = [output.name for output in outputs]
    unique_pools_dict = dict(zip(list(sample_name_out),[list(sample_name_out).count(i) for i in list(sample_name_out)]))
    unique_pools_IDs = (list(unique_pools_dict.keys()))

    #exit step if trying to process more than 1 pool
    if len(unique_pools_IDs) > 1:
        print("Only 1 pool is supported by this step. You are trying to process {0} pools".format(len(unique_pools_IDs)))
        sys.exit(1)

main(sys.argv[1])