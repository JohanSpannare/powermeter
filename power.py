#############################
#                           #
#  LDR Energy Monitor       #
#  Author: Matthew Beeston  #
#  16/11/2020               #
#  mdbind.com               #
#                           #
#############################

# Copyright (C) 2020 Matthew Beeston
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License version 3 as published by the Free Software Foundation.
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gpiozero import LightSensor
import RPi.GPIO as GPIO
from datetime import datetime
import mysql.connector
import sqlite3
import schedule
import socket
import RPi.GPIO as GPIO
import time

conn = None
curs = None

upload = True
c = 0
duration = 0
last_time = 0
verbose = 1
version = "0.21"


# MySQL Host
host = "127.0.0.1"

# Check if server is online
def hostAlive(timeout=3, port=3306):
    global upload
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        if upload == False:
        	print (" + Server Online [%s]" % str(datetime.now()), flush=True)
        upload = True
    except socket.error as ex:
        if upload == True:
        	print (" - Server Offline [%s]" % str(datetime.now()), flush=True)
        upload = False
    return upload

# Create SQLite Database
def createLocalDB():
    global conn, curs
    try:
        conn = sqlite3.connect("/home/mat/energy.db")
        curs = conn.cursor()
        curs.execute("DROP TABLE IF EXISTS Log")
        curs.execute("CREATE TABLE Log(Logtime datetime NOT NULL DEFAULT (datetime('now','localtime')), Rate smallint NOT NULL)")
        print (" + Created Local DB [%s]" % str(datetime.now()), flush=True)
    except (sqlite3.Error, sqlite3.Warning) as e:
        print(" - Error %s [%s]" % (e, str(datetime.now())), flush=True)
        return False
    return True

# Saves data to SQLite Database
def storeData():
    global c
    if type(conn) != sqlite3.Connection:
        createLocalDB()
    try:
        curs.execute("INSERT INTO Log (Rate) VALUES (%s)" % str(c))
        conn.commit()
        if verbose > 0:
            print(" + %s pulses saved." % str(c), flush=True)
        c = 0
    except (sqlite3.Error, sqlite3.Warning) as e:
        print(" - Error %s [%s]" % (e, str(datetime.now())), flush=True)

# Fetch local database records
def backlog():
    if type(conn) == sqlite3.Connection:
        try:
            result = curs.execute("SELECT * FROM Log")
            if result.fetchone() == None:
                return False
            else:
                return True
        except (sqlite3.Error, sqlite3.Warning) as e:
            print(" - Error %s [%s]" % (e, str(datetime.now())), flush=True)
            return False
    else:
        return False

# Upload data to server
def uploadData(backlogData=False):
    global c, upload, duration
    try:
        mydb = mysql.connector.connect(
            host=host,
            user="energy",
            password="SECRET",
            database="Energy")
        mycursor = mydb.cursor()
        if backlogData == False:
            sql = "INSERT INTO Log (Rate, Duration) VALUES (%s,%s)" % (str(c), duration)
        else:
            sql = "INSERT INTO Log (Logtime, Rate, Duration) VALUES %s"
            try:
                result = curs.execute("SELECT * FROM Log")
                data = []
                rows = 1
                for row in result:
                    data.append('("%s",%s)' % (row[0], row[1]))
                    rows = rows + 1
                val = ','.join(data)
                val = val + ',(CURRENT_TIMESTAMP, %s, %s)' % (str(c),duration)
                sql = sql % val
            except (sqlite3.Error, sqlite3.Warning) as e:
                print(" - Error %s [%s]" % (e, str(datetime.now())), flush=True)
                return False
        mycursor.execute(sql)
        mydb.commit()

        if backlogData == False:
            if verbose > 0:
                print(" + %s pulses uploaded." % str(c), flush=True)
        else:
            try:
                curs.execute("DELETE FROM Log")
                conn.commit()
                if verbose > 0:
                    print(" + %s records uploaded." % str(rows), flush=True)
            except (sqlite3.Error, sqlite3.Warning) as e:
                print(" - Error %s [%s]" % (e, str(datetime.now())), flush=True)
        c = 0
        duration = 0
    except mysql.connector.Error as e:
        print(" - Error %s [%s]" % (e, str(datetime.now())), flush=True)
        print (" - Server Offline [%s]" % str(datetime.now()), flush=True)
        upload = False
        storeData()

# Send data to active connection
def sendData():

    # If host online send to host
    if upload == True:
        # If local records present, upload them first
        if backlog() == True:
            uploadData(True)	
        # Upload data
        else:
            uploadData()
    # If host offline, save records locally
    else:
        storeData()


def my_callback(channel):
    if GPIO.input(channel) == GPIO.HIGH:
        global c, duration, last_time
        c = c+1
        t = time.perf_counter() - last_time
        duration = duration+t
        last_time =  time.perf_counter()
        print ("Elapsed " + str(t) + "Duration " + str(duration) + "C " + str(c))

# Send data every 1 minute
schedule.every(5).seconds.do(sendData)
# Check if host alive every 5 minutes
schedule.every(5).minutes.do(hostAlive)

print(" LDR Energy Monitor v%s" % version, flush=True)
print(" + Started [%s]" % str(datetime.now()), flush=True)

schedule.run_pending() 
GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.add_event_detect(27, GPIO.BOTH, callback=my_callback)
last_time = time.perf_counter() #Set first elapsed time

# Run scheduler
while 1:
   schedule.run_pending()
   time.sleep(1)
