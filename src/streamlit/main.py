
"""
Create the functions to:
1. read and preprocess AGS excel data
2. generate oedometer graphs
3. determine preconsolidation pressure objectively and plot relevants graphs (refer to "preconsolidation_pressure_calculations.py")
4. compute the % error between the calculated and recorded preconsolidation pressure (in AGS)
5. print out a list of critical tests which exceeded the error threshold

# code by Ang Wei Jian
# 16 Apr 2023
"""


# ### Imports
# Import libraries and write settings here.
import os
from io import BytesIO
import zipfile
import streamlit as st
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
# import matplotlib.backends.backend_pdf # import explicitly in order for pyinstaller to work - https://github.com/Nuitka/Nuitka/issues/827
import numpy as np
from preconsolidation_pressure_calculations import calculate_pc_Casagrande
from preconsolidation_pressure_calculations import calculate_pc_Oikawa
from preconsolidation_pressure_calculations import calculate_pc_MC



matplotlib.use('PDF')
# change the default interactive matplotlib backend to "non-interactive" PDF backend --> prevent memory leakage/overflow (results in segmentation fault i.e. exit code 11)
# http://datasideoflife.com/?p=1443
# https://matplotlib.org/stable/users/explain/backends.html

def main(ags_files, err_tol, calculate_pc, print_options, troubleshoot_mode, excel_file_name_cleaned = 'cleaned_data_ags_mode.xlsx'):

    hasError = False

    try:
        
        # ### Definition of variables and parameters

        '''
        CONSTANT PARAMETERS
        '''
        # oedometer data (e vs p)
        oed_sheet = 'CONS - AGS'
        oed_params = ['PROJ_ID','HOLE_ID', 'SAMP_REF', 'SPEC_DPTH', 'CONS_INCN', 'CONS_IVR', 'CONS_INCF','CONS_INCE'] 
        oed_params_full = ['Project ID', 'Borehole No.', 'Sample No', 'Specimen Depth (m)', 'Stress Increment No', 
                     'Initial Void Ratio', 'Stress At End Of Stress Increment/ Decrement (kN/m2)', 
                     'Void Ratio At End Of Stress Increment']

        # preconsolidation data (pc)
        pc_sheet = 'CONG - AGS'
        pc_params = ['PROJ_ID', 'HOLE_ID', 'SAMP_REF', 'SPEC_DPTH','CONG_TYPE', 'CONG_COND', 'CONG_REM', 
                     'CONG_DIA', 'CONG_HIGT', 'CONG_MCI', 'CONG_MCF', 'CONG_BDEN', 'CONG_DDEN',
                     'CONG_SATR', 'CONG_IVR','CONG_PRCP']
        pc_params_full = ['Project ID', 'Exploratory hole or location equivalent', 'Sample reference number ', 
                          'Specimen Depth (m)', 'Oedometer or Rowe, primary or secondary consolidation', 
                          'Sample condition', 'Test details including method statement', 'Test specimen diameter (mm)',
                          'Test specimen height (mm)', 'Initial moisture content (%)', 'Final moisture content (%)',
                          'Initial bulk density (Mg/m3)', 'Initial dry density (Mg/m3)', 'Initial degree of saturation (%)',
                          'Initial voids ratio', 'Preconsolidated pressure (kPa)']

        # produce legend for easy reference
        legend = zip(['oed_params'] + oed_params + ['pc_params'] + pc_params, 
                     [''] + oed_params_full + [''] + pc_params_full)

        for i, (param, param_full) in enumerate(legend):
            print(param + " : " + param_full)
            

        # ### Read Data
        # - Use a for loop to read and preprocess data
        # - As not all AGS excel file has the same format, the data has to be preprocessed in each for loop (instead of preprocessing only after the full dataframe is assembled).

        df_oeds = pd.DataFrame()
        df_pcs = pd.DataFrame()

        for ags_file in ags_files:
            file_name_ags = ags_file.name
            df_oed = pd.read_excel(ags_file, sheet_name=oed_sheet, header=6)  
            df_pc = pd.read_excel(ags_file, sheet_name=pc_sheet, header=6)
            
            # as not all AGS excel has the same format, pre-processing has to be done before appending df
            df_oed = preprocess_oed_data(df_oed, oed_params, file_name_ags)
            df_pc = preprocess_pc_data(df_pc, pc_params, file_name_ags)
            df_pc["FILE_NAME"] = file_name_ags
            
            # combine all data in multiple AGS excel files into one df
            df_oeds = pd.concat([df_oeds, df_oed], ignore_index=True)
            df_pcs = pd.concat([df_pcs, df_pc], ignore_index=True)
        
        # create a new column "ID" to number each row
        df_pcs.reset_index(inplace=True)
        df_pcs.rename(columns = {'index':'ID'}, inplace = True)
            
        print(df_oeds)
        print(df_oeds.shape)
        print(df_pcs)
        print(df_pcs.shape)

        df_merge = df_oeds.merge(df_pcs, how='left', on='TEST_ID')

        print(df_merge)
        print(df_merge.shape)

    except ValueError as err:
        st.error(f'Error!  \nType: {type(err)}  \nDescription: {err}  \nSheetname in Excel File "{file_name_ags}" does not follow AGS format.', icon="🚨")
        return 0, True, 0

    except KeyError as err:
        st.error(f'Error!  \nType: {type(err)}  \nDescription: {err}  \nHeader in Excel File "{file_name_ags}" does not follow AGS format.', icon="🚨")
        return 0, True, 0

    except Exception as err:
        st.error(f'Error!  \nType: {type(err)}  \nDescription: {err}  \nError found in Excel File "{file_name_ags}"', icon="🚨")
        return 0, True, 0


    try:

        # plotting preprocessed data and saving figures

        test_ids = df_merge['TEST_ID'].unique()
        pcs_ca = []
        errs_ca = []
        pcs_oi = []
        errs_oi = []
        pcs_mc = []
        errs_mc = []

        figs = []
        fig_names = []
        figs_ca = []
        fig_names_ca = []
        figs_oi = []
        fig_names_oi = []
        figs_mc = []
        fig_names_mc = []
        
        if "Casagrande's Method (1936)" in print_options:
            print_ca = True
        else:
            print_ca = False
        
        if "Oikawa's Method (1987)" in print_options:
            print_oi = True
        else:
            print_oi = False
        
        if "Maximum Curvature Method (Gregory et al., 2006)" in print_options:
            print_mc = True
        else:
            print_mc = False

        for test_id in test_ids:

            print(test_id)
            file_name = df_pcs.loc[df_pcs['TEST_ID'] == test_id, 'FILE_NAME'].iloc[0]

            ID = int(df_pcs.loc[df_pcs['TEST_ID'] == test_id, 'ID'].to_numpy())
            df_merge_subset = df_merge[df_merge['TEST_ID'] == test_id]

            # plot graph of void ratio against log (stress)
            output_fig, fig_name = plot_graph(df_merge_subset, title='{}_{} plot'.format(ID, test_id))
            figs.append(output_fig)
            fig_names.append(fig_name)

            if calculate_pc:
            # calculate preconsolidation pressure with Casagrande Method
                pc_ca, err_ca, output_fig_ca, fig_name_ca = calculate_pc_Casagrande(df_merge_subset, title='{}_{} Casagrande Method'.format(ID, test_id), x='CONS_INCF', y='CONS_INCE', const='CONG_PRCP', label_x=r"Effective Vertical Stress, $\sigma_v'$  [kPa]", label_y='Void Ratio, e [-]', printer=print_ca, troubleshoot_mode=troubleshoot_mode)
                if print_ca: 
                    figs_ca.append(output_fig_ca)
                    fig_names_ca.append(fig_name_ca)
                    
                pc_oi, err_oi, output_fig_oi, fig_name_oi = calculate_pc_Oikawa(df_merge_subset, title='{}_{} Oikawa Method'.format(ID, test_id), x='CONS_INCF', y='CONS_INCE', const='CONG_PRCP', label_x=r"Effective Vertical Stress, $\sigma_v'$  [kPa]",label_y='Log (1 + Void Ratio, e) [-]', printer=print_oi, troubleshoot_mode=troubleshoot_mode)
                if print_oi: 
                    figs_oi.append(output_fig_oi)
                    fig_names_oi.append(fig_name_oi)

                pc_mc, err_mc, output_fig_mc, fig_name_mc = calculate_pc_MC(df_merge_subset, title='{}_{} Maximum Curvature Method'.format(ID, test_id), x='CONS_INCF', y='CONS_INCE', const='CONG_PRCP', label_x=r"Effective Vertical Stress, $\sigma_v'$  [kPa]",label_y='Void Ratio, e [-]', printer=print_mc, troubleshoot_mode=troubleshoot_mode)        
                if print_mc:      
                    figs_mc.append(output_fig_mc)
                    fig_names_mc.append(fig_name_mc)

                print(pc_ca)
                print(err_ca)

                print(pc_oi)
                print(err_oi)

                print(pc_mc)
                print(err_mc)
                
                pcs_ca.append(pc_ca)
                errs_ca.append(err_ca)

                pcs_oi.append(pc_oi)
                errs_oi.append(err_oi)

                pcs_mc.append(pc_mc)
                errs_mc.append(err_mc)

    except ValueError as err:
        st.error(f'Error!  \nType: {type(err)}  \nDescription: {err}  \nA numeric value (i.e. void ratio and stress) in Test ID "{test_id}" in Excel File "{file_name}" is incorrectly recorded.', icon="🚨")
        return 0, True, 0

    except TypeError as err:
        st.error(f'Error!  \nType: {type(err)}  \nDescription: {err}  \nA numeric value (i.e.preconsolidation pressure) in Test ID "{test_id}" in Excel File "{file_name}" is incorrectly recorded.', icon="🚨")
        return 0, True, 0

    except Exception as err:
        st.error(f'Error!  \nType: {type(err)}  \nDescription: {err}  \nError found in Test ID "{test_id}" in Excel File "{file_name}"', icon="🚨")
        return 0, True, 0

    if calculate_pc:
        df_pcs, critical_list = process_error_info(df_pcs, pcs_ca, errs_ca, pcs_oi, errs_oi, pcs_mc, errs_mc, err_tol)
        print(f"{len(critical_list)} oedometer test(s) exceeded the error threshold of {err_tol}%")
        print("")
        print("\n".join(critical_list))
        print("")

        print("done")

    else:
        critical_list=[]
    
    zip_file = export_to_zip(df_pcs, df_oeds, excel_file_name_cleaned, figs, fig_names, figs_ca, fig_names_ca, figs_oi, fig_names_oi, figs_mc, fig_names_mc)

    return critical_list, hasError, zip_file
    



#########----------------------------

# ### Preprocess Data
# 1. preprocess oedometer data in excel_sheet = 'CONS - AGS'
# 2. preprocess preconsolidation pressure data in excel_sheet = 'CONG - AGS'


def preprocess_oed_data(df_oed, oed_params, file_name):
    
    # remove whitespaces from column headers
    df_oed.columns = [col_header.strip() for col_header in df_oed.columns]

    # filter out the important columns
    df_oed = df_oed[oed_params]

    # Drop the rows which only contain 'STOP' marker
    df_oed.dropna(subset=['SAMP_REF'],inplace=True)

    # to replace '/' so that HOLE_ID can be used in folder directory
    df_oed['HOLE_ID'] = [row.replace('/', '-') for row in df_oed['HOLE_ID'].astype('str')]
    # to forward fill missing value in column 'PROJ_ID'
    df_oed['PROJ_ID'].ffill(axis=0, inplace=True)
    # Create unique test id for each test
    df_oed['TEST_ID'] = file_name + '-' + df_oed['PROJ_ID'] + '-' + df_oed['HOLE_ID'] + "-" + df_oed['SAMP_REF']

    print(df_oed.shape)
    
    return df_oed


def preprocess_pc_data(df_pc, pc_params, file_name):

    # remove whitespaces from column headers
    df_pc.columns = [col_header.strip() for col_header in df_pc.columns]

    # filter out the important columns
    df_pc = df_pc[pc_params]

    # Drop the rows which only contain 'STOP' marker
    df_pc.dropna(subset=['SAMP_REF'],inplace=True)

    # to replace '/' so that HOLE_ID can be used in folder directory
    df_pc['HOLE_ID'] = [row.replace('/', '-') for row in df_pc['HOLE_ID'].astype('str')]
    # to forward fill missing value in column 'PROJ_ID'
    df_pc['PROJ_ID'].ffill(axis=0, inplace=True)
    # Create unique test id for each test
    df_pc['TEST_ID'] = file_name + '-' + df_pc['PROJ_ID'] + '-' + df_pc['HOLE_ID'] + '-' + df_pc['SAMP_REF']

    print(df_pc.shape)
    
    return df_pc


#########----------------------------

##### Process Error Information 
# 1. Calculate average error between recorded pc' and calculated pc' for all methods
# 2. Check if error tolerance is exceeded [Boolean: True if error exceeds threshold, else False]

def process_error_info(df, pcs_ca, errs_ca, pcs_oi, errs_oi, pcs_mc, errs_mc, err_tol):
    
    # error for Casagrande Method

    print(df)
    print(pcs_ca)

    df['PC_CA'] = pcs_ca
    df['ERR_CA'] = errs_ca

    # error for Oikawa Method
    df['PC_OI'] = pcs_oi
    df['ERR_OI'] = errs_oi


    # error for Maximum Curvature Method
    df['PC_MC'] = pcs_mc
    df['ERR_MC'] = errs_mc

    # calculate the average error
    df['AVG_ERR'] = (df['ERR_CA'] + df['ERR_OI'] + df['ERR_MC']) / 3

    # return True if avg error exceeds threshold OR avg error is NaN
    df['EXCEED_ERR_TOL'] = (abs(df['AVG_ERR']) > err_tol) | (df['AVG_ERR'].isnull())

    # print out the critical list which exceed error threshold
    critical_df = df[df['EXCEED_ERR_TOL'] == True]
    critical_list = critical_df['ID'].astype('str') + '_' + critical_df['TEST_ID']

    return df, critical_list

#########----------------------------


# ### Save Data to Excel File
# exporting preprocessed data

def export_to_zip(df_pcs, df_oeds, excel_file_name_cleaned, figs, fig_names, figs_ca, fig_names_ca, figs_oi, fig_names_oi, figs_mc, fig_names_mc):
    
    # Create a BytesIO object for the Excel file
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl', mode='w') as writer:
        df_pcs.to_excel(writer, "error summary", index=False, startrow=2)
    with pd.ExcelWriter(excel_buffer, engine='openpyxl', mode='a') as writer:
        df_oeds.to_excel(writer, "OED data (for info)", index=True, startrow=2)
    excel_buffer.seek(0)  # Reset the pointer to the beginning

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        ### Add Excel Files to the ZIP
        zf.writestr(excel_file_name_cleaned, excel_buffer.getvalue())
        # Add Matplotlib figures to the ZIP
        all_figs = figs + figs_ca + figs_oi + figs_mc
        all_fig_names = fig_names + fig_names_ca + fig_names_oi + fig_names_mc
         
        for i in range(len(all_figs)):
            zf.writestr(all_fig_names[i], all_figs[i].getvalue())
    
    # Reset the pointer to the start so that it can read all the binary content
    zip_buffer.seek(0)
    return zip_buffer


#########----------------------------

# ### Plot Graph
# Plot e vs log(p)

def plot_graph(df, title, x='CONS_INCF', y='CONS_INCE', const='CONG_PRCP',
               label_x=r"Effective Vertical Stress, $\sigma_v'$  [kPa]",
               label_y='Void Ratio, e [-]'):
    '''
    df: the dataframe to take from 
    x: column name in df of data x
    y: column name in df of data y
    label_x: name of x axis
    label_y: name of y axis
    '''

    # x - CONS_INCF : Stress At End Of Stress Increment/ Decrement (kN/m2)
    # y - CONS_INCE : Void Ratio At End Of Stress Increment
    # vertical constant line - CONG_PRCP : Recorded Preconsolidated pressure (kPa)

    # Prepare data
    # Convert df to Series to np Array
    stress = df[x].values
    void = df[y].values
    pc = df[const].values[0]
    pc_log = np.log10(pc)

    # Prepare figure
    fig, (ax1) = plt.subplots(nrows=1, figsize=(11.69,8.27))
    fig.suptitle(title, fontsize=16)

    ##### plot lines to determine pc_cs (for Casagrande Method)    
    # plot e-lg p (for Casagrande Method)
    ax1.plot(stress, void, '-s', color='grey', markerfacecolor='none')
    ax1.set_xscale('log')
    ax1.set_xlabel(label_x)
    ax1.set_ylabel(label_y)
    ax1.text(1, 0.99, f"recorded $\sigma_p'$ = {pc:.1f} kPa", 
        ha='right', va='top', transform=ax1.transAxes, color='g')

    
    # plot recorded preconsolidation pressure pc
    ax1.plot([pc, pc],[min(void),max(void)],'--g')
    
    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    fig_name = title + '.pdf'
    
    output_fig = BytesIO()
    fig.savefig(output_fig, format="pdf")
    output_fig.seek(0)
    plt.close(fig)

    return output_fig, fig_name



def manual_mode(ags_files, err_tol, calculate_pc, print_options, troubleshoot_mode, excel_file_name_cleaned = 'cleaned_data_manual_mode.xlsx'):

    hasError = False

    try:

        # ### Read Data
        # - Use a for loop to read and preprocess data
        df_oeds = pd.DataFrame()

        sheet_name = "main (to be updated)"

        for ags_file in ags_files:
            file_name_manual = ags_file.name
            df_oed= pd.read_excel(ags_file, sheet_name=sheet_name, header=6)  
            df_oed["FILE_NAME"] = file_name_manual
            df_oed["TEST_ID"] = file_name_manual + '-' + df_oed["TEST_ID"] 

            # combine all data in multiple excel files into one df
            df_oeds = pd.concat([df_oeds, df_oed], ignore_index=True)
            df_pcs = df_oeds.copy()
            df_pcs.dropna(axis=0, inplace=True)
            df_pcs = df_pcs[["FILE_NAME","TEST_ID","CONG_PRCP"]]

        # create a new column "ID" to number each row
        df_pcs.reset_index(drop=True, inplace=True)
        df_pcs.reset_index(inplace=True)
        df_pcs.rename(columns = {'index':'ID'}, inplace = True)

        # fill up missing values in "TEST_ID" and "CONG_PRCP" in df_oeds
        df_oeds.ffill(axis=0, inplace = True)

        print(df_oeds)
        print(df_oeds.shape)
        print(df_pcs)
        print(df_pcs.shape)

        df_merge = df_oeds

    except ValueError as err:
        st.error(f'Error!  \nType: {type(err)}  \nDescription: {err}  \nSheetname in Excel File "{file_name_manual}" does not follow Template format.', icon="🚨")
        return 0, True, 0

    except KeyError as err:
        st.error(f'Error!  \nType: {type(err)}  \nDescription: {err}  \nHeader in Excel File "{file_name_manual}" does not follow Template format.', icon="🚨")
        return 0, True, 0

    except Exception as err:
        st.error(f'Error!  \nType: {type(err)}  \nDescription: {err}  \nError found in Excel File "{file_name_manual}"', icon="🚨")
        return 0, True, 0

    try:

        # plotting preprocessed data and saving figures

        test_ids = df_merge['TEST_ID'].unique()
        pcs_ca = []
        errs_ca = []
        pcs_oi = []
        errs_oi = []
        pcs_mc = []
        errs_mc = []
        
        figs = []
        fig_names = []
        figs_ca = []
        fig_names_ca = []
        figs_oi = []
        fig_names_oi = []
        figs_mc = []
        fig_names_mc = []
        
        if "Casagrande's Method (1936)" in print_options:
            print_ca = True
        else:
            print_ca = False
        
        if "Oikawa's Method (1987)" in print_options:
            print_oi = True
        else:
            print_oi = False
        
        if "Maximum Curvature Method (Gregory et al., 2006)" in print_options:
            print_mc = True
        else:
            print_mc = False
        
        for test_id in test_ids:

            print(test_id)
            file_name = df_pcs.loc[df_pcs['TEST_ID'] == test_id, 'FILE_NAME'].iloc[0]
            print(file_name)

            ID = int(df_pcs.loc[df_pcs['TEST_ID'] == test_id, 'ID'].to_numpy())
            df_merge_subset = df_merge[df_merge['TEST_ID'] == test_id]

            # plot graph of void ratio against log (stress)
            output_fig, fig_name = plot_graph(df_merge_subset, title='{}_{} plot'.format(ID, test_id))
            figs.append(output_fig)
            fig_names.append(fig_name)

            if calculate_pc:
            # calculate preconsolidation pressure with Casagrande Method, Oikawa Method, Maximum Curvature Method
                pc_ca, err_ca, output_fig_ca, fig_name_ca = calculate_pc_Casagrande(df_merge_subset, title='{}_{} Casagrande Method'.format(ID, test_id), x='CONS_INCF', y='CONS_INCE', const='CONG_PRCP', label_x=r"Effective Vertical Stress, $\sigma_v'$  [kPa]", label_y='Void Ratio, e [-]', printer=print_ca, troubleshoot_mode=troubleshoot_mode)
                if print_ca: 
                    figs_ca.append(output_fig_ca)
                    fig_names_ca.append(fig_name_ca)

                pc_oi, err_oi, output_fig_oi, fig_name_oi = calculate_pc_Oikawa(df_merge_subset, title='{}_{} Oikawa Method'.format(ID, test_id), x='CONS_INCF', y='CONS_INCE', const='CONG_PRCP', label_x=r"Effective Vertical Stress, $\sigma_v'$  [kPa]",label_y='Log (1 + Void Ratio, e) [-]', printer=print_oi, troubleshoot_mode=troubleshoot_mode)
                if print_oi: 
                    figs_oi.append(output_fig_oi)
                    fig_names_oi.append(fig_name_oi)

                pc_mc, err_mc, output_fig_mc, fig_name_mc = calculate_pc_MC(df_merge_subset, title='{}_{} Maximum Curvature Method'.format(ID, test_id), x='CONS_INCF', y='CONS_INCE', const='CONG_PRCP', label_x=r"Effective Vertical Stress, $\sigma_v'$  [kPa]",label_y='Void Ratio, e [-]', printer=print_mc, troubleshoot_mode=troubleshoot_mode)  
                if print_mc:      
                    figs_mc.append(output_fig_mc)
                    fig_names_mc.append(fig_name_mc)

                print(pc_ca)
                print(err_ca)

                print(pc_oi)
                print(err_oi)

                print(pc_mc)
                print(err_mc)
                
                pcs_ca.append(pc_ca)
                errs_ca.append(err_ca)

                pcs_oi.append(pc_oi)
                errs_oi.append(err_oi)

                pcs_mc.append(pc_mc)
                errs_mc.append(err_mc)

    except ValueError as err:
        st.error(f'Error!  \nType: {type(err)}  \nDescription: {err}  \nA numeric value (i.e. void ratio and stress) in Test ID "{test_id}" in Excel File "{file_name}" is incorrectly recorded.', icon="🚨")
        return 0, True, 0

    except TypeError as err:
        st.error(f'Error!  \nType: {type(err)}  \nDescription: {err}  \nA numeric value (i.e.preconsolidation pressure) in Test ID "{test_id}" in Excel File "{file_name}" is incorrectly recorded.', icon="🚨")
        return 0, True, 0

    except Exception as err:
        st.error(f'Error!  \nType: {type(err)}  \nDescription: {err}  \nError found in Test ID "{test_id}" in Excel File "{file_name}"', icon="🚨")
        return 0, True, 0

    if calculate_pc:
        df_pcs, critical_list = process_error_info(df_pcs, pcs_ca, errs_ca, pcs_oi, errs_oi, pcs_mc, errs_mc, err_tol)
        print(f"{len(critical_list)} oedometer test(s) exceeded the error threshold of {err_tol}%")
        print("")
        print("\n".join(critical_list))
        print("")

        print("done")

    else:
        critical_list=[]
        
    zip_file = export_to_zip(df_pcs, df_oeds, excel_file_name_cleaned, figs, fig_names, figs_ca, fig_names_ca, figs_oi, fig_names_oi, figs_mc, fig_names_mc)

    return critical_list, hasError, zip_file


