import subprocess
import csv
import time
import json
import http.client

CSV_FILE = "tranco-20241115.csv"  
OUTPUT_DIR = "latency_results"  
NUM_WEBSITES = 2500  
PING_TIMEOUT = 6
PACKETS_PER_SECOND = 5
MEASURE_SEPARATOR = "|--|"
LINE_SEPARATOR = "\n------------------\n"

class dataCollector:
    def __init__(self, csv_dir, out_dir="data.txt"):
        self.csv_dir = csv_dir
        self.out_dir = out_dir

    def runSubproc(self, command):
        return subprocess.run(
            command,
            capture_output=True,
            text=True
        ).stdout

    def ping(self, host, pings=1):
        # Intentionally avoid error handling here - we will do this when appending data to the csv
        result = self.runSubproc(['ping', '-c', str(pings), '-W', str(PING_TIMEOUT), host])
        strsInResult = result.split('\n')
        
        if len(strsInResult) >= 2:
            strsIpLine = strsInResult[0]
            ipBeginning = strsIpLine.find("(") + 1
            ipEnd = strsIpLine[ipBeginning:].find(")") + ipBeginning
            pingIp = strsIpLine[ipBeginning : ipEnd]
            
            pingTimingOut = strsInResult[-3]
            return (pingIp, pingTimingOut)
            # return pingTimingOut
        else:
            return ("failure", "failure")

    def traceroute(self, host):
        # Intentionally avoid error handling here - we will do this when appending data to the csv
        result = self.runSubproc(['traceroute', host])
        # numberHops = result.count("\n") - 1
        
        # resultList = result.split("\n")
        # rttList = []
        # for idx, resStr in enumerate(resultList):
        #     if idx == 0 or idx == len(resultList) - 1: continue
        #     lastMs = resStr.rfind(" ms")
        #     upToLastMs = resStr[:lastMs - 1]
        #     lastSpace = upToLastMs.rfind(" ")
        #     rttList.append(resStr[lastSpace + 1:lastMs])
        
        # return (rttList, numberHops)
        return result
    
    def curl(self, host):
        dump = '/dev/null'
        formattedTimes = '%{size_download}\n'
        result = self.runSubproc(['curl', '-s', '-w', formattedTimes, '-o', dump, host])
        return result
    
    def collectDataInMass(self, numberDataPoints=10):
        collectedPoints = 0
        writeTo = open(self.out_dir, "a")
        with open(self.csv_dir, 'r') as file:
            fileReader = csv.reader(file)
            for idx, row in enumerate(fileReader):
                if collectedPoints >= numberDataPoints:
                    break
                
                popularity, host = row
                #if ".net" in host:
                #    continue
                collectedPoints+=1
                
                
                print(popularity)
                ip, pingRes = self.ping(host)
                
                if (ip == "failure" or pingRes == "failure"):
                    continue
                
                traceRes = self.traceroute(host)
                curlRes = self.curl(host)
                
                country = self.get_country_from_ip(ip)
                
                writeTo.write(
                    popularity + MEASURE_SEPARATOR + 
                    host + MEASURE_SEPARATOR + 
                    country + MEASURE_SEPARATOR + 
                    pingRes + MEASURE_SEPARATOR + 
                    traceRes + MEASURE_SEPARATOR + 
                    curlRes + LINE_SEPARATOR
                    )
                
                time.sleep(1/PACKETS_PER_SECOND)
        writeTo.close()

    def get_country_from_ip(self, ip):
        # Connect to the IP geolocation API
        conn = http.client.HTTPConnection("ip-api.com")
        conn.request("GET", f"/json/{ip}")
        response = conn.getresponse()
        
        # Parse the JSON response
        if response.status == 200:
            data = json.loads(response.read())
            return data.get("country", "Unknown")
        else:
            return "Error: Unable to fetch data"
    
first_time = int(time.time() * 1000)

collector = dataCollector(csv_dir='tranco-20241115.csv')
pointsCollected = NUM_WEBSITES
collector.collectDataInMass(pointsCollected)

second_time = int(time.time() * 1000)
print(second_time - first_time)
predictedHours = (((second_time - first_time)/1000) * (2000/pointsCollected)) / (60 * 60)
print("hours to run = " + str(predictedHours))
