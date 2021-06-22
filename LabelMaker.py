# This module provides a print automation inteface
#
# The LabelMaker class is passed a dict of entries and a database connection
# 1. Collects data from the database
# 2. Produces an excel file with collected data
# 3. Populates the bartender template
# 4. Sends a print command to BarTender

import win32com.client
import os
import csv
import traceback
from automation1.utilities import logs
from automation1.constants import LOG_ENTER, LOG_EXIT



class LabelMaker():
    def __init__ ( 
        self, logger, label_fields:dict, template_name:str, template_path:str, 
        server
    ):
        """
        label_fields is a dictionary of field names: values
        template_path is the file path of the btw file
        template_name is the file name of the btw file
        server is a connection class, connection to database is passed to LabelMaker
        """
        self._logger = logger
        self._logger.debug( LOG_ENTER )
        
        self._template_name = template_name
        self._template_path = template_path
        self._server = server
        self._barapp = None

        # Initialize an array of names to map label fields in btw to the csv
        self._label_names = []
        self._label_values = []
        for label_name, label_value in label_fields.items():
            if type( label_value ) is float:
                label_value = int( label_value )
            self._label_names.append( label_name )
            self._label_values.append( label_value )
        # end for

        self._logger.debug( LOG_EXIT )
    # end function



    def updateCSV( self ) -> bool:
        """
        This function populates the csv file read by BarTender
        The csv file should share the same directory as the btw
        Returns:
            boolean status check
        """
        self._logger.debug( LOG_ENTER )

        # Initialize csv file path
        csv_path = self._template_path + self._template_name[:-3] + "csv"
        if not os.path.isfile( csv_path ):
            self._logger.debug( "Path name error" )
            return False
        else:
            self._logger.debug( "Path successful" )
        
        # Update csv file
        try:
            with open( csv_path, 'w', newline = '' ) as csv_file:
                csvwriter = csv.writer( csv_file )
                # write the field names
                csvwriter.writerow( self._label_names )
                # write the data rows
                csvwriter.writerow( self._label_values )
            # end with
        except:
            self._logger.debug( "Write to csv failed:" + traceback.format_exc() )
            return False
        # end try

        self._logger.debug( LOG_EXIT )
        return True   
    # end function



    def printTemplate(self) -> bool:
        """        
        Bartender uses the default printer specified in the template file
        This function opens BarTender and prints labels using field information
        in the csv document.
        The csv must have field names mapped to the template fields through the 
        BarTender program.
        Returns:
            boolean status check
        """
        self._logger.debug( LOG_ENTER )
        # Open the bar object
        if not self._barapp:
            try:
                self._barapp = win32com.client.Dispatch(
                    'BarTender.Application' 
                )
                self._barapp.Visible = True
            except:
                self._logger.debug(
                    "Error connecting to BarTender: " + traceback.format_exc()
                )
                return False
            # end try
        
        # Open the template with BarTender
        try:
            barformat = self._barapp.Formats.Open(
                self._template_path + self._template_name, False, ''
            )
        except:
            self._logger.debug(
                "Error opening BarTender template:" + traceback.format_exc()
            )
            return False
        # end try

        # Print the template with BarTender
        try:
            barformat.PrintOut( False, False )
        except :
            self._logger.debug(
                "Error sending print command" + traceback.format_exc()
            )
            return False
        # end try

        self._logger( LOG_EXIT )
        return True
    # end function