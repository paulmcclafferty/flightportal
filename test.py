import time
from random import randrange
import json

try:
    from secrets import secrets
except ImportError:
    print("Secrets including geo are kept in secrets.py, please add them there!")
    raise

# How often to query fr24 - quick enough to catch a plane flying over, not so often as to cause any issues, hopefully
QUERY_DELAY=30
#Area to search for flights, see secrets file
BOUNDS_BOX=secrets["bounds_box"]

#URLs
FLIGHT_SEARCH_HEAD="https://data-cloud.flightradar24.com/zones/fcgi/feed.js?bounds="
FLIGHT_SEARCH_TAIL="&faa=1&satellite=1&mlat=1&flarm=1&adsb=1&gnd=0&air=1&vehicles=0&estimated=0&maxage=14400&gliders=0&stats=0&ems=1&limit=1"
FLIGHT_SEARCH_URL=FLIGHT_SEARCH_HEAD+BOUNDS_BOX+FLIGHT_SEARCH_TAIL
# Deprecated URL used to return less JSON than the long details URL, but can give ambiguous results
# FLIGHT_DETAILS_HEAD="https://api.flightradar24.com/common/v1/flight/list.json?&fetchBy=flight&page=1&limit=1&maxage=14400&query="

# Used to get more flight details with a fr24 flight ID from the initial search
FLIGHT_LONG_DETAILS_HEAD="https://data-live.flightradar24.com/clickhandler/?flight="



# Take the flight ID we found with a search, and load details about it
def get_flight_details(fn):

    # the JSON from FR24 is too big for the matrixportal memory to handle. So we load it in chunks into our static array,
    # as far as the big "trails" section of waypoints at the end of it, then ignore most of that part. Should be about 9KB, we have 14K before we run out of room..
    global json_bytes
    global json_size
    byte_counter=0
    chunk_length=1024
    success=False

    # zero out any old data in the byte array
    for i in range(0,json_size):
        json_bytes[i]=0

    # Get the URL response one chunk at a time
    try:
        response=requests.get(url=FLIGHT_LONG_DETAILS_HEAD+fn,headers=rheaders)
        for chunk in response.iter_content(chunk_size=chunk_length):

            # if the chunk will fit in the byte array, add it
            if(byte_counter+chunk_length<=json_size):
                for i in range(0,len(chunk)):
                    json_bytes[i+byte_counter]=chunk[i]
            else:
                print("Exceeded max string size while parsing JSON")
                return False

            # check if this chunk contains the "trail:" tag which is the last bit we care about
            trail_start=json_bytes.find((b"\"trail\":"))
            byte_counter+=len(chunk)

            # if it does, find the first/most recent of the many trail entries, giving us things like speed and heading
            if not trail_start==-1:
                # work out the location of the first } character after the "trail:" tag, giving us the first entry
                trail_end=json_bytes[trail_start:].find((b"}"))
                if not trail_end==-1:
                    trail_end+=trail_start
                    # characters to add to make the whole JSON object valid, since we're cutting off the end
                    closing_bytes=b'}]}'
                    for i in range (0,len(closing_bytes)):
                        json_bytes[trail_end+i]=closing_bytes[i]
                    # zero out the rest
                    for i in range(trail_end+3,json_size):
                        json_bytes[i]=0
                    # print(json_bytes.decode('utf-8'))

                    # Stop reading chunks
                    print("Details lookup saved "+str(trail_end)+" bytes.")
                    return True
    # Handle occasional URL fetching errors            
    except (RuntimeError, OSError, HttpError) as e:
            print("Error--------------------------------------------------")
            print(e)
            return False

    #If we got here we got through all the JSON without finding the right trail entries
    print("Failed to find a valid trail entry in JSON")
    return False
    

# Look at the byte array that fetch_details saved into and extract any fields we want
def parse_details_json():

    global json_bytes

    try:
        # get the JSON from the bytes
        long_json=json.loads(json_bytes)

        # Some available values from the JSON. Put the details URL and a flight ID in your browser and have a look for more.

        flight_number=long_json["identification"]["number"]["default"]
        #print(flight_number)
        flight_callsign=long_json["identification"]["callsign"]
        aircraft_code=long_json["aircraft"]["model"]["code"]
        aircraft_model=long_json["aircraft"]["model"]["text"]
        #aircraft_registration=long_json["aircraft"]["registration"]
        airline_name=long_json["airline"]["name"]
        #airline_short=long_json["airline"]["short"]
        airport_origin_name=long_json["airport"]["origin"]["name"]
        airport_origin_name=airport_origin_name.replace(" Airport","")
        airport_origin_code=long_json["airport"]["origin"]["code"]["iata"]
        #airport_origin_country=long_json["airport"]["origin"]["position"]["country"]["name"]
        #airport_origin_country_code=long_json["airport"]["origin"]["position"]["country"]["code"]
        #airport_origin_city=long_json["airport"]["origin"]["position"]["region"]["city"]
        #airport_origin_terminal=long_json["airport"]["origin"]["info"]["terminal"]
        airport_destination_name=long_json["airport"]["destination"]["name"]
        airport_destination_name=airport_destination_name.replace(" Airport","")
        airport_destination_code=long_json["airport"]["destination"]["code"]["iata"]
        #airport_destination_country=long_json["airport"]["destination"]["position"]["country"]["name"]
        #airport_destination_country_code=long_json["airport"]["destination"]["position"]["country"]["code"]
        #airport_destination_city=long_json["airport"]["destination"]["position"]["region"]["city"]
        #airport_destination_terminal=long_json["airport"]["destination"]["info"]["terminal"]
        #time_scheduled_departure=long_json["time"]["scheduled"]["departure"]
        #time_real_departure=long_json["time"]["real"]["departure"]
        #time_scheduled_arrival=long_json["time"]["scheduled"]["arrival"]
        #time_estimated_arrival=long_json["time"]["estimated"]["arrival"]
        #latitude=long_json["trail"][0]["lat"]
        #longitude=long_json["trail"][0]["lng"]
        #altitude=long_json["trail"][0]["alt"]
        #speed=long_json["trail"][0]["spd"]
        #heading=long_json["trail"][0]["hd"]


        if flight_number:
            print("Flight is called "+flight_number)
        elif flight_callsign:
            print("No flight number, callsign is "+flight_callsign)
        else:
            print("No number or callsign for this flight.")


        # Set up to 6 of the values above as text for display_flights to put on the screen
        # Short strings get placed on screen, then longer ones scroll over each in sequence

        global label1_short
        global label1_long
        global label2_short
        global label2_long
        global label3_short
        global label3_long

        label1_short=flight_number
        label1_long=airline_name
        label2_short=airport_origin_code+"-"+airport_destination_code
        label2_long=airport_origin_name+"-"+airport_destination_name
        label3_short=aircraft_code
        label3_long=aircraft_model

        if not label1_short:
            label1_short=''
        if not label1_long:
            label1_long=''
        if not label2_short:
            label2_short=''
        if not label2_long:
            label2_long=''
        if not label3_short:
            label3_short=''
        if not label3_long:
            label3_long=''


        # optional filter example - check things and return false if you want

        # if altitude > 10000:
        #    print("Altitude Filter matched so don't display anything")
        #    return False

    except (KeyError, ValueError,TypeError) as e:
        print("JSON error")
        print (e)
        return False


    return True

