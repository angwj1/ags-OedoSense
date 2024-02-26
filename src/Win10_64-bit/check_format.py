
"""
Create a function to:
1. check the format of the AGS data files and identify common problems/errors e.g.
    a. AGS files does not contain OED data (i.e. exact sheetname "CONG - AGS" and "CONS - AGS") --> error_files_1a
    b. Mismatch in number of tests recorded between "CONG - AGS" and "CONS - AGS" --> error_files_1b
    c. A numeric value (i.e. void ratio and stress) is incorrectly recorded or empty. --> error_files_1c_void && error_files_1c_stress
    d. A numeric value (i.e.preconsolidation pressure) is incorrectly recorded or empty. --> error_files_1d
2. print out the list of problems/errors with the AGS data files 

# code by Ang Wei Jian
# 19 Oct 2023
"""


# ### Imports
# Import libraries and write settings here.
import os
import pandas as pd
import numpy as np
from main import preprocess_oed_data
from main import preprocess_pc_data

def check_AGS_file_format(folder_path_input):

    # ### Definition of variables and parameters

    '''
    CONSTANT PARAMETERS
    '''
    # oedometer data (oed, e vs p)
    oed_sheet = 'CONS - AGS'
    oed_params = ['PROJ_ID','HOLE_ID', 'SAMP_REF', 'SPEC_DPTH', 'CONS_INCN', 'CONS_IVR', 'CONS_INCF','CONS_INCE'] 

    # preconsolidation data (pc)
    pc_sheet = 'CONG - AGS'
    pc_params = ['PROJ_ID', 'HOLE_ID', 'SAMP_REF', 'SPEC_DPTH','CONG_TYPE', 'CONG_COND', 'CONG_REM', 
                 'CONG_DIA', 'CONG_HIGT', 'CONG_MCI', 'CONG_MCF', 'CONG_BDEN', 'CONG_DDEN',
                 'CONG_SATR', 'CONG_IVR','CONG_PRCP']

    x='CONS_INCF'
    y='CONS_INCE'
    const='CONG_PRCP'

    error_files_1a = []
    error_files_1b = []
    error_files_1c_void = []
    error_files_1c_stress = []
    error_files_1d = []

    ### Error 1a:
    # AGS files does not contain OED data (i.e. exact sheetname "CONG - AGS" and "CONS - AGS")

    file_names_ags = [f for f in os.listdir(folder_path_input)
                      if os.path.isfile(os.path.join(folder_path_input, f))
                      if not f.startswith(".")
                      if not f.startswith("cleaned_data")]

    for file_name_ags in file_names_ags:
        file_path_ags = os.path.join(folder_path_input, file_name_ags)

        df = pd.ExcelFile(file_path_ags)
        sheetnames = df.sheet_names

        if ('CONS - AGS' not in sheetnames) or ('CONG - AGS' not in sheetnames):
            error_files_1a.append(file_name_ags)


    ### Error 1b:
    # Mismatch in number of tests recorded between "CONG - AGS" and "CONS - AGS"

    ### Error 1c and Error 1d:
    # c. A numeric value (i.e. void ratio and stress) is incorrectly recorded.
    # d. A numeric value (i.e.preconsolidation pressure, pc) is incorrectly recorded.

    for file_name_ags in file_names_ags:
        file_path_ags = os.path.join(folder_path_input, file_name_ags)
        print(file_name_ags)

        if file_name_ags not in error_files_1a:
            df_oed = pd.read_excel(file_path_ags, sheet_name=oed_sheet, header=6)  
            df_pc = pd.read_excel(file_path_ags, sheet_name=pc_sheet, header=6)
            
            # as not all AGS excel has the same format, pre-processing has to be done before appending df
            df_oed = preprocess_oed_data(df_oed, oed_params, file_name_ags)
            df_pc = preprocess_pc_data(df_pc, pc_params, file_name_ags)

            test_ids_oed = df_oed['TEST_ID'].unique()
            test_ids_pc = df_pc['TEST_ID'].unique()

            if len(test_ids_oed) != len(test_ids_pc): 
                extra_test_ids = set(test_ids_oed).symmetric_difference(set(test_ids_pc))
                error_file = file_name_ags + " ; EXTRA TEST ID(s): " + str(list(extra_test_ids))
                error_files_1b.append(error_file)

            else:
                for test_id in test_ids_pc:
                    print(test_id)
                    void = df_oed.loc[df_oed['TEST_ID'] == test_id, y].values
                    stress = df_oed.loc[df_oed['TEST_ID'] == test_id, x].values
                    pc = df_pc.loc[df_pc['TEST_ID'] == test_id, const].values[0]

                    # https://www.askpython.com/python/examples/nan-in-numpy-and-pandas
                    # https://stackoverflow.com/questions/52657223/typeerror-ufunc-isnan-not-supported-for-the-input-types-and-the-inputs-could

                    # CHECK for empty/missing values
                    # if np.isnan(void).sum() > 0:      # np.isnan won't work for object or string dtypes
                    if pd.isnull(void).sum() > 0:
                        error_file = test_id # + " ; FILENAME: " + file_name_ags
                        error_files_1c_void.append(error_file)
                    # if np.isnan(stress).sum() > 0:      # np.isnan won't work for object or string dtypes
                    if pd.isnull(stress).sum() > 0:
                        error_file = test_id # + " ; FILENAME: " + file_name_ags
                        error_files_1c_stress.append(error_file)
                    if np.isnan(pc) == 1:
                        error_file = test_id # + " ; FILENAME: " + file_name_ags
                        error_files_1d.append(error_file)

                     # CHECK for non-numeric values
                    try: 
                        void = pd.to_numeric(void, errors='raise')
                    except Exception:
                        error_file = test_id # + " ; FILENAME: " + file_name_ags
                        error_files_1c_void.append(error_file)
                        pass

                    try: 
                        stress = pd.to_numeric(stress, errors='raise')
                    except Exception:
                        error_file = test_id # + " ; FILENAME: " + file_name_ags
                        error_files_1c_stress.append(error_file)
                        pass

                    try: 
                        pc = pd.to_numeric(pc, errors='raise')
                    except Exception:
                        error_file = test_id # + " ; FILENAME: " + file_name_ags
                        error_files_1d.append(error_file)
                        pass


    ### Error 1a:
    # AGS files does not contain OED data (i.e. exact sheetname "CONG - AGS" and "CONS - AGS") --> error_files_1a
    print("Error 1a")
    print(error_files_1a)

    ### Error 1b:
    # Mismatch in number of tests recorded between "CONG - AGS" and "CONS - AGS" --> error_files_1b
    print("Error 1b")
    print(error_files_1b)

    ### Error 1c 
    # A numeric value (i.e. void ratio and stress) is incorrectly recorded or empty. --> error_files_1c_void && error_files_1c_stress
    print("Error 1c_void")
    print(error_files_1c_void)
    print("Error 1c_stress")
    print(error_files_1c_stress)

    ### Error 1d:
    # A numeric value (i.e.preconsolidation pressure, pc) is incorrectly recorded or empty. --> error_files_1d
    print("Error 1d")
    print(error_files_1d)

    return (error_files_1a, error_files_1b, error_files_1c_void, error_files_1c_stress, error_files_1d)

