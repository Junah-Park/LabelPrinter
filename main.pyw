# This program allows operators to automate label printing for IMU part labels
# Test inputs for GUI to dev server: sn: 1, sn: 3



# release.txt, main.pyw, and git tag
__version__ = '1.2.3'



# Constants
from automation1.constants import *

import os
# production line setting saved to json
import json
# Shutil copies files to a destination folder
import shutil

# GUI modules
import tkinter
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog

# Externally sourced autocomplete drop list selection widget for tkinter
from AutocompleteCombobox import AutocompleteCombobox

# Module that connects to the SQL database
from automation1.ConcordDBConnector import ConcordDBConnector
# Printing automation interface class
from LabelMaker import LabelMaker

# Error logging
from automation1.utilities import logs
import traceback

# Testing
# from automation1.TestManager import TestManager



log = logs() # calling log calls as object
log.logger = os.path.basename( __file__ )
log.initialize()



class DeviceGUI( ttk.Frame ):
    def __init__( self, master = None ):
        log.debug( LOG_ENTER )

        # main frame
        ttk.Frame.__init__( self, master )
        self._gui_root = master

        toplev = self.winfo_toplevel()
        toplev.title( 'Label Printer {}'.format( __version__ ) )     

        # Initialize empty frame objects
        self._mainframe = None

        # Class for connecting with the server
        self._server = ConcordDBConnector( log )
 
        # Get current production line from saved json
        # If file is unavailable or missing, initialize dict
        self._production_line = ""
        try:            
            with open( 'StationInfo.json' ) as info_file :
                self._station_info = json.load(info_file)
            # assign production line to station info if found, else blank
            if self._station_info:
                self._production_line = self._station_info[ "production_line" ]
            else:
                self._station_info = { "production_line" : "" }            
        except:
            log.debug( 
                "Error reading StationInfo.json: " + traceback.format_exc() 
            )
            self._station_info = { "production_line" : " " }
        # end try

        # Initialize display field names
        self._display_names = []
        self._display_values = []

        # Initialize template widgets
        self._label_template_label = None
        self._label_template_field = None

        # Initialize print label button
        self._print_label = None

        # Initialize label maker object variable
        self._lm = None

        # Create main interface
        if self._production_line:
            self.generateMain()
        else:
            self.createSetProduction()      

        log.debug( LOG_EXIT )
    # end function



    def generateMain( self ):
        log.debug( LOG_ENTER )

        # Create main frame if new
        self._mainframe=ttk.Frame( self._gui_root, padding = "12 12 12 12")
        self._mainframe.grid( column = 0, row = 0 )
        self._gui_root.columnconfigure( 0, weight = 1 )
        self._gui_root.rowconfigure( 0, weight = 1)

        # Serial number entry
        self._sn_entry = StringVar()
        self._sn_label = ttk.Label( self._mainframe, text = "Enter S/N:" )
        self._sn_label.grid( column = 0, row = 0 )
        self._sn_field = ttk.Entry(
            self._mainframe, textvariable = self._sn_entry
        )
        self._sn_field.grid( column = 0, row = 1 )
        self._sn_field.grid_configure( padx = 5, pady = 5 )

        # Continue button
        self._continue_button = ttk.Button(
            self._mainframe, text = "Generate fields", 
            command = lambda x = "<Generate>": self.generateFields( x ), 
            takefocus = 0
        )       
        self._continue_button.grid_configure( padx = 5, pady = 5 )
        self._continue_button.grid( column = 0, row = 2 )

        # Bind the Enter key to submit
        self._sn_field.bind( "<Return>", self.generateFields )

        # Focus on first field
        self._sn_field.focus()

        # Tools menu dropdown
        menubar = Menu(
            self._gui_root, background = 'white', foreground = 'black',
                activebackground = 'white', activeforeground = 'black'
        )  
        tools = Menu( 
            menubar, tearoff = False, background = 'white', foreground = 'black'
        )  
        tools.add_command(
            label = "Production Line", command = self.createSetProduction
        )  
        menubar.add_cascade( label = "Tools", menu = tools)
        self._gui_root.config( menu = menubar )

        log.debug( LOG_EXIT )
    # end function      



    def generateFields( self, e:str ):
        """
        generate text labels containing retrieved information from the database
        """
        log.debug( LOG_ENTER )

        # Attempt to retrieve data    
        if not self.getData():
            log.debug( "Data retrieval failed" )
            return
        # end if

        # If fields have already been created, clear the frame
        if self._display_names:
            for display_name in self._display_names:
                display_name.destroy()
            for display_value in self._display_values:
                display_value.destroy()
            self._display_names = []
            self._display_values = []
        # end if

        # Create fields to display
        index = 1
        for field_name, field_value in self._display_fields.items():
            if type( field_value ) is float:
                field_value = int( field_value )
            # end if
            self._display_names.append( 
                ttk.Label( self._mainframe, text = field_name )
            )
            self._display_names[-1].grid( column = index, row = 0 )
            self._display_values.append(
                ttk.Label( self._mainframe, text = field_value )
            )
            self._display_values[-1].grid( column = index, row = 1)
            index += 1
        # end for
        
        # Label selection dropdown
        if self._label_template_label:
            self._label_template_label.destroy()
        # end if
        self._label_template_label = ttk.Label(
            self._mainframe, text = "Template:"
        )
        self._label_template_label.grid( column = index, row = 0 )

        if self._label_template_field:
            self._label_template_field.destroy()
        # end if
        self._label_template_field = AutocompleteCombobox( self._mainframe )
        self._label_template_field.set_completion_list( self._template_names )
        self._label_template_field.grid( column = index, row = 1 )
        self._label_template_field.autocomplete( 
            self._template_names.index( self._primary_template_name )
        )
        self._label_template_field.lift()

        # Print label button
        if self._print_label:
            self._print_label.destroy()
        # end if
        self._print_label = ttk.Button(
            self._mainframe, text = "Print Label", 
            command = lambda x = "<Print Button>": self._printLabel( x ),
            takefocus = 0
        )       
        self._print_label.grid_configure( padx = 5, pady = 5 )
        self._print_label.grid( column = index + 1, row = 1 )
        self._label_template_field.focus()

        # Bind enter key to print method
        self._label_template_field.bind( "<Return>", self.printLabel )

        log.debug( LOG_EXIT )
    # end function



    def getData( self ) -> bool:
        """
        To generate UI fields and Label fields, we need a model id to get values
        from the database.
        Using model id, this function can retrieve:
        - display field names
        - display field values
        - label field names
        - label field values
        - primary template {name: paths}
        - secondary template {names: paths}
        Return:
            boolean (True if retrieval was successful, False if empty)
        """
        log.debug( LOG_ENTER )

        # Use serial number to get model id
        sn = self._sn_entry.get()
        self._model_id, self._display_fields, self._label_fields = \
            self._server.getFieldData( sn, self._production_line )
        
        # Fetched data error check
        invalid_data = []
        if self._model_id == None:
            log.debug( 'Model ID not found' )
            invalid_data.append( "Model ID" )
        # end if
        if not self._display_fields:
            log.debug( 'Display data not found' )
            invalid_data.append( "Display data" )
        # end if
        if not self._label_fields:
            log.debug( 'Label data not found' )
            invalid_data.append( "Label data" )
        # end if

        # Fetch primary template
        self._primary_template = self._server.getPrimaryTemplate( 
            self._model_id 
        )
        if not self._primary_template:
            log.debug( 'Primary template not found' )
            invalid_data.append( "Primary template" )
        # end if

        # Fetch dict of templates
        self._templates = self._server.getTemplates( self._model_id )
        if not self._templates:
            log.debug( 'Template data not found' )
            invalid_data.append( "Templates" )
        # end if

        # Display failed data retrievals
        if invalid_data:
            # Create the error message to display
            error_message = ""
            for field in invalid_data:
                error_message += field
                error_message += ", "
            error_box = messagebox.showerror(
                'Error', error_message[:-1] + " not found."
            )
            return False

        # Assign fetched data
        self._primary_template_name = list( self._primary_template.keys() )[0]
        self._primary_template_value = self._primary_template[
            self._primary_template_name
        ]
        self._template_names = sorted( list( self._templates.keys() ) )
        
        log.debug( LOG_EXIT )
        return True
    # end function
    
    

    def printLabel( self, e:str ):
        """
        Create and print a label using label maker
        """
        log.debug( LOG_ENTER )

        # Retrieve the selected template name and file path
        selected_template_name = self._label_template_field.get()
        
        # Create an instance of the label maker class
        self._lm = LabelMaker(
            log,
            self._label_fields, selected_template_name, 
            self._templates[ selected_template_name ], 
            self._production_line
        )
        
        # Update the csv file
        if not self._lm.updateCSV():
            log.debug( "updateCSV returned false" )            
            error_box = messagebox.showerror(
                'Error', 'Failed to write to csv'
            )

        # Print the template
        if not self._lm.printTemplate():
            log.debug( "printTemplate returned false" )            
            error_box = messagebox.showerror(
                'Error', 'Failed to write to print using BarTender'
            )

        # Refocus on SN text field
        self._sn_field.focus()

        log.debug( LOG_EXIT )
    # end function
    

    # Create a window for setting the production line
    def createSetProduction( self ):
        """
        Create an interface for setting production line
        """
        log.debug( LOG_ENTER )

        # Destroy main interface if present
        if self._mainframe:
            self._mainframe.destroy()
        
        # Create production line selection UI
        self._production_line_window = ttk.Frame( 
            self._gui_root, padding = "12 12 12 12"
        )
        self._production_line_window.grid( column = 0, row = 0 )
        self._gui_root.columnconfigure( 0, weight = 1 )
        self._gui_root.rowconfigure( 0, weight = 1 )
        
        # Get Production Line Names
        production_lines = self._server.getProductionLines()
        
        # Error check production line retrieval
        if not production_lines:
            error_box = messagebox.showerror(
                'Error', 'Production lines not found in the database'
            )
            return
        else:
            production_lines = sorted( production_lines )

        # Create production line selection frame
        self._production_frame = ttk.Frame( 
            self._gui_root, padding = "12 12 12 12"
        )
        self._production_frame.grid( column = 0, row = 0 )
        self._production_selection_label = ttk.Label(
            self._production_line_window, text = "Select Production Line:"
        )
        self._production_selection_label.grid( row = 0, column = 0 )
        self._production_selection_label.grid_configure( padx = 5, pady = 5 )
        self._production_line_selection=AutocompleteCombobox(
            self._production_line_window
        )
        self._production_line_selection.grid( row = 0, column = 1 )
        self._production_line_selection.grid_configure( padx = 5, pady = 5 )
        self._production_line_selection.set_completion_list( production_lines )  
        self._production_line_selection.autocomplete(
            production_lines.index( self._production_line )
        )
        self._production_line_enter = ttk.Button(
            self._production_line_window, 
            text = "Enter", 
            command = self.setProduction
        )
        self._production_line_enter.grid( row = 0, column = 2 )

        log.debug( LOG_EXIT )        
    # end function



    def setProduction( self ):        
        """
        Save production line setting using StationInfo.json
        """
        log.debug( LOG_ENTER )

        # Set variables to selected production line
        self._station_info[ "production_line" ] = \
            self._production_line_selection.get()
        self._production_line = self._station_info[ "production_line" ]

        # Write to the json file
        try:
            with open( 'StationInfo.json', 'w' ) as station_dumped :
                json.dump( self._station_info, station_dumped )
                log.debug("Production Line Saved:" + str( self._station_info ) )
        except:
            log.debug( 
                "Write to StationInfo.json failed: " + traceback.format_exc() 
            )
            messagebox.showerror( 'File Error', 'StationInfo.json not found' )
        # end try

        # Return to main UI
        self._production_line_window.destroy()
        self.generateMain()

        log.debug( LOG_EXIT )
    # end function



# MAIN
def main():
    root = Tk()

    app = DeviceGUI( master = root )
    app.mainloop()

    # app = DeviceGUI( master = root )
    # app.CreateWidgets()
    # app.mainloop()
# end main



if __name__ == '__main__':
    main()
# end if
