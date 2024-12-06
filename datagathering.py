"""
Name: Sanket Makkar
    CaseID:         sxm1626
    File Name:      datagathering.py
    Date Created:   11/29/2024
    Description:    This is the data gathering file for projet 5 containing methods to parse through and 
                    measure each host listed in the first 2500 websites in the tranco-20241115.csv file.
"""
import subprocess
import csv
import time
import json
import http.client

CSV_FILE = "tranco-20241115.csv"  
NUM_WEBSITES = 2500  
PING_TIMEOUT = 6
PACKETS_PER_SECOND = 5
MEASURE_SEPARATOR = "|--|"
LINE_SEPARATOR = "\n------------------\n"
PING_WORKING_LENGTH = 2
OFF_BY_ONE_OFFSET = 1
FAILURE_MESSAGE = "failure"
RESPONSE_STATUS_OK = 200
SECOND_TO_MS = 1000
SECOND_TO_MINUTE = 60
MINUTE_TO_HOUR = 60
DEFAULT_DATA_POINTS_COLLECTED = 10
COUNTER_INITIAL_VALUE = 0
PING_SUMMARY_POSITION = -3

class dataCollector:
    # just define a data collection class that, by default, asks for a csv file to work with
    def __init__(self, csv_dir, out_dir="data.txt"):
        self.csv_dir = csv_dir
        self.out_dir = out_dir

    # generic helper to run a command
    def runSubproc(self, command):
        return subprocess.run(
            command,
            capture_output=True,
            text=True
        ).stdout

    # ping command - will be used frequently, and we only send one ping at a time (hence the default parameter)
    def ping(self, host, pings=1):
        # Intentionally avoid error handling here - we will do this when appending data to the csv
        result = self.runSubproc(['ping', '-c', str(pings), '-W', str(PING_TIMEOUT), host])
        strsInResult = result.split('\n')
        
        if len(strsInResult) >= PING_WORKING_LENGTH:
            strsIpLine = strsInResult[COUNTER_INITIAL_VALUE]
            ipBeginning = strsIpLine.find("(") + OFF_BY_ONE_OFFSET
            ipEnd = strsIpLine[ipBeginning:].find(")") + ipBeginning
            pingIp = strsIpLine[ipBeginning : ipEnd]
            
            pingTimingOut = strsInResult[PING_SUMMARY_POSITION]
            return (pingIp, pingTimingOut)
        else:
            return (FAILURE_MESSAGE, FAILURE_MESSAGE)

    # trace network route command - will also be used frequently
    def traceroute(self, host):
        # just pass raw traceroute output to csv
        result = self.runSubproc(['traceroute', host])
        return result
    
    # curl command to grab downloaded bytes info - used for one finding, and we really only need that variable
    def curl(self, host):
        dump = '/dev/null'
        formattedSize = '%{size_download}\n'
        result = self.runSubproc(['curl', '-s', '-w', formattedSize, '-o', dump, host])
        return result
    
    # the main function to call from this class, orchestrates scale data collection
    def collectDataInMass(self, numberDataPoints=DEFAULT_DATA_POINTS_COLLECTED):
        # we want to stop when we have collected "numberDataPoints" amount of data points for each measurement
        collectedPoints = COUNTER_INITIAL_VALUE
        
        # open up the output file
        writeTo = open(self.out_dir, "a")
        # and open up our csv
        with open(self.csv_dir, 'r') as file:
            # now we can just go through the file using file reader
            fileReader = csv.reader(file)
            for idx, row in enumerate(fileReader):
                # if we reached the relevant data points count then just stop right here
                if collectedPoints >= numberDataPoints:
                    break
                
                # grab popularity as well as host name - these are helpful when manually inspecting data
                popularity, host = row
                
                # inform ourselves of how many points we have collected towards our goal
                collectedPoints+=OFF_BY_ONE_OFFSET
                
                # we of course want to know where we are in the website list to gauge how close we are to being done
                print(popularity)
                
                # then ping
                ip, pingRes = self.ping(host)
                
                # if there was ping failure stop right here - we don't want to write to output if the ping itself didn't work (ping is the most critical measurement for us)
                if (ip == FAILURE_MESSAGE or pingRes == FAILURE_MESSAGE):
                    continue
                
                # now grab the route
                traceRes = self.traceroute(host)
                # and get the info we need from curl
                curlRes = self.curl(host)
                # and identify the country as a string
                country = self.getCountry(ip)
                
                # write to output
                writeTo.write(
                    popularity + MEASURE_SEPARATOR + 
                    host + MEASURE_SEPARATOR + 
                    country + MEASURE_SEPARATOR + 
                    pingRes + MEASURE_SEPARATOR + 
                    traceRes + MEASURE_SEPARATOR + 
                    curlRes + LINE_SEPARATOR
                    )
                
                # delay such that we only measure at most PACKETS_PER_SECOND times (i.e. 5 times per second)
                time.sleep(OFF_BY_ONE_OFFSET/PACKETS_PER_SECOND)
                
        # close out our file
        writeTo.close()

    # helper to grab country of origin information for a host (ex: 'United States' would be for www.google.com)
    def getCountry(self, ip):
        # We use a geolocation website that returns json formatted information - including country location
        conn = http.client.HTTPConnection("ip-api.com")
        conn.request("GET", f"/json/{ip}")
        response = conn.getresponse()
        
        # Just grab the relevant info if we can get it
        if response.status == RESPONSE_STATUS_OK:
            dataReturned = json.loads(response.read())
            return dataReturned.get("country", "Unknown")
        else:
            return "Error: N/A"
    
# We try to time the whole interaction - this was more for me when trying to predict how long this would need to run
first_time = int(time.time() * SECOND_TO_MS)

# init a data collector, tell it to collect data
collector = dataCollector(csv_dir='tranco-20241115.csv')
pointsCollected = NUM_WEBSITES
collector.collectDataInMass(pointsCollected)

# end the timer, and compute the expected number of hours our data collection would take - for the full scale data collection we find this to be the time it took to collect all that data
second_time = int(time.time() * SECOND_TO_MS)
print(second_time - first_time)
predictedHours = (((second_time - first_time)/SECOND_TO_MS) * (NUM_WEBSITES/pointsCollected)) / (SECOND_TO_MINUTE * MINUTE_TO_HOUR)
print("hours to run = " + str(predictedHours))
