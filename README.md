# Query GTFS Realtime Timetables from TfNSW

This script is used to download gtfs-formatted real-time timetables from TfNSW. In the initial step, the script verifies if the gtfs data has been updated since last download. If there is an update, it downloads and saves the gtfs fie in a zip format.


## Getting Started
 These instructions will get you a copy of the project up and running on your local machine or a server for developement and testing purposes.
 
### Prerequisites
This script required Python 2.7 

## GTFS-Realtime Timetables

### Input List
Following is a list of input required to be input to the script:

* `-u` OR `--url` : Specify public URI for GTFS realtime Timetables 
* `-k` OR `--apikey`: Specify API Key registered with TfNSW
* `-n` OR `--filename`: Specify part of the filename of the zip file to be downloaded

### Example Use
To use the script, simply run the python script in the command line:

```
python gtfsdb_tfnsw.py -u "https://api.transport.nsw.gov.au/v1/gtfs/schedule/buses" --apikey="Ae1BjiMglwAIhIZA3ahIsxqMw1aZqEfdicT7" -n 'buses'
```

### Output
Instead of GTFS data being downloaded as a zip file containing csv files, last_modified.json is also created if the script is run for the first time. This json file is used to store the date which each GTFS file has been last modified.


## GTFS-Realtime to database
GTFSrDB loads GTFS-realtime data from TfNSW and store it in a database. The script supports 3 types of GTFS-realtime feeds:

* TripUpdates
* VehiclePositions
* Service Alerts

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

**Case1:** Load GTFS-realtime bus positions and store this in a database named mydb3 (note that if you are using postgresql database the database has to be pre-created). The request will run every 30 seconds (default wait time) and new data is append to the table. 

```
python gtfsrdb_tfnsw.py -p 'https://api.transport.nsw.gov.au/v1/gtfs/vehiclepos/buses' --database="postgresql://localhost/mydb3" --apikey="Ae1BjiMglwAIhIZA3ahIsxqMw1aZqEfdicT7" -m "bus" -c

```

**Case2:** Notice that `-1` is used in this case. The request happens only once querying TripUpdates for bus.

```
python gtfsrdb_tfnsw.py -t 'https://api.transport.nsw.gov.au/v1/gtfs/realtime/buses' --database="postgresql://localhost/mydb3" --apikey="Ae1BjiMglwAIhIZA3ahIsxqMw1aZqEfdicT7" -m "bus" -c -1
```

### Output
Data is stored in table(s) in the database specified when running the script.

### Known limitations (BUGS!)
For some reasons `-a <your API Key>` is currently not working due to it adding an extra space before the actual key, thus causing a failure in authentication. Please use `--apikey="<Your API Key>"` to parse the key to the script.

