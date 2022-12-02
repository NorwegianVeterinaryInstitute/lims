'''
Script to create csv-file for pooling on Biomek pipetting robot and a pooling placement map as pdf for reference and/or manual pooling

Species, Genome Size, Project Account are copied to the derived input using an LLTK script at step entry. Pooling volume calculations done by this script.
At step entry, another script will check that input is max 2 plates. And no tubes allowed (at the moment) - change if needed in future. Will need major rewrite.

author: Magnus Leithaug
'''

from genologics.lims import *
from genologics import config
import sys
import re
from plotnine import ggplot, geom_point, aes, geom_text, scale_y_discrete, scale_x_discrete, theme_bw, ggtitle, xlab, ylab, theme, scale_color_manual, save_as_pdf_pages, scale_color_identity
import pandas as pd

#sort_key function (for sorting the input lists)

def sort_key(elem):
    container_name = elem.container.name
    container, well = elem.location
    row, col = well.split(":")
    return (container_name, int(col), row)


def main(process_id, file_id, pdf_file_id):
    
    #LOAD LIMS INSTANCE AND PROCESS

    lims = Lims(config.BASEURI, config.USERNAME, config.PASSWORD)
    process = Process(lims, id=process_id)

    #LOAD INPUT AND OUTPUT URIs

    inputs = []
    outputs = []
    for i,o in process.input_output_maps:
        output = o['uri']
        if o and o['output-type'] == 'Analyte' and o['output-generation-type'] == 'PerAllInputs':
            input = i['uri']
            inputs.append(input)
            outputs.append(output)

    lims.get_batch(inputs + outputs)

    # LOAD DATA required for the generated files
    # calculating sample volumes from molMbp process udf and input udfs Genome Size and Molarity
    
    MAX_TOTAL_VOLUME = 1500
    
    sample_volumes = []
    source_location = []
    sample_name = []
    molarity = []
    project_account = []
    genome_size = []
    species = []
    input_container_type =[]
    input_container_name =[]

    molMbp = process.udf.get('fmol/Mbp')
    min_vol_required = process.udf.get('Min Volume Required')
    max_vol_available = process.udf.get('Max Volume Available')
    enforce_max_vol = process.udf.get('Enforce Max Volume Available')
    enforce_min_volume = process.udf.get('Enforce Min Volume Required')
    
    for input in sorted(inputs, key=sort_key):
        source_location.append(input.location)
        sample_name.append(input.name)
        molarity.append(input.udf.get('Molarity TS (nM)'))
        project_account.append(input.udf.get('Project Account'))
        genome_size.append(input.udf.get('Genome Size (Mbp)'))
        species.append(input.udf.get('Species'))
        input_container_type.append(input.container.type.name)
        input_container_name.append(input.container.name)
        sample_volumes.append(round(molMbp*input.udf.get('Genome Size (Mbp)')/input.udf.get('Molarity TS (nM)'),2))

    # loop for 'Enforce Min Volume Required' button on the step. 
    # If true, find the minimum value, find its index.
    # Recalculate molMbp to achieve min_vol_required. New value put to the process udf for info to the user. volume_threshold_plotcolor set to yellow
    # finally a for-loop to update sample_volumes using the new fmol/Mbp

    if enforce_min_volume == True:
        min_volume_in_list = min(sample_volumes)
        min_volume_in_list_index = sample_volumes.index(min_volume_in_list)
        if min_volume_in_list < min_vol_required: 
            molMbp = (min_vol_required*molarity[min_volume_in_list_index])/genome_size[min_volume_in_list_index]
            process.udf['fmol/Mbp'] = molMbp
            process.put()

            index = 0
            for input in sorted(inputs, key=sort_key):
                sample_volumes[index] = (round(molMbp*input.udf.get('Genome Size (Mbp)')/input.udf.get('Molarity TS (nM)'),2))
                index += 1

    # volume_threshold_plotcolor to allow conditional coloring on plot
    # adjusting volume to max_vol_available if enforce_max_vol
    # over or under threshold = red, within threshold = palegreen, adjusted volume to max = yellow 

    volume_threshold_plotcolor = []

    for volumes in sample_volumes:
        if volumes > max_vol_available or volumes < min_vol_required:
            volume_threshold_plotcolor.append("red")
        else:
            volume_threshold_plotcolor.append("palegreen") 

    if enforce_max_vol == True:
        for i in range(len(sample_volumes)):
            if sample_volumes[i] > max_vol_available:
                sample_volumes[i] = max_vol_available
                volume_threshold_plotcolor[i] = "yellow"

    if enforce_min_volume == True:
        if min_volume_in_list < min_vol_required:
            volume_threshold_plotcolor[min_volume_in_list_index] = "yellow"

    # DEFINE BIOMEK DECK PLATE POSITIONS (LIBLABWARE)
    # create list with biomek LibLabware variable for sorting plate position on biomek deck 
    # (plate 1 = position "Libraries 1", plate 2 = position "Libraries 2")
    # no duplicate values allowed in set, so can extract unique container names by redefining to set. 

    input_container_name_unique = sorted(list(set(input_container_name)))
    print(input_container_name_unique)
    libLabware = []
    for i in range(len(input_container_name)):
        if input_container_name[i] == input_container_name_unique[0]:
            libLabware.append("Libraries1")
        elif input_container_name[i] == input_container_name_unique[1]:
            libLabware.append("Libraries2")
        else:
            print("Error assigning Biomek LibLabware positions. Contact system admin")
            sys.exit(1)

    #WRITE CSV FILE 
    # using data loaded above. Looping over all inputs and writing line-by-line to the csv-file

    total_sample_number = len(sample_name)

    with open(file_id + "-Biomek_pooling.csv", "w") as file:
        file.write("LibLabware,LibWellPos,DestLabware,DestWellPos,LibVol,SampleName,Molarity,Species,GenomeSize,PlateID,fmol/Mbp-actual" + '\n')
        for i in range(total_sample_number):
            file.write(
                str(libLabware[i]) + ',' + 
                str(re.sub(r':','',source_location[i][1])) + ',' + 
                'LibraryPool'  + ',' + 
                "D1" + "," + 
                str(sample_volumes[i]) + "," + 
                str(sample_name[i]) + "," + 
                str(molarity[i]) + "," +
                str(species[i]) + "," + 
                str(genome_size[i]) + "," +
                str(input_container_name[i]) + "," +
                str(round((sample_volumes[i]*molarity[i])/genome_size[i],0))+ '\n')
    
    #SET PROCESS UDFs - Total, Max and Min volumes.
    # Will display on the step after running the script. Makes it easy to quickly evaluate if you need to adjust fmol/Mbp and rerun

    process.udf["Total Pool Volume"] = round(sum(sample_volumes),2)
    process.udf["Max Pooling Volume"] = round(max(sample_volumes),2)
    process.udf["Min Pooling Volume"] = round(min(sample_volumes),2)
    process.put()

    # CREATE PLOT FOR PRINT-OUT WITH PLOTNINE
    # round sample volumes for a neater presentation
    # create empty wells for plotting grey circles - transffered to pandas dataframe for input to ggplot
    # create lists for row and column index for all samples. Collected from source_location, so will be ordered according to sort_key
    # make plate1- and plate2-specific pandas dataframes to be used as input to ggplot. Done with for-loop while using if-statement to select for input_container_name_unique
    # make plots using plotnine ggplot. plot2 only gets produced if len(input_container_name_unique) == 2
    # print out plots in pdf-files. pdf_file_id ({compoundOutputFileLuid2}) will place it in file placeholder 2 in lims

    sample_volumes_round = [round(num,1) for num in sample_volumes]

    pool_names = [output.name for output in outputs]
    pool_names_unique =list(set(pool_names))

    row_empty = ["A","B","C","D","E","F","G","H"]*12
    col_empty = [
    "1","1","1","1","1","1","1","1",
    "2","2","2","2","2","2","2","2",
    "3","3","3","3","3","3","3","3",
    "4","4","4","4","4","4","4","4",
    "5","5","5","5","5","5","5","5",
    "6","6","6","6","6","6","6","6",
    "7","7","7","7","7","7","7","7",
    "8","8","8","8","8","8","8","8",
    "9","9","9","9","9","9","9","9",
    "10","10","10","10","10","10","10","10",
    "11","11","11","11","11","11","11","11",
    "12","12","12","12","12","12","12","12"]
    
    white_dict = {'row_empty':row_empty, 'col_empty':col_empty}
    white_df = pd.DataFrame(white_dict)

    well = [loc[1] for loc in source_location]
    row = [item.split(":",1)[0] for item in well]
    col = [item.split(":",1)[1] for item in well]
    
    well_plate_1=[]
    well_plate_2=[]
    row_plate_1=[]
    row_plate_2=[]
    col_plate_1=[]
    col_plate_2=[]
    sample_volumes_plate_1=[]
    sample_volumes_plate_2=[]
    volume_threshold_plotcolor_plate_1=[]
    volume_threshold_plotcolor_plate_2=[]

    for i in range(len(input_container_name)):
        if input_container_name[i] == input_container_name_unique[0]:
            
            well_plate_1.append(well[i])
            row_plate_1.append(row[i])
            col_plate_1.append(col[i])
            sample_volumes_plate_1.append(sample_volumes_round[i])
            volume_threshold_plotcolor_plate_1.append(volume_threshold_plotcolor[i])

            plot_dict_plate_1 = {'Well':well_plate_1,'row':row_plate_1, 'col':col_plate_1, 'volume':sample_volumes_plate_1, 'over_threshold':volume_threshold_plotcolor_plate_1}
            plot_df_plate_1 = pd.DataFrame(plot_dict_plate_1)

    if len(input_container_name_unique) == 2:
        for i in range(len(input_container_name)):
            if input_container_name[i] == input_container_name_unique[1]:
            
                well_plate_2.append(well[i])
                row_plate_2.append(row[i])
                col_plate_2.append(col[i])
                sample_volumes_plate_2.append(sample_volumes_round[i])
                volume_threshold_plotcolor_plate_2.append(volume_threshold_plotcolor[i])

                plot_dict_plate_2 = {'Well':well_plate_2,'row':row_plate_2, 'col':col_plate_2, 'volume':sample_volumes_plate_2, 'over_threshold':volume_threshold_plotcolor_plate_2}
                plot_df_plate_2 = pd.DataFrame(plot_dict_plate_2)

    plot_plate1 = (ggplot()
    + geom_point(data=white_df, mapping = aes(x='col_empty', y='row_empty'), size =19, colour="whitesmoke")
    + geom_point(data=plot_df_plate_1, mapping=aes(x='col', y='row', colour = 'over_threshold'), size =19)
    + scale_color_identity()
    + geom_text(data=plot_df_plate_1, mapping=aes(x='col',y='row',label='volume'), size = 9, show_legend = False)
    + scale_y_discrete(limits=["H","G","F","E","D","C","B","A"])
    + scale_x_discrete(limits=["1","2","3","4","5","6","7","8","9","10","11","12"])
    + ggtitle("Pooling Map,   "+str(pool_names_unique[0])+",   "+str(len(well_plate_1))+" samples"+",  plate ID: "+ input_container_name_unique[0]  + "\n\n green = OK, Yellow = adjusted , Red = not within "+str(min_vol_required) +"-"+str(max_vol_available)+"µl" )
    + xlab("Column")
    + ylab("Row")
    + theme_bw()
    + theme(legend_position='none', figure_size=(8,6))
    )

    if len(input_container_name_unique) == 2:
        plot_plate2 = (ggplot()
        + geom_point(data=white_df, mapping = aes(x='col_empty', y='row_empty'), size =19, colour="whitesmoke")
        + geom_point(data=plot_df_plate_2, mapping=aes(x='col', y='row', colour = 'over_threshold'), size =19)
        + scale_color_identity()
        + geom_text(data=plot_df_plate_2, mapping=aes(x='col',y='row',label='volume'), size = 9, show_legend = False)
        + scale_y_discrete(limits=["H","G","F","E","D","C","B","A"])
        + scale_x_discrete(limits=["1","2","3","4","5","6","7","8","9","10","11","12"])
        + ggtitle("Pooling Map,   "+str(pool_names_unique[0])+",   "+str(len(well_plate_2))+" samples"+",  plate ID: "+ input_container_name_unique[1] + "\n\n green = OK, Yellow = adjusted , Red = not within "+str(min_vol_required) +"-"+str(max_vol_available)+"µl" )
        + xlab("Column")
        + ylab("Row")
        + theme_bw()
        + theme(legend_position='none', figure_size=(8,6))
        )

    if len(input_container_name_unique) == 2:
        save_as_pdf_pages([plot_plate1,plot_plate2], pdf_file_id + '-plate_map.pdf', verbose = False)
    else:
        plot_plate1.save(pdf_file_id + '-plate_map.pdf', verbose = False)

    # print final message.
    # warning messages if total volume or individial sample volumes is too high or too small.

    warning1a = False #over max available, total volume over MAX_TOTAL_VOLUME and under 2µl
    warning1b = False #over max available and total volume over 1500
    for i in range(total_sample_number):
        if sample_volumes[i] > max_vol_available and sum(sample_volumes) > MAX_TOTAL_VOLUME:
            for i in range(total_sample_number):
                if sample_volumes[i] < min_vol_required:
                    warning1a = True
                    break
                else:
                    warning1b = True
            break

    warning2a = False #sample pooling volumes over max available and under min required
    warning2b = False #sample pooling volumes over max available
    for i in range(total_sample_number):
        if sample_volumes[i] > max_vol_available:
            for i in range(total_sample_number):
                if sample_volumes[i] < min_vol_required:
                    warning2a = True
                    break
                else:
                    warning2b = True           
            break

    warning3 = False #volume over MAX_TOTAL_VOLUME. Individual sample volumes ok.
    for i in range(total_sample_number):
        if sum(sample_volumes) > MAX_TOTAL_VOLUME:
            warning3 = True
            break

    warning4 = False #sample volumes under min volume required
    for i in range(total_sample_number):
        if sample_volumes[i] < min_vol_required:
            warning4 = True
    
    if warning1a == True:
        print("--> WARNING: pooling volume(s) > {max} µl and < {min} µl, while total volume is over {maxtotal} ml. Consider making adjustments".format(max = str(max_vol_available),min = str(min_vol_required),maxtotal = str(MAX_TOTAL_VOLUME)))
        sys.exit(1)
    elif warning1b == True:
        print("--> WARNING: pooling volume(s) > {max} and total volume is over {maxtotal}. Consider making adjustments".format(max = str(max_vol_available),min = str(min_vol_required),maxtotal = str(MAX_TOTAL_VOLUME)))
        sys.exit(1)
    elif warning2a == True:
        print("--> WARNING: pooling volume(s) > {max} and < {min}. Consider making adjustments".format(max = str(max_vol_available),min = str(min_vol_required),maxtotal = str(MAX_TOTAL_VOLUME)))
        sys.exit(1)
    elif warning2b == True:
        print("--> WARNING: pooling volume(s) > {max}. Consider making adjustments".format(max = str(max_vol_available),min = str(min_vol_required),maxtotal = str(MAX_TOTAL_VOLUME)))
        sys.exit(1)
    elif warning3 == True:
        print("--> WARNING: total volume is over {maxtotal}. Consider making adjustments".format(max = str(max_vol_available),min = str(min_vol_required),maxtotal = str(MAX_TOTAL_VOLUME)))
        sys.exit(1)
    elif warning4 == True:
        print("--> WARNING: pooling volume(s) < {min}. Consider making adjustments".format(max = str(max_vol_available),min = str(min_vol_required),maxtotal = str(MAX_TOTAL_VOLUME)))
        sys.exit(1)
    else:
        print("--> Successfully created Biomek csv file for pooling")
        
#Run as EPP: python3 /opt/gls/clarity/customextensions/Biomek_pooling_VI.py {processLuid} {compoundOutputFileLuid1} {compoundOutputFileLuid2}
main(sys.argv[1], sys.argv[2], sys.argv[3])
