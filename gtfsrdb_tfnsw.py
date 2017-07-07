#!/usr/bin/python

# gtfsrdb_tfnsw.py: load TfNSW gtfs-realtime data to a database

# Copyright 2017, Tara Sutjarittham

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Authors:
# Tara Sutjarittham
# Forked from mattwigway/gtfsrdb

#from google.transit import gtfs_realtime_pb2
import tfnsw_gtfs_realtime_pb2
from optparse import OptionParser
import time
import sys
import datetime
import pytz
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib2 import urlopen,Request
from model import *
import logging, logging.handlers
import logging.config


p = OptionParser()
p.add_option('-t', '--trip-updates', dest='tripUpdates', default=None,
             help='The trip updates URL', metavar='URL')

p.add_option('-a', '--alerts', default=None, dest='alerts',
             help='The alerts URL', metavar='URL')

p.add_option('-p', '--vehicle-positions', dest='vehiclePositions', default=None,
             help='The vehicle positions URL', metavar='URL')

p.add_option('-d', '--database', default=None, dest='dsn',
             help='Database connection string', metavar='DSN')

p.add_option('-o', '--discard-old', default=False, dest='deleteOld',
             action='store_true',
             help='Dicard old updates, so the database is always current')

p.add_option('-c', '--create-tables', default=False, dest='create',
             action='store_true', help="Create tables if they aren't found")

p.add_option('-w', '--wait', default=30, type='int', metavar='SECS',
             dest='timeout', help='Time to wait between requests (in seconds)')

p.add_option('-v', '--verbose', default=False, dest='verbose',
             action='store_true', help='Print generated SQL')

p.add_option('-l', '--language', default='en', dest='lang', metavar='LANG',
             help='When multiple translations are available, prefer this language')

p.add_option('-1', '--once', default=False, dest='once', action='store_true',
             help='only run the loader one time')

p.add_option('-k', '--apikey', default=None, dest='apiKey',
             help='API Key', metavar='KEY')

p.add_option('-m', '--mode', default=None, dest='mode',
             help='mode of transportation E.g. Bus, Train', metavar='MODE')

opts,args = p.parse_args()
#opts= p.parse_args()

#Keep log
#logging.config.fileConfig('logging.conf', defaults={'logfilename': 'GTFSR.log'})
logging.config.fileConfig('logging.conf')
logger = logging.getLogger('GTFSR')

if opts.dsn == None:
    print 'No database specified!'
    exit(1)

if opts.alerts == None and opts.tripUpdates == None and opts.vehiclePositions == None:
    print 'No trip updates, alerts, or vehicle positions URLs were specified!'
    exit(1)

if opts.alerts == None:
    print 'Warning: no alert URL specified, proceeding without alerts'

if opts.tripUpdates == None:
    print 'Warning: no trip update URL specified, proceeding without trip updates'

if opts.vehiclePositions == None:
    print 'Warning: no vehicle positions URL specified, proceeding without vehicle positions'

if opts.apiKey == None:
    print 'Warning: no API Key specified, proceeding without API Key'

if opts.mode == None:
    #print 'Warning: no mode of transport specified, proceeding without mode of transport'
    logger.warning('no mode of transport specified, proceeding without mode of transport')
    opts.mode = 'NA'


# Connect to the database
engine = create_engine(opts.dsn, echo=opts.verbose)

# sessionmaker returns a class
session = sessionmaker(bind=engine)()

# Check if it has the tables
# Base from model.py
for table in Base.metadata.tables.keys():
    try:
        if not engine.has_table(table):
            if opts.create:
                #print 'Creating table %s' % table
                logger.info('Creating table %s', table)
                Base.metadata.tables[table].create(engine)
            else:
                #print 'Missing table %s! Use -c to create it.' % table
                logger.error('Missing table %s! Use -c to create it.', table)
                exit(1)
    except Exception, err:
        logger.error('Database Error: %s', str(err))
        exit(1)


# Get a specific translation from a TranslatedString
def getTrans(string, lang):
    # If we don't find the requested language, return this
    untranslated = None

    # single translation, return it
    if len(string.translation) == 1:
        return string.translation[0].text

    for t in string.translation:
        if t.language == lang:
            return t.text
        if t.language == None:
            untranslated = t.text
    return untranslated

#Authentication information
#api_key = 'apikey Ae1BjiMglwAIhIZA3ahIsxqMw1aZqEfdicT7'

try:
    keep_running = True
    while keep_running:
        try:
            # if True:
            if opts.apiKey:
                #Add API key to the correct format to be included in the header
                api_key='apikey' + ' ' + opts.apiKey

            if opts.deleteOld:
                # Go through all of the tables that we create, clear them
                # Don't mess with other tables (i.e., tables from static GTFS)
                for theClass in AllClasses:
                    for obj in session.query(theClass):
                        session.delete(obj)

            if opts.tripUpdates:
                GTFSR_type = 'tripUpdates'
                q = Request(opts.tripUpdates)
                q.add_header('Authorization', api_key)
                fm = tfnsw_gtfs_realtime_pb2.FeedMessage()
                fm.ParseFromString(
                    urlopen(q).read()
                )

                # Convert this a Python object, and save it to be placed into each
                # trip_update
                timestamp = datetime.datetime.fromtimestamp(fm.header.timestamp, tz=pytz.timezone('Australia/Sydney'))

                # Check the feed version
                if fm.header.gtfs_realtime_version != u'1.0':
                    #print 'Warning: feed version has changed: found %s, expected 1.0' % fm.header.gtfs_realtime_version
                    logger.warning('%s - %s - feed version has changed: found %s, expected 1.0', GTFSR_type, opts.mode, fm.header.gtfs_realtime_version)

                #print 'Adding %s trip updates' % len(fm.entity)
                logger.info('%s - %s - Adding %s trip updates', GTFSR_type, opts.mode, len(fm.entity))
                for entity in fm.entity:

                    tu = entity.trip_update

                    dbtu = TripUpdate(
                        trip_id=tu.trip.trip_id,
                        route_id=tu.trip.route_id,
                        trip_start_time=tu.trip.start_time,
                        trip_start_date=tu.trip.start_date,

                        # get the schedule relationship
                        # This is somewhat undocumented, but by referencing the 
                        # DESCRIPTOR.enum_types_by_name, you get a dict of enum types
                        # as described at http://code.google.com/apis/protocolbuffers/docs/reference/python/google.protobuf.descriptor.EnumDescriptor-class.html
                        schedule_relationship=
                        tu.trip.DESCRIPTOR.enum_types_by_name['ScheduleRelationship'].values_by_number[
                            tu.trip.schedule_relationship].name,

                        vehicle_id=tu.vehicle.id,
                        vehicle_label=tu.vehicle.label,
                        vehicle_license_plate=tu.vehicle.license_plate,
                        timestamp=timestamp,
                        transport_mode=opts.mode)

                    for stu in tu.stop_time_update:
                        dbstu = StopTimeUpdate(
                            stop_sequence=stu.stop_sequence,
                            stop_id=stu.stop_id,
                            arrival_delay=stu.arrival.delay,
                            #arrival_time=stu.arrival.time,
                            arrival_time=datetime.datetime.fromtimestamp(stu.arrival.time, tz=pytz.timezone('Australia/Sydney')),
                            arrival_uncertainty=stu.arrival.uncertainty,
                            departure_delay=stu.departure.delay,
                            #departure_time=stu.departure.time,
                            departure_time=datetime.datetime.fromtimestamp(stu.departure.time, tz=pytz.timezone('Australia/Sydney')),
                            departure_uncertainty=stu.departure.uncertainty,
                            schedule_relationship=
                            tu.trip.DESCRIPTOR.enum_types_by_name['ScheduleRelationship'].values_by_number[
                                tu.trip.schedule_relationship].name
                        )
                        session.add(dbstu)
                        dbtu.StopTimeUpdates.append(dbstu)

                    session.add(dbtu)

            if opts.alerts:
                GTFSR_type = 'alerts'
                q = Request(opts.alerts)
                q.add_header('Authorization', api_key)
                fm = tfnsw_gtfs_realtime_pb2.FeedMessage()
                fm.ParseFromString(
                    urlopen(q).read()
                )

                # Convert this a Python object, and save it to be placed into each
                # trip_update
                timestamp = datetime.datetime.fromtimestamp(fm.header.timestamp, tz=pytz.timezone('Australia/Sydney'))

                # Check the feed version
                if fm.header.gtfs_realtime_version != u'1.0':
                    #print 'Warning: feed version has changed: found %s, expected 1.0' % fm.header.gtfs_realtime_version
                    logger.warning('%s - %s - feed version has changed: found %s, expected 1.0', GTFSR_type, opts.mode, fm.header.gtfs_realtime_version)

                    #print 'Adding %s alerts' % len(fm.entity)
                    logger.info('%s - %s - Adding %s alerts', GTFSR_type, opts.mode, len(fm.entity))

                    for entity in fm.entity:
                        alert = entity.alert
                        dbalert = Alert(
                            start=alert.active_period[0].start,
                            end=alert.active_period[0].end,
                            cause=alert.DESCRIPTOR.enum_types_by_name['Cause'].values_by_number[alert.cause].name,
                            effect=alert.DESCRIPTOR.enum_types_by_name['Effect'].values_by_number[alert.effect].name,
                            url=getTrans(alert.url, opts.lang),
                            header_text=getTrans(alert.header_text, opts.lang),
                            description_text=getTrans(alert.description_text,
                                                      opts.lang)
                        )

                        session.add(dbalert)
                        for ie in alert.informed_entity:
                            dbie = EntitySelector(
                                agency_id=ie.agency_id,
                                route_id=ie.route_id,
                                route_type=ie.route_type,
                                stop_id=ie.stop_id,

                                trip_id=ie.trip.trip_id,
                                trip_route_id=ie.trip.route_id,
                                trip_start_time=ie.trip.start_time,
                                trip_start_date=ie.trip.start_date)
                            session.add(dbie)
                            dbalert.InformedEntities.append(dbie)

            if opts.vehiclePositions:
                GTFSR_type = 'vehiclePositions'
                q = Request(opts.vehiclePositions)
                q.add_header('Authorization', api_key)
                fm = tfnsw_gtfs_realtime_pb2.FeedMessage()
                fm.ParseFromString(
                    urlopen(q).read()
                )

                # Convert this a Python object, and save it to be placed into each
                # vehicle_position
                timestamp = datetime.datetime.fromtimestamp(fm.header.timestamp,tz=pytz.timezone('Australia/Sydney'))

                # Check the feed version
                if fm.header.gtfs_realtime_version != u'1.0':
                    #print 'Warning: feed version has changed: found %s, expected 1.0' % fm.header.gtfs_realtime_version
                    logger.warning('%s - %s - feed version has changed: found %s, expected 1.0', GTFSR_type, opts.mode,
                                   fm.header.gtfs_realtime_version)

                #print 'Adding %s vehicle_positions' % len(fm.entity)
                logger.info('%s - %s - Adding %s vehicle_positions', GTFSR_type, opts.mode, len(fm.entity))
                for entity in fm.entity:
                    vp = entity.vehicle

                    dbvp = VehiclePosition(
                        trip_id=vp.trip.trip_id,
                        route_id=vp.trip.route_id,
                        trip_start_time=vp.trip.start_time,
                        trip_start_date=vp.trip.start_date,
                        schedule_relationship=vp.trip.schedule_relationship,
                        vehicle_id=vp.vehicle.id,
                        vehicle_label=vp.vehicle.label,
                        vehicle_license_plate=vp.vehicle.license_plate,
                        position_latitude=vp.position.latitude,
                        position_longitude=vp.position.longitude,
                        position_bearing=vp.position.bearing,
                        position_speed=vp.position.speed,
                        position_timestamp=datetime.datetime.fromtimestamp(vp.timestamp,tz=pytz.timezone('Australia/Sydney')),
                        congestion_level=vp.congestion_level,
                        occupancy_status=vp.occupancy_status,
                        air_conditioned=vp.vehicle.Extensions[tfnsw_gtfs_realtime_pb2.tfnsw_vehicle_descriptor].air_conditioned,
                        wheelchair_accessible=vp.vehicle.Extensions[tfnsw_gtfs_realtime_pb2.tfnsw_vehicle_descriptor].wheelchair_accessible,
                        vehicle_model=vp.vehicle.Extensions[tfnsw_gtfs_realtime_pb2.tfnsw_vehicle_descriptor].vehicle_model,
                        special_vehicle_attributes=vp.vehicle.Extensions[tfnsw_gtfs_realtime_pb2.tfnsw_vehicle_descriptor].special_vehicle_attributes,
                        timestamp=timestamp,
                        transport_mode=opts.mode
                    )

                    session.add(dbvp)

            # This does deletes and adds, since it's atomic it never leaves us
            # without data
            session.commit()
        except:
            # else:
            #print 'Exception occurred in iteration'
            #print sys.exc_info()
            logger.error('%s - %s - Exception occurred in iteration: %s', GTFSR_type, opts.mode, sys.exc_info())

        # put this outside the try...except so it won't be skipped when something
        # fails
        # also, makes it easier to end the process with ctrl-c, b/c a 
        # KeyboardInterrupt here will end the program (cleanly)
        if opts.once:
            print "Executed the load ONCE ... going to stop now..."
            keep_running = False
        else:
            time.sleep(opts.timeout)

finally:
    print "Closing session . . ."
    session.close()