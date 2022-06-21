'''
csv generator for EpMotion to normalize samples going into sample prep.
All calculations have been done with a LLTK evaluateDynamicExpression script, so we can extract ready-to-use UDFs from the process/step.
Future updates: Also include LLTK calculations in this script. Write excelfile (openpyxl) that is less crowded than the csv for sample placement on deck (?). 
'''

from genologics.lims import *
from genologics import config
import sys
import re

def main(process_id, file_id_sample, file_id_buffer):
    
    #load lims instance and process

    lims = Lims(config.BASEURI, config.USERNAME, config.PASSWORD)
    process = Process(lims, id=process_id)
    projects = lims.get_projects()

    #load inputs and outputs uri`s`

    inputs = []
    outputs = []
    for i,o in process.input_output_maps:
        output = o['uri']

        if o and o['output-type'] == 'Analyte' and o['output-generation-type'] == 'PerInput':
            input = i['uri']
            inputs.append(input)
            outputs.append(output)
    lims.get_batch(inputs + outputs)
    
    #Make tuples with variables needed for csv-file creation

    DNA_input = [output.udf.get('DNA input (µl)') for output in outputs]
    BufferVolume = [output.udf.get('Buffer volume (µl)') for output in outputs]
    dest_location = [output.location for output in outputs]
    source_location = [input.location for input in inputs]
    input_container_ID = [input.container.id for input in inputs]
    sample_name = [output.name for output in outputs]

    input_container_type = [input.container.type.name for input in inputs]
    input_type_tube = [x for x in input_container_type if x == "Tube"]
    input_type_plate = [x for x in input_container_type if x == "96 well plate"]

    #project names (this chunk seems a bit slow for some reason. Rewrite?)
    project_names = []
    for i in range(len(DNA_input)):
        project_names.append(output.samples[i].project.name)

    #total number of samples in step. Exit if more than 96.

    length = len(DNA_input)

    if length > 96:
        print("You have entered the step with", length, ", samples. Maximum for this step is 96 samples")
        sys.exit(1)

    #make tuples with EPmotion tube rack labware IDs and position IDs

    EPmotion_tube_rack = [
        1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
        2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,
        3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,3,
        4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,
        ]
    EPmotion_tube_rack_position = [
        1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,
        1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,
        1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,
        1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,
        ]

    #assign source well and source labware on the EP motion deck

    src_well = []
    src_labware = []    
    input_container_ID_plates = []

    for i in range(length):
        if input_container_type[i] == "96 well plate":
            input_container_ID_plates.append(input_container_ID[i])
        else:
            pass

    number_of_unique_plates = dict(zip(list(input_container_ID_plates),[list(input_container_ID_plates).count(i) for i in list(input_container_ID_plates)]))
    keys_wells_plate = (list(number_of_unique_plates.keys()))

    for i in range(length):
        if input_container_type[i] == "96 well plate":
            src_well.append(re.sub(r':','',source_location[i][1]))
            if input_container_ID[i] == keys_wells_plate[0]:
                src_labware.append("5")
            elif input_container_ID[i] == keys_wells_plate[1]:
                src_labware.append("6")
            elif input_container_ID[i] == keys_wells_plate[2]:
                src_labware.append("7")
            elif input_container_ID[i] == keys_wells_plate[3]:
                src_labware.append("8")
            elif input_container_ID[i] == keys_wells_plate[4]:
                print("No more than four plates supported at the deck simultaneously")
                sys.exit(1)                
            else:
                print("Error assigning labware position for plate(s). Aborting. Contact your system admin.")
                sys.exit(1)
        elif input_container_type[i] == "Tube":
            src_well.append(EPmotion_tube_rack_position[i])
            src_labware.append(EPmotion_tube_rack[i])
        else:
            print("input container type not recognized. Only Tubes or 96 well plates are supported")
            sys.exit(1)
    
    #Make human readable source position to make csv easier to read

    position_human_readable = []
    for i in range(length):
        if src_labware[i] == 1:
            position_human_readable.append("rack_1")
        elif src_labware[i] == 2:
            position_human_readable.append("rack_2")
        elif src_labware[i] == 3:
            position_human_readable.append("rack_3")
        elif src_labware[i] == 4:
            position_human_readable.append("rack_4")
        elif src_labware[i] == "5":
            position_human_readable.append("plate_1")
        elif src_labware[i] == "6":
            position_human_readable.append("plate_2")
        elif src_labware[i] == "7":
            position_human_readable.append("plate_3")
        elif src_labware[i] == "8":
            position_human_readable.append("plate_4")
        else:
            print("error assigning human readable source names. Contact admin.")
            sys.exit(1)
        
    #write csv-files for transfering sample and buffer. Note that buffer volumes < 0 wont be transferred.

    with open(file_id_sample + "-EpMotionSample.csv", "w") as file:
        file.write("Labware;Src.Barcode;Src.List Name;Dest.Barcode;Dest.List name;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write("Barcode ID;Labware;Source;Labware;Destination;Volume;Tool;Name;Project;SourcePosition" + '\n')
        for i in range(length):
            file.write(';' + str(src_labware[i]) + ';' + str(src_well[i]) + ';' + '1;' + str(re.sub(r':','',dest_location[i][1])) + ';' + str(DNA_input[i])  + ';' + 'TS_50;' + sample_name[i] + ';' + project_names[i] + ';' + position_human_readable[i] +'\n')

    with open(file_id_buffer + "-EpMotionBuffer.csv", "w") as file:
        file.write("Labware;Src.Barcode;Src.List Name;Dest.Barcode;Dest.List name;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write("Barcode ID;Labware;Source;Labware;Destination;Volume;Tool;Name;Project;SourcePosition" + '\n')
        for i in range(length):
            if BufferVolume[i] > 0:
                dest_well = dest_location[i][1]
                destination_well = re.sub(r':','',dest_well)
                file.write(';' + '1;' + '7;' + '1;' + destination_well + ';' + str(BufferVolume[i])  + ';' + 'TS_50;' + sample_name[i] + ';' + project_names[i] + ';' + position_human_readable[i] + '\n')
            else:
                pass
    
    print("Successfully created EPmotion sample csv files")

#run as EPP: python3 /opt/gls/clarity/customextensions/EpMotion_normalization_file_sample.py {processLuid} {compoundOutputFileLuidN} {compoundOutputFileLuidN} 
# (python3 /opt/gls/clarity/customextensions/EpMotion_normalization_file_sample.py PROCESS_ID FILE_ID_SAMPLE FILE_ID_BUFFER)

main(sys.argv[1], sys.argv[2], sys.argv[3])