# -*- coding: utf-8 -*-
# Copyright 2021 Tampere University and VTT Technical Research Centre of Finland
# This software was developed as a part of the ProCemPlus project: https://www.senecc.fi/projects/procemplus
# This source code is licensed under the MIT license. See LICENSE in the repository root directory.
# Author(s): Otto Hylli <otto.hylli@tuni.fi>
#            Antti Keski-Koukkari <antti.keski-koukkari@vtt.fi>

"""This module contains a class for keeping track of the simulation components."""

from typing import List
import tools.tools as tools
from resource_forecaster.resource_forecast_state_source  import CsvFileResourceForecastStateSource, CsvFileError

LOGGER = tools.FullLogger(__name__)

class SimulationComponents():
    """Keeps a list of components for the simulation."""

    def __init__(self):
        self.__components = {}
        LOGGER.debug("New SimulationComponents object created.")

    def add_component(self, component: str, resource_state_csv_folder: str, resource_forecast_state_csv_delimiter: str, 
                      forecast_horizon: str, unit_of_measure: str):
        """Adds a new component to the simulation component list.
           If the given component is already in the list, the function prints an error message."""
        if component not in self.__components:
            try:
                self.__components[component] = CsvFileResourceForecastStateSource(resource_state_csv_folder+component+".csv",
                                                                                       forecast_horizon, unit_of_measure,
                                                                                       resource_forecast_state_csv_delimiter)
                initialization_error = None
                LOGGER.info("Component: {:s} registered to SimulationComponents.".format(component))
            except CsvFileError as error:
                self.__components[component] = None
                initialization_error = f'Unable to create a csv file resource forecast state source for the component: {str( error )}'
                LOGGER.warning("Component: {:s} {:s}".format(component, initialization_error))
        else:
            LOGGER.warning("{:s} is already registered to the simulation component list".format(component_id))    

    def remove_component(self, component: str):
        """Removes the given component from the simulation component list.
           If the given component is not found in the list, the function prints an error message."""
        if self.__components.pop(component, None) is None:
            LOGGER.warning("{:s} was not found in the simulation component list".format(component))
        else:
            LOGGER.info("Component: {:s} removed from SimulationComponents.".format(component))
    
    def get_component(self, component):
        """Returns component object"""
        return self.__components[component]

    def get_component_list(self, latest_epoch_less_than=None) -> List[str]:
        """Returns a list of the registered simulation components."""
        if latest_epoch_less_than is None:
            return list(self.__components.keys())
        return [
            component
            for component, component_status in self.__components.items()
            if component_status.epoch_number < latest_epoch_less_than
        ]

    def __str__(self) -> str:
        """Returns a list of the component ids."""
        return ", ".join([
            "{:s}".format(
                component)
            for component, component_status in self.__components.items()
        ])