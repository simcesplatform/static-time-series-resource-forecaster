# static-time-series-resource-forecast

A simulation platform component used to simulate simple loads and generators forecaster whose published states are determined by a file containing a time series of attribute values for each epoch.

## Requirements

- python 3.7
- pip for installing requirements

## Usage

The component is based on the AbstractSimulationCompoment class from the [simulation-tools](https://github.com/simcesplatform/simulation-tools) repository. It is configured via environment variables which include common variables for all AbstractSimulationComponent subclasses such as rabbitmq connection and component name. Environment variables specific to this component are listed below:
- RESOURCE_FORECAST_COMPONENT_IDS (required): List names of forecasted resources. This information should match with csv file names that contain resource forecast state information. 
- RESOURCE_TYPES (required): List types of forecasted resources. Accepted values are Generator or Load.
- RESOURCE_FORECAST_STATE_CSV_FOLDER (required): Location of the folder that contains csv files. Csv files contain the resource forecast state information used in the simulation. Relative file paths are in relation to the current working directory.
- RESOURCE_STATE_CSV_DELIMITER (optional): Delimiter used in the csv file. The default is ",". 
- RESOURCE_TYPE (optional): Type of this resource. Default is "ResourceForecaster".
- RESOURCE_FORECAST_TOPIC (optional): The upper level topic under whose subtopics the resource states are published. If this environment variable is not present "ResourceForecastState" is used.
- FORECAST_HORIZON (optional): If this environment variable is not present then default "PT36H" is used. 
- UNIT_OF_MEASURE (optional): If this environment variable is not present then default "kW" is used. 


The csv file should contain columns: TimeIndex and RealPower. Each row (+ forecast horizon) containing values will then represent data for one epoch. There should be at least as many data rows as there will be epochs. In case epochs + forecast horizon exceeds number of data rows, then this component uses data from remaining rows. 

The component can be launched with:

    python -m resource_forecaster.component

Docker can be used with the included docker file

## Tests

The included unittests can be executed with:

    python -m unittest

This requires RabbitMQ connection information provided via environment variables as required by the AbstractSimulationComponent class. Tests can also be executed with docker compose:

    docker-compose -f docker-compose-test.yml up
    
After executing tests exit with ctrl-c and remove the test environment:

    docker-compose -f docker-compose-test.yml down -v


## Demo

The [demo](demo) directory includes everything required for running a docker compose based demo with this component which uses  all other base simulation platform components: simulation manager, log writer and log reader. It is based on a [similar demo](https://github.com/simcesplatform/Simulation-Manager/tree/master/docker-files) 
for the simulation manager which uses dummy components. This demo assumes that all required simulation platform repositories including this one are cloned under the same parent directory. A test simulation can then be launched from the demo directory by running:

    ./start_simulation.sh

Simulation parameters can be changed by modifying the env files in the env directory. The simulation includes one resource forecaster that forecasts load1 and generator1. The resource forecast state data they use are in the load1.csv and generator1.csv files. The simulation includes 5 epochs.

