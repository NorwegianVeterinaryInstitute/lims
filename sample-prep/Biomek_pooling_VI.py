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

    # Cache all analytes/samples and submitted sample udfs

    analytes = process.all_inputs(unique=True)
    analytes = lims.get_batch(analytes)
    lims.get_batch(analyte.samples[0] for analyte in analytes)

    analyte_names = [a.name for a in analytes]
    species = [a.samples[0].udf["Species"] for a in analytes]
    genome_size = [a.samples[0].udf["Genome Size (Mbp)"] for a in analytes]
    project_account = [a.samples[0].udf["Project Account"] for a in analytes]

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

    sample_volumes = [round(input.udf.get('Sample volume to pool (µl)'),2) for input in inputs]
    source_location = [input.location for input in inputs]
    total_sample_number = len(sample_volumes)
    Pool_names = [output.name for output in outputs]
    sample_name = [input.name for input in inputs]
    molarity = [input.udf.get('Molarity TS (nM)') for input in inputs]

    #exit script if entered step with more than one pool

    unique_pools_dict = dict(zip(list(Pool_names),[list(Pool_names).count(i) for i in list(Pool_names)]))
    Pool_names_unique = (list(unique_pools_dict.keys()))

    if len(Pool_names_unique) > 1:
        print("This step only supports one pool at the time. Return to ice bucket and repeat with a single pool")
        sys.exit(1)

    #write csv-file

    with open(file_id + "-Biomek_pooling.csv", "w") as file:
        file.write("LibLabware,LibWellPos,DestLabware,DestWellPos,LibVol,SampleName,Molarity,Species,GenomeSize,ProjectAccount" + '\n')
        for i in range(total_sample_number):
            file.write(
                "Libraries" + ',' + 
                str(re.sub(r':','',source_location[i][1])) + ',' + 
                'LibraryPool'  + ',' + 
                "D1" + "," + 
                str(sample_volumes[i]) + "," + 
                str(sample_name[i]) + "," + 
                str(molarity[i]) + "," +
                str(species[i]) + "," + 
                str(genome_size[i]) + "," +
                str(project_account[i]) + "," + '\n')
    
    #set process UDFs - Total, Max and Min volumes in pooling list

    process.udf["Total Pool Volume"] = round(sum(sample_volumes),2)
    process.udf["Max Pooling Volume"] = round(max(sample_volumes),2)
    process.udf["Min Pooling Volume"] = round(min(sample_volumes),2)
    process.put()

    #print final message. Print warning messages if total volume or individial sample volumes is too high or too small.

    warning1a = False #over 26µl, total volume over 1500 and under 2µl
    warning1b = False #over 26µl and total volume over 1500
    for i in range(total_sample_number):
        if sample_volumes[i] > 26 and sum(sample_volumes) > 1500:
            for i in range(total_sample_number):
                if sample_volumes[i] < 2:
                    warning1a = True
                    break
                else:
                    warning1b = True
            break

    warning2a = False #sample pooling volumes over 26µl and under 2µl
    warning2b = False #sample pooling volumes over 26µl
    for i in range(total_sample_number):
        if sample_volumes[i] > 26:
            for i in range(total_sample_number):
                if sample_volumes[i] < 2:
                    warning2a = True
                    break
                else:
                    warning2b = True           
            break

    warning3 = False #volume over 1500. Individual sample volumes ok.
    for i in range(total_sample_number):
        if sum(sample_volumes) > 1500:
            warning3 = True
            break

    warning4 = False #sample volumes under 2µl
    for i in range(total_sample_number):
        if sample_volumes[i] < 2:
            warning4 = True
    
    if warning1a == True:
        print("WARNING: pooling volume(s) > 26µl and <2µl, while total volume is over 1.5ml. Consider making adjustments")
        sys.exit(1)
    elif warning1b == True:
        print("WARNING: pooling volume(s) > 26µl and total volume is over 1.5ml. Consider making adjustments")
        sys.exit(1)
    elif warning2a == True:
        print("WARNING: pooling volume(s) > 26µl and < 2µl. Consider making adjustments")
        sys.exit(1)
    elif warning2b == True:
        print("WARNING: pooling volume(s) > 26µl. Consider making adjustments")
        sys.exit(1)
    elif warning3 == True:
        print("WARNING: total volume is over 1.5ml. Consider making adjustments")
        sys.exit(1)
    elif warning4 == True:
        print("WARNING: pooling volume(s) < 2µl. Consider making adjustments")
        sys.exit(1)
    else:
        print("Successfully created Biomek csv file for pooling")

main(sys.argv[1], sys.argv[2])


