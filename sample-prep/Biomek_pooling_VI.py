'''
Script to create csv-file for pooling on Biomek pipetting robot (post PCR lab)
All calculations for pooling have been done with a LLTK evaluateDynamicExpression script, so we can extract ready-to-use UDFs from the process/step.
Future updates: Also include LLTK calculations in this script?
'''

from genologics.lims import *
from genologics import config
import sys
import re

def main(process_id, file_id):
    
    #load lims instance and process

    lims = Lims(config.BASEURI, config.USERNAME, config.PASSWORD)
    process = Process(lims, id=process_id)

    #load inputs and outputs uri`s`

    inputs = []
    outputs = []
    for i,o in process.input_output_maps:
        output = o['uri']
        if o and o['output-type'] == 'Analyte' and o['output-generation-type'] == 'PerAllInputs':
            input = i['uri']
            inputs.append(input)
            outputs.append(output)

    lims.get_batch(inputs + outputs)

    #load variables for csv-file

    sample_volumes = [input.udf.get('Sample volume to pool (µl)') for input in inputs]
    source_location = [input.location for input in inputs]
    total_sample_number = len(sample_volumes)
    Pool_names = [output.name for output in outputs]
    sample_name = [input.name for input in inputs]

    print(sample_name)

    #exit script if entered step with more than one pool

    unique_pools_dict = dict(zip(list(Pool_names),[list(Pool_names).count(i) for i in list(Pool_names)]))
    Pool_names_unique = (list(unique_pools_dict.keys()))

    if len(Pool_names_unique) > 1:
        print("This step only supports one pool at the time. Return to ice bucket and repeat with a single pool")
        sys.exit(1)

    #write csv-file

    with open(file_id + "-Biomek_pooling.csv", "w") as file:
        file.write("LibLabware,LibWellPos,DestLabware,DestWellPos,LibVol" + '\n')
        for i in range(total_sample_number):
            file.write("Libraries" + ',' + str(re.sub(r':','',source_location[i][1])) + ',' + 'LibraryPool'  + ',' + "D1" + "," + str(sample_volumes[i]) + "," + str(sample_name[i]) +'\n')
    
    print("Successfully created Biomek csv file for pooling")

main(sys.argv[1], sys.argv[2])


