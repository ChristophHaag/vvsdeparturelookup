#!/usr/bin/python
# -*-coding: utf-8 -*-

#Most code taken from https://github.com/shackspace/vvass/blob/master/ass.py

import http.cookiejar
import json
import urllib.request
import time
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

def stationId(stationId, limit, line=None):
    if not isStationId(stationId):
        print(stationId + " is not a station id, searching....")
        #http://www2.vvs.de/vvs/XSLT_STOPFINDER_REQUEST?jsonp=func&suggest_macro=vvs&name_sf=Uhl
        url = "http://www2.vvs.de/vvs/XSLT_STOPFINDER_REQUEST?jsonp=func&suggest_macro=vvs&name_sf="
        encodedStationid = urllib.parse.quote_plus(stationId)
        repl = urllib.request.urlopen(url + encodedStationid).read().decode("UTF-8")
        #func({...})
        #print(repr(repl))
        repl = repl[5:-2] #TODO: not hardcoded
        j = json.loads(repl)
        name, best, quality = None, None, 0

        print("Candidates:")
        for i in j["stopFinder"]["points"]:
            #what is anytype? It seems to be the one that is the right one
            #better be sure and check type too
            if i["anyType"] == "stop" or i["type"] == "stop":
                print(i["name"] + " with id: "  + str(i["ref"]["id"]) + " of type: " + i["type"] + "/" + i["anyType"] + " quality: " + str(i["quality"]))
                if int(i["quality"]) > quality:
                    name = i["name"]
                    best = int(i["ref"]["id"])
                    quality = int(i["quality"])
        print("\nBest match for " + stationId + ":\n" + name + " with id: " + str(best) + " and quality " + str(quality) + "\n")
        stationId = best
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
    departures = [{"direction": s["direction"], "departure": s["departureTime"], "line": s["symbol"]} for s in
                  filteredstations]

    maxlen = 0
    for i in departures:
        if len(i["direction"]) > maxlen:
            maxlen = len(i["direction"])
    for i in departures:
        print(("{0:6}{1:" + str(maxlen + 2) + "}{2}").format(i["line"], i["direction"], i["departure"]))


def get_EFA_from_VVS(stationId, lim):
    """send HTTP Request to VVS and return a xml string"""
    #parameters needed for EFA
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

    url = 'http://www2.vvs.de/vvs/widget/XML_DM_REQUEST?'
    url += 'zocationServerActive=%d' % zocationServerActive
    url += '&lsShowTrainsExplicit%d' % lsShowTrainsExplicit
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
    """receive efa data and return a json object"""
    root = ET.fromstring(efa)
    xmlDepartures = root.findall('./itdDepartureMonitorRequest/'
                                 + 'itdDepartureList/itdDeparture')
    if len(xmlDepartures) == 0:
        print('error: The EFA presented an empty itdDepartureList. Reason therefore might be an unknown station ID.')

    departures = []

    for departure in xmlDepartures:
        stopName = departure.attrib['stopName']
        itdServingLine = departure.find('itdServingLine')
        symbol = itdServingLine.attrib['symbol']
        direction = itdServingLine.attrib['direction']
        itdDate = departure.find('itdDateTime/itdDate')
        year = itdDate.attrib['year']
        month = fixdate(itdDate.attrib['month'])
        day = fixdate(itdDate.attrib['day'])
        itdTime = departure.find('itdDateTime/itdTime')
        hour = fixdate(itdTime.attrib['hour'])
        minute = fixdate(itdTime.attrib['minute'])
        #yyyymmddHHMM
        departureTime = hour + ":" + minute + " (" + day + "." + month + "." + year + ")"
        route = departure.find('itdServingLine/itdRouteDescText').text

        ret = {'stopName': stopName,
               'symbol': symbol,
               'direction': direction,
               'departureTime': departureTime,
               'route': route}

        departures.append(ret)

    requestTime = time.strftime('%Y%m%d%H%M')
    dataset = {'status': 'success',
               'requestTime': requestTime,
               'departures': departures}
    return dataset


def fixdate(date):
    """ fixes single digit date characters with a leading 0
"""
    if len(date) != 2:
        date = '0' + date
    return date


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
