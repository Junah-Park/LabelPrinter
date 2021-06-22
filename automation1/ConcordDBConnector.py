# This module provides methods to handle data fetched from the server
# systsql01\dev for production server



import os
import pyodbc
import traceback
from automation1.utilities import logs
from automation1.DatabaseManagerSQL import DatabaseManagerSQL
from automation1.constants import *



# Database connection parameters contained in dict
db_info_concord_label_dev = {
    'SERVER':'####\####',
    'USER': '####',
    'PW': '####',
    'DB': '####'
}

db_info_concord_label_prod = {
    'SERVER':'####',
    'USER': '####',
    'PW': '####',
    'DB': '####'
}



class ConcordDBConnector():
    """
    Connector class interface for encapsulating data retrieval and processing
    """
    def __init__( self, logger ):
        self._logger = logger
        self._logger.debug( LOG_ENTER )

        # Connect to main server and database
        try:
            self._db_manager = DatabaseManagerSQL(
                db_info_concord_label_dev['SERVER'],
                db_info_concord_label_dev['USER'],
                db_info_concord_label_dev['PW'],
                db_info_concord_label_dev['DB'] 
            )
            self._db_manager.Connect()
        except:
            self._logger.debug(
                "Constructor connection error: " + traceback.format_exc()
            )

        # Cached database connection
        self._sn_db = None
        self._server_name = None
        self._db_name = None

        self._logger.debug( LOG_EXIT )
    # end function



    def connectTo(
        self, server_name:str, user:str, pw:str, db_name:str,
    ) -> bool:
        """        
        Connect to specified database if the desired connection has changed
        Returns:
            boolean successful connection status
        """
        if server_name == self._server_name and db_name == self._db_name:
            return True
        else:
            try:
                if self._sn_db:
                    self._sn_db.Disconnect()
                # end if
                self._sn_db = DatabaseManagerSQL( 
                    server_name, user, pw, db_name 
                )
                self._sn_db.Connect()
                self._server_name = server_name
                self._db_name = db_name                
            except:
                self._logger.debug(
                    "Error connecting to the desired database: " + \
                        traceback.format_exc()
                )
                return False
            # end try
        # end if
        return True



    def getFieldData( self, sn:str, production_line_name:str ) -> list:
        
        """
        Uses serial number and production line name to get data

        sn contains the serial number
        production_line_name is a string, name of the production line

        Returns:
        [
            model_id:str
            display:dict - dictionary of values to display to UI
            label:dict - dictionary of values to print on the label
        ]
        
        """
        self._logger.debug( LOG_ENTER )
    
        # Call functions to get parameters
        model_id = self.getModelID( sn, production_line_name )
        display = self.getDisplayData( sn, model_id )
        label = self.getLabelData( sn, model_id )

        self._logger.debug( LOG_EXIT )

        return [ model_id, display, label ]
        # end try



    def getModelID( self, sn:str, production_line_name:str ) -> str:
        """
        This method establishes a database connection while fetching a model id
        Returns:
            model_id:str
        """
        self._logger.debug( LOG_ENTER )

        # Retrieve sn replacement token, Production Line ID, and Model query
        # as well as credentials for connecting to db containing the model
        try:
            returnValue = self._db_manager.ExecQuery(
                "SELECT FactorySNValueToken, ProductionLineID, \
                    ModelLookupQuery, ServerName, DBName, [User], Password \
                        FROM dbo.ProductionLine WHERE ProductionLineName='" + \
                        production_line_name + "'"
            )
        except:
            self._logger.debug(
                "Error retrieving connection data from ProductionLine table: " \
                    + traceback.format_exc()
            )
            return None
        # end try

        # Value check and pulling out data from the list
        if returnValue:
            returnValue = returnValue[0]
        else:
            return None
        self._logger.debug( returnValue )

        # Spread fetched parameters
        token, production_line_id, model_lookup, server_name, db_name, user, pw\
                = returnValue

        model_lookup = model_lookup.replace( token, sn )


        # Connect to the server and database containing the model
        self.connectTo(server_name, user, pw, db_name)

        # Get model using retrieved query
        try:
            model = self._sn_db.ExecQuery( model_lookup )[0][0]
        except:
            self._logger.debug(
                "Connection error while retrieving model name: " + \
                    traceback.format_exc()
            )
            return None
        # end try
        
        # Get Model ID
        try:
            model_id = self._db_manager.ExecQuery(
                "SELECT ModelID FROM [ProductLabelDev1].[dbo].[Model] WHERE \
                    ModelName='" + model + "'"
            )
        except:
            self.logger.debug(
                "Connection error while retrieving model id: " + \
                    traceback.format_exc()
            )
            return None
        
        # Value check and pulling out data from the list
        if model_id:
            model_id = model_id[0][0]
        else:
            self._logger.debug( "Model ID query returned empty" )
            return None

        self._logger.debug( LOG_EXIT )

        return model_id




    def getDisplayData( self, sn:str, model_id:str ) -> dict:
        """
        uses serial number and model id to fetch display data
        Returns:
            display:dict a dictionary of feature names and values of item info
            to display to the UI
        """
        self._logger.debug( LOG_ENTER )
    
        # Get the query that retrieves data for populating the UI    
        try:
            display_query = self._db_manager.ExecQuery(
                "SELECT DisplayFieldQuery FROM \
                    [ProductLabelDev1].[dbo].[ModelLabel] \
                        WHERE ModelID='" + str( model_id ) + "'"
            )
        except:
            self._logger.debug(
                "Error while getting the display data query: " + \
                    traceback.format_exc()
            )
            return {}
        # end try

        # Value check and pulling out data from the list
        if display_query:
            display_query = display_query[0][0]
        else:
            self._logger.debug(
                "Fetching query for retrieving display data returned empty:"
            )
            return {}

        # Replace token in query with serial
        display_query = display_query.replace( '#SN#', sn )   
        
        # Execute the query for fetching values
        display_values = self._sn_db.ExecQuery( display_query )
        if display_values:
            display_values = display_values[0]
        else:
            self._logger.debug( "Display data query returned empty:" )
            return {}
        
        # Parse query for column names
        start = 'SELECT '
        end = ' FROM'
        display_query = display_query[
            display_query.find( start ) + \
                len( start ):display_query.rfind( end )
            ]
        display_names = display_query.split( ',' )

        # Create and return a dictionary
        display = {}

        for i in range( len( display_values ) ):
            display[ display_names[i] ] = display_values[i]

        self._logger.debug( LOG_EXIT )
        return display
    # end function



    def getLabelData( self, sn:str, model_id:str ) -> dict:
        """
        uses serial number and model id to fetch label data
        Returns:
            label:dict a dictionary of feature names and values of item info
            to populate the label template
        """
        self._logger.debug( LOG_ENTER )
    
        # Get the query that retrieves data for populating the UI    
        try:
            label_query = self._db_manager.ExecQuery(
                "SELECT LabelFieldQuery FROM \
                    [ProductLabelDev1].[dbo].[ModelLabel] \
                        WHERE ModelID='" + str( model_id ) + "'"
            )
        except:
            self._logger.debug(
                "Error while getting the label data query: " + \
                    traceback.format_exc()
            )
        # end try
        
        # Value check and pulling out data from the list
        if label_query:
            label_query = label_query[0][0]
        else:            
            self._logger.debug(
                "Fetching query for retrieving label data returned empty"
            )
            return {}
        # end if

        # Replace token in query with serial
        label_query = label_query.replace( '#SN#', sn )            
        
        # Execute the query for fetching values
        label_values = self._sn_db.ExecQuery( label_query )
        if label_values:
            label_values = label_values[0]
        else:
            self._logger.debug( "Label data query returned empty" )
            return {}
        # end if
        
        # Parse query for column names
        start = 'SELECT '
        end = ' FROM'
        label_query = label_query[
            label_query.find( start ) + \
                len( start ):label_query.rfind( end )
            ]
        label_names = label_query.split( ',' )

        # Create and return a dictionary
        label = {}
        for i in range( len( label_values ) ):
            label[ label_names[i] ] = label_values[i]
        # end for

        self._logger.debug( LOG_EXIT )
        return label
    # end function



    def getPrimaryTemplate( self, model_id:str ) -> dict:
        """
        Uses model id to get the primary template name and path as dict
        Returns:
            {
                template_name(str): template_path(str)
            }
        """
        self._logger.debug( LOG_ENTER )

        try:
            # Get template information
            template = self._db_manager.ExecQuery(
                "SELECT TemplateName, TemplatePath FROM [dbo].[ModelLabel] \
                    WHERE ModelID='" + str( model_id ) \
                        + "' AND LabelName='Primary'")
        except:
            self._logger.debug(
                "Error retrieving primary template: " + traceback.format_exc()
            )
            return {}
        # end try
        
        # Value check
        if template:
            template_name = template[0][0]
            template_path = template[0][1]
        else:
            self._logger.debug( "Primary template query returned empty" )
            return {}
        # end try

        self._logger.debug( LOG_EXIT )
        return { template_name: template_path }
    # end function



    def getTemplates( self, model_id:str ) -> dict:
        """
        Uses model id to return a dictionary of template names mapped to paths
        Returns:
            dict of template_name:template_path
        """
        # Get all templates attached to model
        try:
            templates = self._db_manager.ExecQuery(
                "SELECT TemplateName, TemplatePath FROM [dbo].[ModelLabel] \
                    WHERE ModelID='" + str( model_id ) + "'")
        except:
            self._logger.debug(
                "Error retrieving templates: " + traceback.format_exc()
            )
            return {}
        # end try

        # Create and return a dictionary of templates
        template_dict = {}
        if templates:
            for template_name, template_path in templates:
                template_dict[ template_name ] = template_path
        else:
            self._logger.debug( "Templates retrieval returned empty" )            
            return {}
        
        self._logger.debug( LOG_EXIT )
        return template_dict
    # end function



    def getProductionLines( self ) -> list:
        """
        Connect to ProductionLabel database and retrieve Production Lines
        Returns:
            production_lines:list
        """
        self._logger.debug( LOG_ENTER )

        try:
            # Connect to product label database
            production_lines = self._db_manager.ExecQuery(
                "SELECT DISTINCT ProductionLineName FROM [dbo].ProductionLine"
            )
        except:
            self._logger.debug(
                "Error retrieving production lines: " + traceback.format_exc()
            )
            return []
        # end try

        
        # Value check
        if production_lines:
            production_lines = list( production_lines[0] )        
        else:
            self._logger.debug( "Production lines retrieval returned empty" )
            return []
            
        self._logger.debug( LOG_EXIT )
        return production_lines
    # end function
