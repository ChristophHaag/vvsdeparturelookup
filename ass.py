#!/usr/bin/python
# -*-coding: utf-8 -*-

# Most code taken from https://github.com/shackspace/vvass/blob/master/ass.py

import http.cookiejar
import json
import urllib.request
import time
import datetime
import xml.etree.ElementTree as ET
import sys
import urllib.request
import urllib.parse


def isStationId(id):
    try:
        i = int(id)
        if len(str(i)) == 7:
            return True
    except:
        return False
    return False


def findstation(s):
    """
    Prints all candidates for the given station name and returns a list sorted after their quality. First is best, last is worst.
    like: [{"name", "quality" (higher is better), "id"}, ...]
    """
    print(s + " is not a station id, searching....")
    # http://www2.vvs.de/vvs/XSLT_STOPFINDER_REQUEST?jsonp=func&suggest_macro=vvs&name_sf=Uhl
    url = "http://www2.vvs.de/vvs/XSLT_STOPFINDER_REQUEST?jsonp=&suggest_macro=vvs&name_sf="
    encodedStationid = urllib.parse.quote_plus(s)
    repl = urllib.request.urlopen(url + encodedStationid).read().decode("UTF-8")
    #repl = repl[5:-2]  # browser sends jsonp=func GET and gets javascript func{<our json>}. if we send jsonp="", then we get only json
    j = json.loads(repl)
    name, best, quality = None, None, 0

    candidates = []
    print("Candidates:")
    for i in j["stopFinder"]["points"]:
        #what is anytype? It seems to be the one that is the right one
        #better be sure and check type too
        if i["anyType"] == "stop" or i["type"] == "stop":
            print(i["name"] + " with id: " + str(i["ref"]["id"]) + " of type: " + i["type"] + "/" + i[
                "anyType"] + " quality: " + str(i["quality"]))
            candidates.append({"name": i["name"], "quality": i["quality"],
                               "type": (i["type"] if not i["type"] == "any" else i["anyType"]), "id": i["ref"]["id"]})
            if int(i["quality"]) > quality:
                name = i["name"]
                best = int(i["ref"]["id"])
                quality = int(i["quality"])
    print("\nBest match for " + s + ":\n" + name + " with id: " + str(best) + " and quality " + str(quality) + "\n")
    stationids = sorted(candidates, key=lambda x: x["quality"])
    return stationids


def stationId(stationId, limit, line=None):
    if not isStationId(stationId):
        stationId = findstation(stationId)[0]["id"]
    if len(str(stationId)) != 7:
        print("error: the station ID needs to be a 7 digit integer")
    efa = get_EFA_from_VVS(stationId, int(limit))

    if efa == "ERROR":
        print("error:  Couldn't connect to the EFA, something is broken.")

    stations = parseEFA(efa)
    if line:
        filteredstations = [s for s in stations["departures"] if s["symbol"] == line]
    else:
        filteredstations = stations["departures"]
    departures = [{"direction": s["direction"], "departure": s["departureTime"], "line": s["symbol"], "delay": s["delay"]} for s in
                  filteredstations]
    for d in departures:
        if d["delay"] and d["delay"] != datetime.timedelta(minutes=0):
            d["delaymins"] = str(int(d["delay"].seconds / 60)) + " minutes"
            d["delayedtime"] = d["departure"] + d["delay"]

    maxlen = 0
    delaylen = 0
    for i in departures:
        if len(i["direction"]) > maxlen:
            maxlen = len(i["direction"])
        if "delaymins" in i and len(i["delaymins"]) > maxlen:
            delaylen = len(i["delaymins"])
    for i in departures:
        s = ("{line:<6}{direction:<" + str(maxlen + 2) + "}{departure:%H:%M}")
        if "delaymins" in i: #TODO: aligning
            s += " +{delaymins:*<" + str(delaylen + 4) + "} -> {delayedtime:%H:%M}"
        print(s.format(**i))


def get_EFA_from_VVS(stationId, lim):
    """send HTTP Request to VVS and return a xml string"""
    # parameters needed for EFA
    zocationServerActive = 1
    lsShowTrainsExplicit = 1
    stateless = 1
    language = 'de'
    SpEncId = 0
    anySigWhenPerfectNoOtherMatches = 1
    #max amount of arrivals to be returned
    limit = lim
    depArr = 'departure'
    type_dm = 'any'
    anyObjFilter_dm = 2
    deleteAssignedStops = 1
    name_dm = stationId
    mode = 'direct'
    dmLineSelectionAll = 1
    itdDateYear = int(time.strftime('%y'))
    itdDateMonth = int(time.strftime('%m'))
    itdDateDay = int(time.strftime('%d'))
    itdTimeHour = int(time.strftime('%H'))
    itdTimeMinute = int(time.strftime('%M'))
    useRealtime = 1
    outputFormat = "JSON"

    url = 'http://www2.vvs.de/vvs/widget/XML_DM_REQUEST?'
    url += 'zocationServerActive=%d' % zocationServerActive
    url += '&lsShowTrainsExplicit=%d' % lsShowTrainsExplicit
    url += '&stateless=%d' % stateless
    url += '&language=%s' % language
    url += '&SpEncId=%d' % SpEncId
    url += '&anySigWhenPerfectNoOtherMatches=%d' \
           % anySigWhenPerfectNoOtherMatches
    url += '&limit=%d' % limit
    url += '&depArr=%s' % depArr
    url += '&type_dm=%s' % type_dm
    url += '&anyObjFilter_dm=%d' % anyObjFilter_dm
    url += '&deleteAssignedStops=%d' % deleteAssignedStops
    url += '&name_dm=%s' % name_dm
    url += '&mode=%s' % mode
    url += '&dmLineSelectionAll=%d' % dmLineSelectionAll
    url += '&itdDateYear=%d' % itdDateYear
    url += '&itdDateMonth=%d' % itdDateMonth
    url += '&itdDateDay=%d' % itdDateDay
    url += '&itdTimeHour=%d' % itdTimeHour
    url += '&itdTimeMinute=%d' % itdTimeMinute
    url += '&useRealtime=%d' % useRealtime
    url += '&outputFormat=%s' % outputFormat

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.
                                         HTTPCookieProcessor(cj))
    opener.addheaders = [('User-agent',
                          'Mozilla/5.0 (X11; Linux x86_64; rv:22.0)'
                          'Gecko/20100101 Firefox/22.0')]
    opener.addheaders = [('Accept-Charset', 'utf-8')]
    efa = opener.open(url)
    data = efa.read()
    #debugging informaton
    code = efa.getcode()
    efa.close()

    if code != 200:
        return "ERROR"

    return (data)


def parseEFA(efa):
    """receive efa data"""
    efaj = json.loads(efa.decode("utf-8"))
    departures = []
    for departure in efaj["departureList"]:
        stopName = departure['stopName']

        dT = departure["dateTime"]
        year = dT['year']
        month = dT['month']
        day = dT['day']
        hour = dT['hour']
        minute = dT['minute']
        departureTime = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute))

        servline = departure['servingLine']
        symbol = servline['symbol']
        direction = servline['direction']
        delayj = servline["delay"] if "delay" in servline else  "0"
        delay = datetime.timedelta(minutes=int(delayj))

        ret = {'stopName': stopName,
               'symbol': symbol,
               'direction': direction,
               'departureTime': departureTime,
                'delay': delay
            }

        departures.append(ret)

    requestTime = time.strftime('%Y%m%d%H%M')
    dataset = {'status': 'success',
               'requestTime': requestTime,
               'departures': departures}
    return dataset

if __name__ == "__main__":
    if len(sys.argv) == 3:
        stationId(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 4:
        stationId(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print(sys.argv[0] + " [stationID|Station Name] limit [filter]")
        print(
            "The request is for all lines that depart at the station. Limiting and filtering will first limit all lines and then filter.")
        print("Example: ./ass.py 5006008 20 S1")
