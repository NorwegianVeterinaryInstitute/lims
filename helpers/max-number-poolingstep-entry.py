'''
Script to restrict certain sample combinations from entering the pooling step

Rules for the step:
1- No tubes allowed. Only plates (96 well plate or HSP plate)
2- No duplicate applications allowed into the step
3- No more than two plates allowed into the step at the same time due to limitations on robot and pooling script.
    (might be rewritten for up to max 4 plates later)

Script will exit the script if rules are broken while providing useful error message for the user.
Author: Magnus Leithaug
'''

import sys
from genologics.lims import *
from genologics import config

def main(process_id):
    
    # load lims instance and process uid
    
    lims = Lims(config.BASEURI, config.USERNAME, config.PASSWORD)
    process = Process(lims, id=process_id)
    
    #load input and output data

    inputs = []
    outputs = []
    for i,o in process.input_output_maps:
        output = o['uri']
        if o and o['output-type'] == 'ResultFile' and o['output-generation-type'] == 'PerAllInputs':
            input = i['uri']
            inputs.append(input)
            outputs.append(output)
    lims.get_batch(inputs + outputs)
    
    # Rule 1: exit step if input container type is Tube

    input_container_type = [input.container.type.name for input in inputs]
    if input_container_type == "Tube":
        print("Only 96-well plates are allowed to enter this step. You have tried to enter the step with Tubes --> Exiting step") 
        sys.exit(1)
    
    # Rule 2: exit step if having samples with different applications 

    application = [input.udf.get('Application') for input in inputs]
    applications_unique = list(set(application))

    if len(applications_unique) > 1:
        print("You are entering samples with {0} different applications. You can only pool samples with the same application".format(len(applications_unique)))
        sys.exit(1)

    # Rule 3: exit step if entering step with more than two plates

    input_container_name = [input.container.name for input in inputs]
    if len(input_container_name) > 2:
        print("You are entering the step with {0} plates. At the moment this step only support a maximum of two sample plates for pooling".format(len(input_container_name)))


#Run as EPP: python3 /opt/gls/clarity/customextensions/max-number-poolingstep-entry.py {processLuid}
main(sys.argv[1])
