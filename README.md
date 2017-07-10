# GTFS-Realtime to database

TfNSW-GTFSrDB loads GTFS-realtime data from TfNSW and store it in a specified database. It supports 3 types of GTFS-realtime feeds:

* TripUpdates
* VehiclePositions
* Service Alerts

## Getting Started
These instructions will get you a copy of the project up and running on your local machine or a server for developement and testing purposes.
 
### Prerequisites
TfNSW-GTFSrDB requires Python 2.7.
Below is a list of Python packages required to be installed for this project (these packages are not included as part of Python standard library):

* protobuf
* sqlalchemy
* pytz
* psycopg2

To install the aforementioned python packages, enter the following command in the command prompt:

```
pip install <Package_name>
```


### Installation
1. Clone or download the project [here](#https://github.com/tarasutjarittham/TfNSW_GTFSRDB)
2. Go to the project directory by enter:
```
cd <path_to_the_project>
```
3. Run gtfsrdb_tfnsw.py script (please see the section below for details)


## Usage

### Input List
Following is a list of input available:

* `-t` OR `--trip-updates`: Specify TripUpdates URI
* `-p` OR `--vehicle-positions`: Specify VehiclePositions URI
* `-a` OR `--alerts`: Specify Alerts URI
* `-d` OR `--database`: Specify datavase url
* `-o` OR `--discard-old`: Specify to discard old data to keep the database uptodate
* `-c` OR `--create-tables`: Create tables in the database if not currently exist
* `-w` OR `--wait`: Specify number of seconds before the next request starts
* `-1` OR `--once`: Specify if the request is to be run only once
* `-k` OR `--apikey`: Specify API Key registered with TfNSW
* `-m` OR `--mode`: Specify which mode of transportation is being queried. This will be added in a new field for the table (The aim for this is to store all the data from all mode of transportaion e.g. bus, train, lightrail, in a single table for the same type of GTFS feed)


### Example Use

**Case1:** Load GTFS-realtime bus positions and store it in a database named mydb3 (note that if you are using postgresql database the database has to be pre-created). The request will run every 30 second (default wait time) and new data is append to the table. 

```
python gtfsrdb_tfnsw.py -p 'https://api.transport.nsw.gov.au/v1/gtfs/vehiclepos/buses' --database="postgresql://localhost/mydb3" --apikey="<Your API Key>" -m "bus" -c

```

**Case2:** Notice that `-1` is used in this case. The request happens only once querying TripUpdates for buses.

```
python gtfsrdb_tfnsw.py -t 'https://api.transport.nsw.gov.au/v1/gtfs/realtime/buses' --database="postgresql://localhost/mydb3" --apikey="<Your API Key>" -m "bus" -c -1
```

## Output
### Database
Data is stored in table(s) in the specified database. Tables created include:

* alerts
* entity_selectors
* stop_time_updates
* trip_updates
* vehicle_positions

### Logging
Logging will be kept and the default location of the log file can be found in `logs/GTFSR.log`
The location to store log fle can be changed in `logging.conf` under [handler_fileHandler], by modifying the args value.




## Known limitations (BUGS!)
For some reasons `-a <your API Key>` is currently not working due to it adding an extra space before the actual key, thus causing a failure in authentication. Please use `--apikey="<Your API Key>"` to parse your authentication key to the script.

