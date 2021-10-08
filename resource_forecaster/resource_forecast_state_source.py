# -*- coding: utf-8 -*-
# Copyright 2021 Tampere University and VTT Technical Research Centre of Finland
# This software was developed as a part of the ProCemPlus project: https://www.senecc.fi/projects/procemplus
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Otto Hylli <otto.hylli@tuni.fi>
#            Antti Keski-Koukkari <antti.keski-koukkari@vtt.fi>

'''
Contains classes related to reading the resource forecast state from a csv file.
'''
import isodate
import csv

from dataclasses import dataclass

@dataclass
class ResourceForecastState():
    '''
    Represents resource forecast state read from the csv file.
    ''' 
    
    unit_of_measure: str
    time_index: list
    real_power: list
    resource_id: str


class CsvFileError(Exception):
    '''
    CsvFileResourceForecastStateSource was unable to read the given csv file or the file was missing a required column.
    '''    

class NoDataAvailableForEpoch( Exception ):
    """Raised by CsvFileResourceForecastDataSource.getNextEpochData when there is no more ResourceForecastStates available from the csv file."""
    
class CsvFileResourceForecastStateSource():
    '''
    Class for getting resource forecast states from a csv file.
    '''
    
    def __init__(self, file_name: str, forecast_horizon: str, unit_of_measure: str, delimiter: str = ","):
        '''
        Create object which uses the given csv file that uses the given delimiter.
        Raises CsvFileError if file cannot be read e.g. file not found, or it is missing required columns.
        '''
        self._initial_state = True
        self._unit_of_measure = unit_of_measure
        self._file = None # required if there is no file and the __del__ method is executed
        try:
            self._file = open( file_name, newline = "")
            
        except Exception as e:
            raise CsvFileError( f'Unable to read file {file_name}: {str( e )}.' )
        
        self._csv = csv.DictReader( self._file, delimiter = delimiter )
        # check that self._csv.fieldnames has required fields
        required_fields = set( [ 'TimeIndex', 'RealPower'])
        fields = set( self._csv.fieldnames )
        # missing contains fields that do not exist or is empty if all fields exist.
        missing = required_fields.difference( fields )
        if len( missing ) > 0:
            raise CsvFileError( f'Resource state source csv file missing required columns: {",".join( missing )}.' )
        
        # "If the ISO date string does not contain years or months, a timedelta instance is returned, else a Duration instance is returned."
        self._forecast_horizon = isodate.parse_duration(forecast_horizon)
        
        self._state = None
        
    def __del__(self):
        '''
        Close the csv file when this object is destroyed.
        '''
        if self._file != None:
            self._file.close()
        
    def getNextEpochData(self, epoch_message, component) -> ResourceForecastState:
        '''
        Get resource forecast i.e. read the next csv file for forecast horizon and return its contents.
        Raises NoDataAvailableForEpoch if the csv file has no more rows.
        Raises ValueError if a value from the csv file cannot be converted to the appropriate data type.
        Returns remaining rows if simulation is ending. 
        '''
        epoch_start_time = isodate.parse_datetime(epoch_message.start_time)
        
        values = {} # values for ResourceForecastState attributes
        values['resource_id'] = component
        values['unit_of_measure'] = self._unit_of_measure
        
        if self._initial_state:
            # Initialize first items for while loop
            time_index = []
            series = []
            try:
                row = next(self._csv)
                current_time_index = isodate.parse_datetime(row['TimeIndex'])
                if current_time_index == epoch_start_time:
                    time_index.append(row['TimeIndex'])
                    series.append(float(row['RealPower']))
                elif current_time_index > epoch_start_time:
                    raise NoDataAvailableForEpoch( 'The source csv file does not have data for this epoch start time.')
            except StopIteration:
                raise NoDataAvailableForEpoch( 'The source csv file does not have any rows remaining.' )
            
            # Collect rest of the items
            try:
                while current_time_index < epoch_start_time + self._forecast_horizon:
                    row = next(self._csv)
                    current_time_index = isodate.parse_datetime(row['TimeIndex'])
                    if current_time_index >= epoch_start_time:
                        time_index.append(row['TimeIndex'])
                        series.append(float(row['RealPower']))
            except StopIteration:
                raise NoDataAvailableForEpoch( 'The source csv file does not have any rows remaining.' )
            
            values['time_index'] = time_index
            values['real_power'] = series
            self._initial_state = False
        else:
            try:
                time_index = self._state.time_index
                time_index.pop(0)
                series = self._state.real_power
                series.pop(0)
                row = next(self._csv)
                time_index.append(row['TimeIndex'])
                series.append(float(row['RealPower']))
                values['time_index'] = time_index
                values['real_power'] = series
            except StopIteration:
                # Simulation ending. Return last rows until the end. Might want to implement check if last row in csv instead of this
                values['time_index'] = time_index
                values['real_power'] = series
        
        self._state = ResourceForecastState( **values )
        return self._state