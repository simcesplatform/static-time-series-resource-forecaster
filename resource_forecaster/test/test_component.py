# -*- coding: utf-8 -*-
# Copyright 2021 Tampere University and VTT Technical Research Centre of Finland
# This software was developed as a part of the ProCemPlus project: https://www.senecc.fi/projects/procemplus
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Otto Hylli <otto.hylli@tuni.fi>
#            Antti Keski-Koukkari <antti.keski-koukkari@vtt.fi>

'''
Tests for the ResourceForecaster component.
'''

from typing import List, Tuple, Union, cast
import os 
import pathlib
import csv
import isodate

from tools.messages import AbstractMessage
from tools.message.block import TimeSeriesBlock, ValueArrayBlock
from domain_messages.resource_forecast import ResourceForecastPowerMessage 

from tools.tests.components import MessageGenerator, TestAbstractSimulationComponent

from resource_forecaster.component import create_component, RESOURCE_TYPES, \
                                    RESOURCE_FORECAST_COMPONENT_IDS, \
                                    RESOURCE_FORECAST_STATE_CSV_FOLDER, \
                                    FORECAST_HORIZON
from resource_forecaster.resource_forecast_state_source import ResourceForecastState, NoDataAvailableForEpoch

SIMULATION_EPOCHS=5

class ManagerMessageGenerator( MessageGenerator ):
    '''
    Custom generator for simulation manager messages. Has a 15 minute epoch.
    '''
    
    def __init__(self, simulation_id: str, process_id: str):
        '''
        Create a message generator with 60 minute epoch length.
        '''
        super().__init__( simulation_id, process_id )
        self.epoch_interval = 3600

class ResourceForecastStateMessageGenerator( MessageGenerator ):
    """Message generator for the tests. extended to produce the expected ResourceForecastState messages."""
    
    def __init__(self, simulation_id: str, process_id: str):
        super().__init__( simulation_id, process_id)
        # read expected resource states from csv.
        with open( pathlib.Path( __file__ ).parent.absolute() / 'test1.csv', newline = '', encoding = 'utf-8') as file:
            data = csv.DictReader( file, delimiter = ',' )
            forecast_horizon = isodate.parse_duration(os.environ[FORECAST_HORIZON])
            # for each epoch a tuple consisting of expected state and is a warning expected on that epoch.
            # epoch 0 has no state
            self.states = {}
            init = True
            i = 1
            series = []
            time_index_list = []
            if init:
                # Initialize first items for while loop
                row = next(data)
                current_time_index = isodate.parse_datetime(row['TimeIndex'])
                first_time_index = isodate.parse_datetime(row['TimeIndex'])
                time_index_list.append(row['TimeIndex'])
                series.append(float(row['RealPower']))
                while current_time_index < first_time_index + forecast_horizon:
                    row = next(data)
                    current_time_index = isodate.parse_datetime(row['TimeIndex'])
                    time_index_list.append(row['TimeIndex'])
                    series.append(float(row['RealPower']))
                init = False
                self.states[i] = ResourceForecastState( real_power = series, time_index = time_index_list,
                                                               unit_of_measure='kW', resource_id='test1')
            while i <= SIMULATION_EPOCHS:
                series = list(series)
                time_index_list = list(time_index_list)
                try:
                    i += 1
                    time_index_list.pop(0)
                    series.pop(0)
                    row = next(data)
                    time_index_list.append(row['TimeIndex'])
                    series.append(float(row['RealPower']))
                    self.states[i] = ResourceForecastState( real_power = series, time_index = time_index_list,
                                                               unit_of_measure='kW', resource_id='test1')
                except StopIteration:
                    raise NoDataAvailableForEpoch( 'The source csv file does not have any rows remaining.' )

    def get_resource_forecast_state_message(self, epoch_number: int, triggering_message_ids: List[str]) -> Union[ResourceForecastPowerMessage, None]:
        """Get the expected ResourceForecastPowerMessage for the given epoch."""
        if epoch_number == 0 or epoch_number >= len( self.states ):
            return None
        
        # get the resource forecast state for this epoch.
        state  = self.states[ epoch_number ]
        self.latest_message_id = next(self.id_generator)
        forecast = TimeSeriesBlock(TimeIndex=state.time_index,
                                  Series={
                                      "RealPower": ValueArrayBlock(
                                          UnitOfMeasure=state.unit_of_measure,
                                          Values=state.real_power)
                                      }
            )
        
        resource_forecast_state_message = ResourceForecastPowerMessage(**{
            "Type": "ResourceForecastState.Power",
            "SimulationId": self.simulation_id,
            "SourceProcessId": self.process_id,
            "MessageId": self.latest_message_id,
            "EpochNumber": epoch_number,
            "TriggeringMessageIds": triggering_message_ids,
            "ResourceId": state.resource_id,
            "Forecast": forecast
        })
            
        return resource_forecast_state_message

class TestResourceForecastComponent( TestAbstractSimulationComponent ):
    """Unit tests for ResourceForecaster component.""" 
    
    # the method which initializes the component
    component_creator = create_component
    message_generator_type = ResourceForecastStateMessageGenerator
    normal_simulation_epochs = SIMULATION_EPOCHS
    # use custom manager whose epoch length matches the test data.
    manager_message_generator = ManagerMessageGenerator( TestAbstractSimulationComponent.simulation_id, TestAbstractSimulationComponent.test_manager_name )
    
    # specify component initialization environment variables.
    os.environ[ RESOURCE_FORECAST_STATE_CSV_FOLDER ] = str('./resource_forecaster/test/')
    os.environ[ RESOURCE_TYPES ] = str('Load')
    os.environ[RESOURCE_FORECAST_COMPONENT_IDS] = str('test1')
    os.environ[FORECAST_HORIZON] = str('PT6H')
    
    def get_expected_messages(self, component_message_generator: ResourceForecastStateMessageGenerator, epoch_number: int, triggering_message_ids: List[str]) -> List[Tuple[AbstractMessage, str]]:
        """Get the messages and topics the component is expected to publish in given epoch."""
        if epoch_number == 0:
            return [
                (component_message_generator.get_status_message(epoch_number, triggering_message_ids), "Status.Ready")
                ]
            
        return [
            (component_message_generator.get_resource_forecast_state_message(epoch_number, triggering_message_ids), "ResourceForecastState." + os.environ[ RESOURCE_TYPES ] + "." + os.environ[RESOURCE_FORECAST_COMPONENT_IDS] ),
            (component_message_generator.get_status_message(epoch_number, triggering_message_ids), "Status.Ready")
        ]
        
    def compare_resource_forecast_state_message(self, first_message: ResourceForecastPowerMessage, second_message: ResourceForecastPowerMessage ):
        """Check that the two ResourceForecastPower messages have the same content."""
        self.compare_abstract_result_message(first_message, second_message)
        #
        self.assertEqual( first_message.resource_id, second_message.resource_id )
        # block checks
        first_message_block = first_message.forecast
        second_message_block = second_message.forecast
        self.assertListEqual( first_message_block.series['RealPower'].values, second_message_block.series['RealPower'].values )
        self.assertListEqual( first_message_block.time_index, second_message_block.time_index )
        self.assertEqual( first_message_block.series['RealPower'].unit_of_measure, second_message_block.series['RealPower'].unit_of_measure )
        
    def compare_message(self, first_message: AbstractMessage, second_message: AbstractMessage) -> bool:
        """Override the super class implementation to add the comparison of ResourceForecastPower messages."""
        if super().compare_message(first_message, second_message):
            return True

        if isinstance(second_message, ResourceForecastPowerMessage ):
            self.compare_resource_forecast_state_message(cast(ResourceForecastPowerMessage, first_message), second_message)
            return True

        return False
