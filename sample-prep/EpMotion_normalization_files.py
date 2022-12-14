'''
csv generator for EpMotion to normalize samples going into sample prep.

Samples at step entry is placed automatically sorting on project name first, then on submitted sample id
For generating the csv-file, this script is instead sorting on output placement. As long as the auto-place script at 
step entry is running, this sorting will be identical as the sorting at entry. But if we are changing to manual placement
in the future, sorting on placement will make sure that the csv-file has data written in correct order 
(ie vertical sorting A1, B1... H1, A2,B2....H2 and so on)

Script sections:
1. LOAD INSTANCE AND INPUTS/OUTPUTS DATA
2. CALCULATE DNA VOLUME AND BUFFER VOLUME
3. STORING INPUT-OUTPUT DATA IN LISTS FOR CSV FILES
4. DEFINE THE EPMOTION TUBE RACKS
5. ASSIGN TUBES AND PLATES TO A LOCATION ON THE EPMOTION DECK
6. WRITE CSV-FILES

NOTE - If changing script to sort on project name and sample id, see sorting list in auto-place-epmotion.py
TODO - When time allows, write file for the occasional manual setup. Excel file? Or possibly as a plate-plot with plotnine? 

author: Magnus Leithaug
'''

from genologics.lims import *
from genologics import config
import sys
import re

def main(process_id, file_id_sample, file_id_buffer):
    
    ''' 1. LOAD INSTANCE AND INPUTS/OUTPUTS DATA'''
    # Load lims instance and process

    lims = Lims(config.BASEURI, config.USERNAME, config.PASSWORD)
    process = Process(lims, id=process_id)

    # for-loop to cache lists of inputs and outputs. 
    # Also using the same loop to store output locations which will be used to create a list for sorting metadata later 

    inputs = []
    outputs = []
    output_location = []

    for ii,oo in process.input_output_maps:
        if oo and oo['output-type'] == 'Analyte' and oo['output-generation-type'] == "PerInput":
            
            input = ii['uri']
            output = oo['uri']

            output_location.append(output.location)    
            inputs.append(input)
            outputs.append(output)            

    '''2. CALCULATE DNA VOLUME AND BUFFER VOLUME'''
    # getting process udf data used for calculations

    minimum_pipetting_volume = process.udf.get('Minimum Pipetting Volume (µl)')
    maximum_pipetting_volume = process.udf.get('Maximum Pipetting Volume (µl)')
    total_volume_per_sample = process.udf.get('Total Volume per Sample  (µl)')

    # doing the default calculations for DNA input volume and Buffer volume. 

    for output in outputs:
        output.udf['DNA input (µl)'] = output.udf['input to prep (ng)'] / output.udf['Concentration Fluorescence (ng/µl)']
        output.udf['Buffer volume (µl)'] = total_volume_per_sample - output.udf['DNA input (µl)']
        output.qc_flag = "PASSED"
    
    # if enforce min vol, then recalculate low volumes. Flag = "FAILED" signals to the user that the input to prep / pipetting volume has been changed

    enforce_min_vol = process.udf.get('Enforce Minimum Pipetting Volume')
    if enforce_min_vol == True:
        for output in outputs:
            if  output.udf['DNA input (µl)'] < minimum_pipetting_volume:
                output.udf['DNA input (µl)'] = minimum_pipetting_volume
                output.udf['input to prep (ng)'] = process.udf['Minimum Pipetting Volume (µl)'] * output.udf['Concentration Fluorescence (ng/µl)']
                output.udf['Buffer volume (µl)'] = total_volume_per_sample- output.udf['DNA input (µl)']
                output.qc_flag = "FAILED"
    

    # if enforce max vol, then recalculate high volumes. Flag = "FAILED" signals to the user that the input to prep / pipetting volume has been changed

    enforce_max_vol = process.udf.get('Enforce Maximum Pipetting Volume')
    if enforce_max_vol == True:
        for output in outputs:
            if  output.udf['DNA input (µl)'] > maximum_pipetting_volume:
                output.udf['DNA input (µl)'] = maximum_pipetting_volume
                output.udf['input to prep (ng)'] = maximum_pipetting_volume * output.udf['Concentration Fluorescence (ng/µl)']
                output.udf['Buffer volume (µl)'] = total_volume_per_sample - output.udf['DNA input (µl)']
                output.qc_flag = "FAILED"

    # store above calculated values in variables (sample_volume and buffer_volume) and put calculated values + qc flag info back to lims via api (put_batch method)

    lims.put_batch(outputs)

    '''3. STORING INPUT-OUTPUT DATA IN LISTS FOR CSV FILES'''

    # Making list for sorting on output well id. First need to switch place of column and row (sorting first on column, then on row)
    # Next, zipping the output wells with input and output uri`s to be used for metadata list creation below (output_wells_inputURI, output_wells_outputURI)

    output_wells = []
    for _,well in output_location:
        row, col = well.split(":")
        output_wells.append((int(col), row))

    output_wells_inputURI = list(zip(output_wells,inputs))    
    output_wells_outputURI = list(zip(output_wells,outputs))

    # creating lists with input metadata that will be used for the csv-file.
    # sorting using the output_wells_inputURI containing [(col,row),input-uri)]. ie sorting on col first, then row. Uri used to append the data

    source_location = []
    input_container_ID = []
    input_container_name = []
    input_container_type = []
    project_names = []
    submitted_id = []

    for _,input in sorted(output_wells_inputURI):
        source_location.append(input.location)
        input_container_ID.append(input.container.id)
        input_container_name.append(input.container.name)
        input_container_type.append(input.container.type.name)
        submitted_id.append(input.samples[0].id)
        project_names.append(input.samples[0].project.name)

    # DNA/buffer volumes and qc-flag status have been put to the database through api above in section 2
    # Now we need to store those volumes and other output data for writing to the csv-file.
    # As for the input data, we are also here sorting on output wells. But now using output_wells_outputURI which contain our output URIs

    dest_location = []
    sample_name = []
    sample_volume =[]
    buffer_volume = []

    for _,output in sorted(output_wells_outputURI):
        dest_location.append(output.location)
        sample_name.append(output.name)
        sample_volume.append(output.udf['DNA input (µl)'])
        buffer_volume.append(output.udf['Buffer volume (µl)'])

    '''4.  DEFINE THE EPMOTION TUBE RACKS'''
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

    '''5. ASSIGN TUBES AND PLATES TO A LOCATION ON THE EPMOTION DECK'''
    # Make lists of unique plate IDs and tube IDs. 
    # Looping over all samples to extract all plate container ids, and then finding the unique plate ids. Ie one unique id per plate (unique_plates_IDs).
    # Looping over all samples to extract all tube submitted sample id`s. Ie one unique id for each sample (submitted_id_tubes).

    input_container_ID_plates = []

    for i in range(len(sample_name)):
        if input_container_type[i] == "96 well plate":
            input_container_ID_plates.append(input_container_ID[i])
        else:
            pass
    
    unique_plates_IDs_dict = dict(zip(list(input_container_ID_plates),[list(input_container_ID_plates).count(i) for i in list(input_container_ID_plates)]))
    unique_plates_IDs = (list(unique_plates_IDs_dict.keys()))

    submitted_id_tubes = []
    for i in range(len(sample_name)):
        if input_container_type[i] == "DNA for NGS":
            submitted_id_tubes.append(submitted_id[i])
    
    # Assign source well and source labware on the EP motion deck. Iterating over all samples in a for-loop. If input_container_type is a plate, the sample source well will be the input well. 
    # Next, the EPmotion plate position is determined from the list of unique_plate_IDs -> Each unique plate is given a separate position on the deck. No more than 4 plates allowed on the deck.
    # If the sample is a tube placed within a DNA for NGS box, the deck positions are set using positions defined in EPmotion_tube_rack_position and EPmotion_tube_rack. We are using the submitted_id[i] to query the index of submitted_id_tubes. 
    # submitted_id_tubes contain only the submitted ID of tubes sorted according to output placement. The first tube in the list will get placed in EPmotion_tube_rack_position[1] in EPmotion_tube_rack[1] and so on up to a maximum of 96 sample tubes.

    src_well = []
    src_labware = [] 
    for i in range(len(sample_name)):
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
        elif input_container_type[i] == "DNA for NGS":
            src_well.append(EPmotion_tube_rack_position[submitted_id_tubes.index(submitted_id[i])])
            src_labware.append(EPmotion_tube_rack[submitted_id_tubes.index(submitted_id[i])])
        else:
            print("Input container type not recognized. Only tubes placed in a -DNA for NGS- cryobox or 96 well plates are supported")
            sys.exit(1)
    
    # Make human readable source position to make csv easier to read when loading deck

    position_human_readable = []
    for i in range(len(sample_name)):
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
    
    
    '''6. WRITE CSV-FILES'''    
    # Write csv-files with cashed metadata. Note that buffer volumes < 0 is exluded (could have negative values if enforce maximum pipetting volume is set to False)
    # EPMotion program requires two files - one for each transfer (sample + buffer)

    with open(file_id_sample + "-EpMotionSample.csv", "w") as file:
        file.write("Labware;Src.Barcode;Src.List Name;Dest.Barcode;Dest.List name;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write("Barcode ID;Labware;Source;Labware;Destination;Volume;Tool;Submission Name;SubmittedLimsID;Sample Name;Storage Container;Storage Well;EPMotion Deck Position;EPMotion Tube Placement" + '\n')
        for i in range(len(sample_name)):
            file.write(';' + str(src_labware[i]) + ';' + str(src_well[i]) + ';' + '1;' + str(re.sub(r':','',dest_location[i][1])) + ';' + str(round(sample_volume[i],2))  + ';' + 'TS_50;' + str(project_names[i]) + ';' + str(submitted_id[i]) + ';'  + str(sample_name[i]) + ";" + str(input_container_name[i]) + ';' + str(re.sub(r':','',source_location[i][1])) + ';' + str(position_human_readable[i]) + ';' + str(src_well[i])  +'\n')
              
    with open(file_id_buffer + "-EpMotionBuffer.csv", "w") as file:
        file.write("Labware;Src.Barcode;Src.List Name;Dest.Barcode;Dest.List name;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write(";;;;;;;" + '\n')
        file.write("Barcode ID;Labware;Source;Labware;Destination;Volume;Tool" + '\n')
        for i in range(len(sample_name)):
            if buffer_volume[i] > 0:
                dest_well = dest_location[i][1]
                destination_well = re.sub(r':','',dest_well)
                file.write(';' + '1;' + '7;' + '1;' + destination_well + ';' + str(round(buffer_volume[i],2))  + ';' + 'TS_50;' + ';' + '\n')
            else:
                pass
    
    print("Successfully created EPmotion sample csv files")

# Run as EPP: python3 /opt/gls/clarity/customextensions/EpMotion_normalization_file_sample.py {processLuid}(PROCESS_ID) {compoundOutputFileLuidN}(FILE_ID_SAMPLE) {compoundOutputFileLuidN}(FILE_ID_BUFFER) 

main(sys.argv[1], sys.argv[2], sys.argv[3])