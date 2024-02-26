"""
Create a software (with GUI) named "AGS Checker - Oedometer" to:
- Read AGS Excel files
- Plot Oedometer Graphs
- Determine the Preconsolidation Pressure with Three Methods: 1. Casagrande Method, 2. Maximum Curvature Method (Gregory et al.), 3. Oikawa Method
- Check the Recorded Preconsolidation Pressure (in AGS) against the Calculated Preconsolidation Pressure

Instructions to use software:
1. Select the Input Folder containing the AGS Excel files 
2. Select the Output Folder that will store the Plotted Graphs and Results 
3. Adjust the Settings where necessary 
4. Generate Graphs

# Important reference
# https://stackoverflow.com/questions/1186789/how-to-call-a-python-2-script-from-another-python-2-script
# https://www.youtube.com/watch?v=LzCfNanQ_9c
# https://github.com/Sven-Bo/advanced-gui-with-usersettings-and-menubar
# https://github.com/PySimpleGUI/psgcompiler

# code by Ang Wei Jian
# 16 Apr 2023
"""

# show splash screen
if getattr(sys, 'frozen', False):
   import pyi_splash
   pyi_splash.update_text("Loading...")

import PySimpleGUI as sg

# ### Imports
# Import libraries and write settings here.
from pathlib import Path  
import pandas as pd 
import main
import os
from check_format import check_AGS_file_format

def resource_path():
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return base_path



def is_valid_path(filepath):
    if filepath and Path(filepath).exists():
        return True
    sg.popup_error("Filepath is not correct.")
    return False


def settings_window(settings):
    # ------ GUI Definition ------ #
    layout = [[sg.T("SETTINGS")],
              [sg.T("Calculate Preconsolidation Pressure?"),
               sg.Checkbox(' ',settings["Param"]["calculate_pc"], enable_events=True, key="-CALCULATE_PC-")],
              [sg.T("Error Tolerance (%):", s=15, justification="l"),
               sg.Slider(range=(0, 300), default_value=settings["Param"]["error_tolerance"], expand_x=True, orientation='horizontal', key='-ERROR_TOLERANCE-')],
              [sg.T("Superimpose Gradient and Curvature Plots?"),
               sg.Checkbox(' ',settings["Param"]["troubleshoot_mode"], key="-TROUBLESHOOT_MODE-")],
              [sg.T("Print Graphs for:")],
              [sg.Checkbox('Casagrande Method', settings["Param"]["print_casagrande"], key="-PRINT_CASAGRANDE-")],
              [sg.Checkbox('Maximum Curvature Method (Gregory et al.)', settings["Param"]["print_max_curvature"], key="-PRINT_MAXIMUM_CURVATURE-")],
              [sg.Checkbox('Oikawa Method', settings["Param"]["print_oikawa"], key="-PRINT_OIKAWA-")],
              [sg.B("Save Current Settings", s=20)]]

    window = sg.Window("Settings Window", layout, modal=True, use_custom_titlebar=True, finalize=True)

    if settings["Param"]["calculate_pc"] == False:
        window["-ERROR_TOLERANCE-"].update(disabled=True)
        window["-ERROR_TOLERANCE-"].Widget.config(troughcolor = 'grey')
        window["-PRINT_CASAGRANDE-"].update(disabled=True)
        window["-PRINT_MAXIMUM_CURVATURE-"].update(disabled=True)
        window["-PRINT_OIKAWA-"].update(disabled=True)
        window["-TROUBLESHOOT_MODE-"].update(disabled=True)

    while True:
        event, values = window.read()
        print(event)

        if event == sg.WINDOW_CLOSED:
            break
        if event == "-CALCULATE_PC-":
            if values["-CALCULATE_PC-"] == False:
                window["-ERROR_TOLERANCE-"].update(disabled=True)
                window["-ERROR_TOLERANCE-"].Widget.config(troughcolor = 'grey')
                window["-PRINT_CASAGRANDE-"].update(disabled=True)
                window["-PRINT_MAXIMUM_CURVATURE-"].update(disabled=True)
                window["-PRINT_OIKAWA-"].update(disabled=True)
                window["-TROUBLESHOOT_MODE-"].update(disabled=True)
            if values["-CALCULATE_PC-"] == True:
                window["-ERROR_TOLERANCE-"].update(disabled=False)
                window["-ERROR_TOLERANCE-"].Widget.config(troughcolor = sg.theme_slider_color())
                window["-PRINT_CASAGRANDE-"].update(disabled=False)
                window["-PRINT_MAXIMUM_CURVATURE-"].update(disabled=False)
                window["-PRINT_OIKAWA-"].update(disabled=False)
                window["-TROUBLESHOOT_MODE-"].update(disabled=False)

        if event == "Save Current Settings":
            settings["Param"]["calculate_pc"] = values["-CALCULATE_PC-"]
            settings["Param"]["error_tolerance"] = values["-ERROR_TOLERANCE-"]
            settings["Param"]["print_casagrande"] = values["-PRINT_CASAGRANDE-"]
            settings["Param"]["print_max_curvature"] = values["-PRINT_MAXIMUM_CURVATURE-"]
            settings["Param"]["print_oikawa"] = values["-PRINT_OIKAWA-"]
            settings["Param"]["troubleshoot_mode"] = values["-TROUBLESHOOT_MODE-"]

            # Display success message & close window
            sg.popup_no_titlebar("Settings saved!")
            break
        
    window.close()


def main_window():
    # ------ Menu Definition ------ #
    menu_def = [["Menu", ["About", "Help", "Exit"]]]


    # ------ GUI Definition ------ #
    layout = [[sg.MenubarCustom(menu_def, tearoff=False)],
              [sg.T("Input Folder:", s=17, justification="r"), sg.I(key="-IN-"), sg.FolderBrowse()],
              [sg.T("Output Folder:", s=17, justification="r"), sg.I(key="-OUT-"), sg.FolderBrowse()],
              [sg.T("Mode:", s=17, justification="r"), sg.Radio('AGS Format', "mode", key="-AGS_MODE-", default=True), sg.Radio('Manual Entry', "mode", key="-MANUAL_MODE-")],
              [sg.Exit(s=16, button_color="tomato"),sg.B("Settings", s=16), sg.B("Check AGS File Format", s=19), sg.B("Generate Graphs", s=16)]]

    window_title = settings["GUI"]["title"]
    window = sg.Window(window_title, layout, use_custom_titlebar=True)

    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, "Exit"):
            break
        if event == "Help":
            window.disappear()
            sg.popup(window_title, "Instructions",
                "1. Select the Input Folder containing the AGS Excel files \n2. Select the Output Folder that will store the Plotted Graphs and Results \n3. Adjust the Settings where necessary \n4. Check the format of the AGS files \n5. Generate Graphs \n", 
                grab_anywhere=True)
            window.reappear()
        if event == "About":
            window.disappear()
            sg.popup(window_title, "Version 2.0 - Built by Ang Wei Jian, 2023", 
                "Read AGS Excel files, Check File Format, Plot Oedometer Graphs, and Check the Recorded Preconsolidation Pressure against the Preconsolidation Pressure Calculated with Three Methods: \n1. Casagrande Method \n2. Maximum Curvature Method (Gregory et al.) \n3. Oikawa Method \n", 
                grab_anywhere=True)
            window.reappear()
        if event == "Settings":
            settings_window(settings)

        ##Call Function to generate oedometer graphs and obtain preconsolidation pressure
        if event == "Generate Graphs":
            if (is_valid_path(values["-IN-"])) and (is_valid_path(values["-OUT-"])):
                if values["-AGS_MODE-"] == True:
                    critical_list, hasError = main.main(folder_path_input=values["-IN-"], folder_path_output=values["-OUT-"], err_tol=float(settings["Param"]["error_tolerance"]), calculate_pc = settings["Param"]["calculate_pc"], print_ca = settings["Param"]["print_casagrande"], print_oi = settings["Param"]["print_oikawa"], print_mc = settings["Param"]["print_max_curvature"], troubleshoot_mode=settings["Param"]["troubleshoot_mode"], file_name_cleaned = 'cleaned_data_ags_mode.xlsx')
                elif values["-MANUAL_MODE-"] == True:
                    critical_list, hasError = main.manual_mode(folder_path_input=values["-IN-"], folder_path_output=values["-OUT-"], err_tol=float(settings["Param"]["error_tolerance"]), calculate_pc = settings["Param"]["calculate_pc"], print_ca = settings["Param"]["print_casagrande"], print_oi = settings["Param"]["print_oikawa"], print_mc = settings["Param"]["print_max_curvature"], troubleshoot_mode=settings["Param"]["troubleshoot_mode"], file_name_cleaned = 'cleaned_data_manual_mode.xlsx')

                if hasError==False:       
                # Display success message, list of critical tests that exceeded the error threshold & close window
                    if settings["Param"]["calculate_pc"] == True:
                        processed_crit_list = "\n*".join(critical_list)
                        sg.PopupScrolled(f'Graphs Generated! \n \nThe following {len(critical_list)} test(s) exceeded the error threshold of {float(settings["Param"]["error_tolerance"])}%: \n*{processed_crit_list}', title="Critical List of Tests which Exceeded Error Tolerance")
                    else:
                        sg.popup_no_titlebar('Graphs Generated!')

        ##Call Function to check AGS file format
        if event == "Check AGS File Format":
            if (is_valid_path(values["-IN-"])) and (is_valid_path(values["-OUT-"])):
                if values["-AGS_MODE-"] == True:
                    print("AGS OK!")
                    ### Error 1a:
                    # AGS files does not contain OED data (i.e. exact sheetname "CONG - AGS" and "CONS - AGS") --> error_files_1a
                    ### Error 1b:
                    # Mismatch in number of tests recorded between "CONG - AGS" and "CONS - AGS" --> error_files_1b
                    ### Error 1c 
                    # A numeric value (i.e. void ratio and stress) is incorrectly recorded. --> error_files_1c_void && error_files_1c_stress
                    ### Error 1d:
                    # A numeric value (i.e.preconsolidation pressure, pc) is incorrectly recorded. --> error_files_1d
                    error_files_1a, error_files_1b, error_files_1c_void, error_files_1c_stress, error_files_1d = check_AGS_file_format(folder_path_input=values["-IN-"])

                    AGS_error_text = "AGS File Format Checked! "

                    if len(error_files_1a) > 0:
                        processed_error_files_1a = "\n*".join(error_files_1a)
                        AGS_error_text = AGS_error_text + f'\n \nIn the following {len(error_files_1a)} AGS file(s), OED data (i.e. exact sheetname "CONG - AGS" and "CONS - AGS") cannot be found: \n*{processed_error_files_1a}'

                    if len(error_files_1b) > 0:
                        processed_error_files_1b = "\n*".join(error_files_1b)
                        AGS_error_text = AGS_error_text + f'\n \nIn the following {len(error_files_1b)} AGS file(s), there is a mismatch in number of tests recorded between "CONG - AGS" and "CONS - AGS" : \n*{processed_error_files_1b}'

                    if len(error_files_1c_void) > 0:
                        processed_error_files_1c_void = "\n*".join(error_files_1c_void)
                        AGS_error_text = AGS_error_text + f'\n \nIn the following {len(error_files_1c_void)} Test ID(s), there are empty or non-numeric values in "void ratio" column : \n*{processed_error_files_1c_void}'

                    if len(error_files_1c_stress) > 0:
                        processed_error_files_1c_stress = "\n*".join(error_files_1c_stress)
                        AGS_error_text = AGS_error_text + f'\n \nIn the following {len(error_files_1c_stress)} Test ID(s), there are empty or non-numeric values in "stress" column : \n*{processed_error_files_1c_stress}'

                    if len(error_files_1d) > 0:
                        processed_error_files_1d = "\n*".join(error_files_1d)
                        AGS_error_text = AGS_error_text + f'\n \nIn the following {len(error_files_1d)} Test ID(s), there are empty or non-numeric values in "pre-consolidation pressure" column : \n*{processed_error_files_1d}'

                    sg.PopupScrolled(AGS_error_text, title="List of AGS Files with Errors")

                elif values["-MANUAL_MODE-"] == True:
                    sg.popup_no_titlebar('File Format can only be checked for AGS Files.')

    window.close()


if __name__ == "__main__":

    # SETTINGS_PATH = Path.cwd()
    SETTINGS_PATH = resource_path()
    # create the settings object and use ini format
    settings = sg.UserSettings(
        path=SETTINGS_PATH, filename="config.ini", use_config_file=True, convert_bools_and_none=True
    )
    theme = settings["GUI"]["theme"]
    font_family = settings["GUI"]["font_family"]
    font_size = int(settings["GUI"]["font_size"])
    sg.theme(theme)
    sg.set_options(font=(font_family, font_size))

    if getattr(sys, 'frozen', False):
    	pyi_splash.close()
	
    main_window()

