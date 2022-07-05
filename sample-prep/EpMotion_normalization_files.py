'''
csv generator for EpMotion to normalize samples going into sample prep.
All calculations have been done with a LLTK evaluateDynamicExpression script, so we can extract ready-to-use UDFs from the process/step.
Future update: Also include LLTK calculations in this script to make the EPP faster. 
'''

from genologics.lims import *
from genologics import config
import sys
import re

def main(process_id, file_id_sample, file_id_buffer):
    
    # Load lims instance and process

    lims = Lims(config.BASEURI, config.USERNAME, config.PASSWORD)
    process = Process(lims, id=process_id)

    # Load inputs and outputs data

    inputs = []
    outputs = []
    for i,o in process.input_output_maps:
        output = o['uri']
        if o and o['output-type'] == 'Analyte' and o['output-generation-type'] == 'PerInput':
            input = i['uri']
            inputs.append(input)
            outputs.append(output)
    lims.get_batch(inputs + outputs)
    
    # Make lists with variables needed for csv-files

    DNA_input = [output.udf.get('DNA input (µl)') for output in outputs]
    buffer_volume = [output.udf.get('Buffer volume (µl)') for output in outputs]
    dest_location = [output.location for output in outputs]
    source_location = [input.location for input in inputs]
    input_container_ID = [input.container.id for input in inputs]
    sample_name = [output.name for output in outputs]
    input_container_name = [input.container.name for input in inputs]
    input_container_type = [input.container.type.name for input in inputs]
    input_type_tube = [x for x in input_container_type if x == "Tube"] #not used (yet)
    input_type_plate = [x for x in input_container_type if x == "96 well plate"] #not used (yet)

    # Make lists with project names and submitted sample IDs (also for the csv-files)

    project_names = []
    submitted_id = []
    for ii,oo in process.input_output_maps:
        if oo['output-generation-type'] == "PerInput":
            i = ii['uri']
            submitted_id.append(i.samples[0].id)
            project_names.append(i.samples[0].project.name)

    # Calculate number of samples. Used for looping chunks below. Also exit if more than 96 total samples going into step. 

    num_samples = len(sample_name)
    if num_samples > 96:
        print("You have entered the step with", num_samples, ", samples. Maximum for this step is 96 samples")
        sys.exit(1)

    # Make lists with EPmotion tube rack labware IDs and position IDs (we have 4 racks with 24 positions in each = max 96 tubes)

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

    # Make lists of unique plate IDs and tube IDs for use in next chunk. 
    # Note that tube IDs will always be unique (1 per sample), while plate IDs will have several entires (same ID for multiple samples)

    input_container_ID_plates = []
    input_container_ID_tubes = []

    for i in range(num_samples):
        if input_container_type[i] == "96 well plate":
            input_container_ID_plates.append(input_container_ID[i])
        else:
            pass

    unique_plates_IDs_dict = dict(zip(list(input_container_ID_plates),[list(input_container_ID_plates).count(i) for i in list(input_container_ID_plates)]))
    unique_plates_IDs = (list(unique_plates_IDs_dict.keys()))

    for i in range(num_samples):
        if input_container_type[i] == "Tube":
            input_container_ID_tubes.append(input_container_ID[i])
        else:
            pass
    
    # Assign source well and source labware on the EP motion deck

    src_well = []
    src_labware = [] 
    for i in range(num_samples):
        if input_container_type[i] == "96 well plate":
            src_well.append(re.sub(r':','',source_location[i][1]))
            if input_container_ID[i] == unique_plates_IDs[0]:
                src_labware.append("5")
            elif input_container_ID[i] == unique_plates_IDs[1]:
                src_labware.append("6")
            elif input_container_ID[i] == unique_plates_IDs[2]:
                src_labware.append("7")
            elif input_container_ID[i] == unique_plates_IDs[3]:
                src_labware.append("8")
            elif input_container_ID[i] == unique_plates_IDs[4]:
                print("No more than four plates supported at the deck simultaneously")
                sys.exit(1)                
            else:
                print("Error assigning labware position for plate(s). Aborting. Contact your system admin.")
                sys.exit(1)
        elif input_container_type[i] == "Tube":
            src_well.append(EPmotion_tube_rack_position[input_container_ID_tubes.index(input_container_ID[i])])
            src_labware.append(EPmotion_tube_rack[input_container_ID_tubes.index(input_container_ID[i])])
        else:
            print("input container type not recognized. Only Tubes or 96 well plates are supported")
            sys.exit(1)
    
    # Make human readable source position to make csv easier to read when loading deck

    position_human_readable = []
    for i in range(num_samples):
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
        
    # Write csv-files with sample and buffer volumes, positions and metadata. Note that buffer volumes < 0 wont be transferred.
    # Note: EPMotion program requires two files - one for each transfer (sample + buffer)

    with open(file_id_sample + "-EpMotionSample.csv", "w") as file:
        file.write("Labware;Src.Barcode;Src.List Name;Dest.Barcode;Dest.List name;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write("Barcode ID;Labware;Source;Labware;Destination;Volume;Tool;Name;ContainerName;SubmittedLimsID;Project;SourcePosition" + '\n')
        for i in range(num_samples):
            file.write(';' + str(src_labware[i]) + ';' + str(src_well[i]) + ';' + '1;' + str(re.sub(r':','',dest_location[i][1])) + ';' + str(DNA_input[i])  + ';' + 'TS_50;' + sample_name[i] + ";" + input_container_name[i] + ';' + submitted_id[i] + ';' + project_names[i] + ';' + position_human_readable[i] +'\n')

    with open(file_id_buffer + "-EpMotionBuffer.csv", "w") as file:
        file.write("Labware;Src.Barcode;Src.List Name;Dest.Barcode;Dest.List name;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write("Barcode ID;Labware;Source;Labware;Destination;Volume;Tool;Name;Project" + '\n')
        for i in range(num_samples):
            if buffer_volume[i] > 0:
                dest_well = dest_location[i][1]
                destination_well = re.sub(r':','',dest_well)
                file.write(';' + '1;' + '7;' + '1;' + destination_well + ';' + str(buffer_volume[i])  + ';' + 'TS_50;' + sample_name[i] + ';' + project_names[i] + ';' + '\n')
            else:
                pass
    
    print("Successfully created EPmotion sample csv files")

# Run as EPP: python3 /opt/gls/clarity/customextensions/EpMotion_normalization_file_sample.py {processLuid}(PROCESS_ID) {compoundOutputFileLuidN}(FILE_ID_SAMPLE) {compoundOutputFileLuidN}(FILE_ID_BUFFER) 

main(sys.argv[1], sys.argv[2], sys.argv[3])