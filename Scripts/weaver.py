import json                 
import requests             
from time import sleep              
import copy                 
import random
import string
from typing import List
from urllib3.exceptions import InsecureRequestWarning  # Required import to prevent error outputs when using insecure connections...
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning) # This disables that error
import inspect
import functools
import warnings

version = "0.22.5" # Weaver.Py version
validateConfigurations = True # Whether to perform basic config validation
quitOnError = True # Whether to quit when an error is raised within weaverError by checkForError
increasedErrorMessaging = True # Whether to log more errors when an error is flagged

# weaverError class - for raising exceptions
class weaverError:
    def checkForError(resp: requests.Response, extras=[]) -> bool: # Check for and raise an error based on HTTP response status code.
        try:
            if "20" in str(resp.status_code):
                return False
            if increasedErrorMessaging:
                extras.append(resp.text)
                extras.append(str(resp.status_code))
            if "409" in str(resp.status_code):
                raise weaverError.ResourceAlreadyExists(extras=extras)
            elif "404" in str(resp.status_code):
                raise weaverError.ResourceNotFound(extras=extras)
            elif "401" in str(resp.status_code):
                raise weaverError.InvalidToken(extras=extras)
            else:
                raise weaverError.UnknownError(extras=extras)
        except Exception as e:
            if (e.message):
                print(e.message)
            else:
                print(e)
            if quitOnError:
                exit()
            return True

    class ResourceNotFound(Exception): # Tried to get, edit or delete something that doesn't exist.
        def __init__(self, message: str = "Requested resource was not found.", extras = None):
            try:
                self.message = message
                if extras:
                    self.message = message + " ~> ["
                    for extra in extras:
                        if extra:
                            self.message += "'" + extra + "', "
                    self.message = self.message[:-2] + "]"
                super().__init__(self.message)
            except Exception as e:
                raise weaverError.InternalError(e.message)

    class ResourceAlreadyExists(Exception): # Tried to create something that already exists (clashing IDs?)
        def __init__(self, message = "Conflicting resource already exists.", extras = None):
            try:
                self.message = message
                if extras:
                    self.message = message + " ~> ["
                    for extra in extras:
                        if extra:
                            self.message += "'" + extra + "', "
                    self.message = self.message[:-2] + "]"
                super().__init__(self.message)
            except Exception as e:
                raise weaverError.InternalError(e.message)

    class InvalidToken(Exception): # API Token was invalid
        def __init__(self, message:str = "Request Denied", extras = None):
            try:
                self.message = message
                if extras:
                    self.message = message + " ~> ["
                    for extra in extras:
                        if extra:
                            self.message += "'" + extra + "', "
                    self.message = self.message[:-2] + "]"
                super().__init__(self.message)
            except Exception as e:
                raise weaverError.InternalError(e.message)

    class UnknownError(Exception): # An unknown / unidentifiable error
        def __init__(self, message:str = "An error occurred", extras = None):
            try:
                self.message = message
                if extras:
                    self.message = message + " ~> ["
                    for extra in extras:
                        if extra:
                            self.message += "'" + extra + "', "
                    self.message = self.message[:-2] + "]"
                super().__init__(self.message)
            except Exception as e:
                raise weaverError.InternalError(e.message)

    class InternalError(Exception): # An error pertaining to Weaver.
        def __init__(self, message:str = "An internal error occurred", extras = None): # Raises an error pertaining to the Weaver Library itself.
            try:
                self.message = message
                if extras:
                    self.message = message + " ~> ["
                    for extra in extras:
                        if extra:
                            self.message += "'" + extra + "', "
                    self.message = self.message[:-2] + "]"
                super().__init__(self.message)
            except Exception as e:
                raise weaverError.InternalError(e)

# weaverNet class - HTTP Request tools!
class weaverNet:
    def cleanJson(d: dict) -> dict: # Take in a JSON object, and clean it (removing any null values)
        for key, value in list(d.items()):              # For every key/value you pair
            if str(type(d[key])) == "<class 'dict'>":   # If the value is a dictionary [similar to array]
                d[key] = weaverNet.cleanJson(d[key])    # Recursively clean it, then update the value
            else:                                       # Otherwise...
                if value is None or value == "None" or value == "none" or value == "null" or value == "":    # If the value is empty
                    del d[key]                          # Remove ('clean') it!
        return d                                        # Return 'cleaned' json!

    def generateAuthHeaders(token: str) -> dict: # Take token and return json headers for authed web requests
        return {'Authorization':'Bearer ' + token}

    def AUTH(url:str, req: dict, verifyHTTPS: bool = True, delay: int = 10) -> str: # This is just a POST request, but without the token.
        response = requests.post(url, json=req, verify=verifyHTTPS)
        sleep(delay/1000)
        return response.text

    def POST(url:str, token:str, req:dict, verifyHTTPS:bool = True, delay:int = 10) -> requests.Response: # HTTP POST Request
        response = requests.post(url, headers=weaverNet.generateAuthHeaders(token), json=req, verify=verifyHTTPS)
        sleep(delay/1000)
        return response

    def GET(url:str, token:str, verifyHTTPS:bool = True, delay:int = 10) -> requests.Response: # HTTP GET Request
        response = requests.get(url, headers=weaverNet.generateAuthHeaders(token), verify=verifyHTTPS)
        sleep(delay/1000)
        return response

    def PUT(url:str, token:str, req:dict, verifyHTTPS:bool = True, delay:int = 10) -> requests.Response: # HTTP PUT Request
        response = requests.put(url, headers=weaverNet.generateAuthHeaders(token), json=req, verify=verifyHTTPS)
        sleep(delay/1000)
        return response
    
    def DELETE(url:str, token:str, verifyHTTPS:bool = True, delay:int = 10) -> requests.Response: # HTTP DELETE Request
        response = requests.delete(url, headers=weaverNet.generateAuthHeaders(token), verify=verifyHTTPS)
        sleep(delay/1000)
        return response

class weaverValidation:
    class _definitions:            # This is a list of config entries, and what format they should be.
        channel_category = {
            "_id": str,
            "name": str,
            "desc": str
        }

        channel_source_options_srt = {
            "passphrase": str,
            "chunkSize": int,
            "encrypted": bool
        }

        channel_source = {
            "_id": str,
            "address": str,
            "protocol": int
        }

        channel = {
            "_id": str,
            "enabled": bool,
            "number": int,
            "name": str
        }
        
        output_options = {
            "type": int,
            "maxConnections": int,
            "maxBandwidth": int,
            "chunkSize": int,
            "latency": int,
            "ttl": int,
            "address": str,
            "port": int,
            "passphrase": str,
            "outputOneTTL": int,
            "outputOneAddress": str,
            "outputOnePort": int,
            "outputTwoTTL": int,
            "outputTwoAddress": str,
            "outputTwoPort": int,
            "pathDelay": int,
            "preserveHeaders": bool
        }

        output = {
            "stream": str,
            "name": str,
            "id": str,
            "paused": bool,
            "active": bool,
            "stopped": bool,
            "mwedge": str,
            "tags": str,
            "muteOnError": bool,
            "muteOnErrorPeriod": int
        }

        source_options_dashsevensource = {
            "enabled": bool,
            "sourceAddress": str,
            "enableCorrection": bool,
            "buffer": int,
            "useFEC": bool,
            "port": int,
            "address": str
        }

        source_options = {
            "limitBitrate": bool,
            "passphrase": str,
            "hostPort": int,
            "hostAddress": str,
            "latency": int,
            "address": str,
            "port": int,
            "chunkSize": int,
            "enableCorrection": bool,
            "useFEC": bool,
            "preserveHeaders": bool
        }

        source = {
            "_id": str,
            "stream": str,
            "priority": int,
            "name": str,
            "id": str,
            "paused": bool,
            "active": bool,
            "etr290Enabled": bool,
            "stopped": bool,
            "exhausted": bool,
            "mwedge": str,
            "passive": bool
        }

        stream = {
            "name": str,
            "id": str,
            "enableThumbnails": bool,
            "mwedge": str
        }

        edge = {
            "clientId": str,
            "_id": str,
            "externalIpAddress": str,
            "httpServerPort": int,
            "mwcore": str,
            "txcore": str,       
            "name": str,
            "online": bool,
            "topTalkersEnabled": bool,
            "version": str
        }

        device = {
            "_id": str,
            "serial": str,
            "clientVersion": str,
            "name": str,
            "manufacturer": str,
            "mac": str,
            "version": str,
            "model": str,
            "online": bool,
            "configuredAddress": str,
            "debug": bool,
            "checkedAt": str,
            "lastRebooted": str,
            "lastRefreshed": str,
            "licensed": bool,
            "location": str,
            "updatedAt": str,
            "createdAt": str,
            "powerState": int,
            "requiresRebootAt": str
        }

        device_network = {
            "dhcp": bool,
            "ip": str,
            "gateway": str,
            "dns": str,
            "mask": str,
            "externalIp": str,
            "ntpServer": str,
            "timeZone": str
        }

        users = {
            "_id": str,
            "deviceLimited": bool,
            "deviceLimit": int,
            "logonLimited": bool,
            "logonLimit": int,
            "username": str,
            "provider": str,
            "admin": bool,
            "tokenTimeout": int,
        }

        definitions_dictionary = {
            "<class 'weaver.Channel.Category'>": channel_category,
            "<class 'weaver.Channel.Source.Options.Srt'>": channel_source_options_srt,
            "<class 'weaver.Channel.Source'>": channel_source,
            "<class 'weaver.Channel'>": channel,
            "<class 'weaver.Output.Options'>": output_options,
            "<class 'weaver.Output'>": output,
            "<class 'weaver.Source.Options.DashSevenSource'>": source_options_dashsevensource,
            "<class 'weaver.Source.Options'>": source_options,
            "<class 'weaver.Source'>": source,
            "<class 'weaver.Stream'>": stream,
            "<class 'weaver.Edge'>": edge,
            "<class 'weaver.Device'>": device,
            "<class 'weaver.Device.Network'>": device_network,
            "<class 'weaver.Users'>": users,
        }

    class _requirements:             # This is just a list of config entries that we should warn if missing
        definitions_dictionary = {  # We should only add references here when there is something above!
        }

    def ValidateConfiguration(obj, objType: type) -> str | dict: # Takes an object and validates the config against the info held (if enabled)
        if not validateConfigurations:          # Actually, we should probably check if the user wants us to
            return obj                          # And if they don't, just give them their thing back unchanged
        
        if isinstance(obj, str):                # If they do, do we have json or string?
            obj_json = json.loads(obj)          # If string, load it to json
        else:
            obj_json = obj                      # If json, just use it
        
        target_defs_raw = None                  # Initialise a bunch of variables
        target_defs = None
        target_reqs_raw = None
        target_reqs = None
 
        try:
            target_defs = weaverValidation._definitions.definitions_dictionary[str(objType)]
        except Exception as e:
            throwaway = 0
        try:
            target_reqs = weaverValidation._requirements.definitions_dictionary[str(objType)]
        except:
            throwaway = 0

        if target_defs == None:             # If this is still None, it means we didn't match any object types
            return obj                          # So just return the original object (we may have not implemented it yet)

        for key, keyType in target_defs.items():      # Go through every key in the target definitions
            try:
                if obj_json[key] == "six two three three":
                    print("squeak")
                    exit()
                obj_json[key] = keyType(obj_json[key])
            except Exception as e:  # There's been an error in the casting, so something must be wrong...
                # So, if the error ISN'T just "'whatever-the-key-is'", then that means we found it...
                # But we couldn't cast it to the required type for some reason - it's bad config !! Tell them !!
                # Examples: While int("5") will return 5, int("five") etc. would fail, for example.
                # We can also do bool(0) / bool("false") and bool(1) / bool("true") to False and True,
                # but not bool("t") etc.
                
                if not str(e) == f"'{key}'" and obj_json[key]:
                    print(f"WARNING: Configuration entry '{key}' in object of type {objType} is neither correct, nor in a format that can be automatically converted. Expected '{keyType}', got {type(obj_json[key])}. Recommend you quit this script and validate your configuration.")
                    input()
                else:
                    # Ok, so the error WAS just "'whatever-the-key-is'" ... That just means the key isn't in the config!
                    # We should check that this is safe...
                    if target_reqs and str(e).replace("'", "") in target_reqs: # Remove the apostrophes and then check whether the key is present in the list of required values
                        # If it is - tell the user!
                        print(f"WARNING: An object of type {objType} is missing a required configuration parameter '{key}'. Press ENTER if this is expected, otherwise quit this script.")
                        input()
                # If not of these parameters match, that means it's probably just a key that's missing from the configuration,
                # But that isn't *required* / not always there.
        
        if isinstance(obj, str):                            # If we were given a string, return a string
            return json.dumps(obj_json)
        else:                                               # If we were given a json object, return a json object
            return obj_json

# weaverApi class
class weaverApi:
    def GetAuthKey(coreAddress:str, username:str, password:str) -> str: # Takes a prebuilt core object, username and password and returns API token. Returns string token.
        resp = json.loads(weaverNet.AUTH(coreAddress + '/auth/signin', {'username':username,'password':password}))    # Set 'resp' to the JSON response from the AUTH request
        try:
            return resp["token"]                                                                                      # This returns the value of the 'token' key (i.e. the token)
        except:
            return "Incorrect credentials!"                                                                           # This returns if there is no token key (i.e. wrong creds)

    def GetCoreVersion(c:'Core'):
        try:
            url = f"{c.coreAddress}/api/settings"
            return json.loads(weaverNet.GET(url, c.authToken, c.verifyHTTPS, c.defaultCallDelayMillis).text).get("version")
        except Exception:
            return "0.0.0"

    def GetDevices(c:'Core', jsonQuery:str = "") -> requests.Response: # Takes a prebuilt core object (and optionally json query string) and calls the API to get an edge from its ID. Returns unprocessed call response.
        if jsonQuery != "" and not jsonQuery.startswith("?"):
            jsonQuery = f"?{jsonQuery}"
        url = f"{c.coreAddress}/api/devices{jsonQuery}"
        response = weaverNet.GET(url, c.authToken, c.verifyHTTPS, c.defaultCallDelayMillis)
        weaverError.checkForError(response, extras=["GetDevices", url])
        return response

    def GetCurrentUser(c: 'Core') -> requests.Response:
        url = f"{c.coreAddress}/api/currentUser"
        response = weaverNet.GET(url, c.authToken, c.verifyHTTPS, c.defaultCallDelayMillis)
        return response

    def GetUsers(c:'Core', jsonQuery:str = "") -> requests.Response: # Takes a prebuilt core object (and optionally json query string) and calls the API to get an edge from its ID. Returns unprocessed call response.
        if jsonQuery != "" and not jsonQuery.startswith("?"):
            jsonQuery = f"?{jsonQuery}"
        url = f"{c.coreAddress}/api/users{jsonQuery}"
        response = weaverNet.GET(url, c.authToken, c.verifyHTTPS, c.defaultCallDelayMillis)
        weaverError.checkForError(response, extras=["GetUsers", url])
        return response

    def GetEdges(c:'Core', jsonQuery:str = "") -> requests.Response: # Takes a prebuilt core object (and optionally json query string) and calls the API to get all edges matching the query. Returns unprocessed call response.
        if jsonQuery != "" and not jsonQuery.startswith("?"):                   # If there is a query (e.g. "online=true") and it doesn't start with a ?
            jsonQuery = "?" + jsonQuery                                         # Prepend a ?
        url = c.coreAddress + "/api/mwedges" + jsonQuery                         # Now create the request url (core + /api/mwedges + query)
        response = weaverNet.GET(url, c.authToken, c.verifyHTTPS, c.defaultCallDelayMillis)                             # Return the response of the GET request
        weaverError.checkForError(response, extras=["GetEdges", url])
        return response

    def GetEdgeById(c:'Core', edgeId:str) -> requests.Response: # Takes a prebuilt core object and calls the API to get an edge from its ID. Returns unprocessed call response.
        url = c.coreAddress + "/api/mwedge/" + edgeId                           # Now create the request url (core + /api/mwedges/ + id)
        response = weaverNet.GET(url, c.authToken, c.verifyHTTPS, c.defaultCallDelayMillis)                             # Return result of GET request.
        weaverError.checkForError(response, extras=["GetEdgeById", edgeId, url])
        return response

    def UpdateEdge(e:'Edge') -> requests.Response: # Takes a prebuilt edge object and calls the API to update it. Returns unprocessed call response.
        url = e.coreObject.coreAddress + "/api/mwedge/" + e._id                                                 # Build req URL from ID's
        response = weaverNet.PUT(url, e.coreObject.authToken, e.to_json(), e.coreObject.verifyHTTPS, e.coreObject.defaultCallDelayMillis)                   # Return result of the Update Request (serializing 'e' into json)
        weaverError.checkForError(response, extras=["UpdateEdge", url])
        return response

    def CreateOutput(o:'Output') -> requests.Response: # Takes a prebuilt output object and calls the API to create it. Returns unprocessed call response.
        url = o.edgeObject.coreObject.coreAddress + "/api/mwedge/" + o.edgeObject._id + "/output/"              # Build req URL from ID's
        response = weaverNet.POST(url, o.edgeObject.coreObject.authToken, o.to_json(), o.edgeObject.coreObject.verifyHTTPS, o.edgeObject.coreObject.defaultCallDelayMillis)                  # Return result of the Update Request (serializing 'o' into json)
        weaverError.checkForError(response, extras=["CreateOutput", url])
        return response

    def UpdateOutput(o:'Output') -> requests.Response: # # Takes a prebuilt output object and calls the API to update it. Returns unprocessed call response.
        url = o.edgeObject.coreObject.coreAddress + "/api/mwedge/" + o.edgeObject._id + "/output/" + o.id      # Build req URL from ID's
        response = weaverNet.PUT(url, o.edgeObject.coreObject.authToken, o.to_json(), o.edgeObject.coreObject.verifyHTTPS, o.edgeObject.coreObject.defaultCallDelayMillis)                   # Return result of the Update Request (serializing 'o' into json)
        weaverError.checkForError(response, extras=["UpdateOutput", url])
        return response

    def CreateSource(s:'Source') -> requests.Response: # Takes a prebuilt source object and calls the API to create it. Returns unprocessed call response.
        url = s.edgeObject.coreObject.coreAddress + "/api/mwedge/" + s.edgeObject._id + "/source/"              # Build req URL from ID's
        response = weaverNet.POST(url, s.edgeObject.coreObject.authToken, s.to_json(), s.edgeObject.coreObject.verifyHTTPS, s.edgeObject.coreObject.defaultCallDelayMillis)
        weaverError.checkForError(response, extras=["CreateSource", url])
        return response

    def UpdateSource(s:'Source') -> requests.Response: # Takes a prebuilt source object and calls the API to update it. Returns unprocessed call response.
        url = s.edgeObject.coreObject.coreAddress + "/api/mwedge/" + s.edgeObject._id + "/source/" + s.id      # Build req URL from ID's
        response = weaverNet.PUT(url, s.edgeObject.coreObject.authToken, s.to_json(), s.edgeObject.coreObject.verifyHTTPS, s.edgeObject.coreObject.defaultCallDelayMillis)                   # Return result of the Update Request (serializing 's' into json)
        weaverError.checkForError(response, extras=["UpdateSource", url])
        return response

    def CreateStream(st:'Stream') -> requests.Response: # Takes a prebuilt stream object and calls the API to create it. Returns unprocessed call response.
        url = st.edgeObject.coreObject.coreAddress + "/api/mwedge/" + st.edgeObject._id + "/stream/"             # Build req URL from ID's
        response = weaverNet.POST(url, st.edgeObject.coreObject.authToken, st.to_json(), st.edgeObject.coreObject.verifyHTTPS, st.edgeObject.coreObject.defaultCallDelayMillis)                 # Return result of the Update Request (serializing 'st' into json)
        weaverError.checkForError(response, extras=["CreateStream", url])
        return response
    
    def CreateMultiple(core: 'Core', edge: 'Edge', streams: List['Stream'] = [], sources: List['Source'] = [], outputs: List['Output'] = []) -> requests.Response: # Takes a prebuilt stream object and calls the API to create it. Returns unprocessed call response.
        url = core.coreAddress + "/api/mwedge/" + edge._id             # Build req URL from ID's
        streams_json = []
        for stream in streams:
            streams_json.append(stream.to_json())
        sources_json = []
        for source in sources:
            sources_json.append(source.to_json())
        outputs_json = []
        for output in outputs:
            outputs_json.append(output.to_json())
        j_body = {"streams": streams_json, "sources": sources_json, "outputs": outputs_json}
        response = weaverNet.POST(url, core.authToken, j_body, core.verifyHTTPS, core.defaultCallDelayMillis)                 # Return result of the Update Request (serializing 'st' into json)
        print(response.text)
        weaverError.checkForError(response, extras=["CreateMultiple", url])
        return response

    def UpdateStream(st:'Stream') -> requests.Response: # Takes a stream stream object and calls the API to update it. Returns unprocessed call response.
        url = st.edgeObject.coreObject.coreAddress + "/api/mwedge/" + st.edgeObject._id + "/stream/" + st.id       # Build req URL from ID's
        response = weaverNet.PUT(url, st.edgeObject.coreObject.authToken, st.to_json(), st.edgeObject.coreObject.verifyHTTPS, st.edgeObject.coreObject.defaultCallDelayMillis)                   # Return result of the Update Request (serializing 's' into json)
        weaverError.checkForError(response, extras=["UpdateStream", url])
        return response

    def UpdateDevice(d:'Device') -> requests.Response: # Takes a prebuilt Device object and calls the API to update it. Returns unprocessed call response.
        url = d.coreObject.coreAddress + "/api/device/" + d._id      # Build req URL from ID's
        response = weaverNet.PUT(url, d.coreObject.authToken, d.to_json(), d.coreObject.verifyHTTPS, d.coreObject.defaultCallDelayMillis)                   # Return result of the Update Request (serializing 's' into json)
        weaverError.checkForError(response, extras=["UpdateDevice", url])
        return response
    
    def RebootDevice(d:'Device') -> requests.Response: # Takes a prebuilt Device object and calls the API to update it. Returns unprocessed call response.
        url = d.coreObject.coreAddress + "/api/device/" + d._id + "/reboot"      # Build req URL from ID's
        response = weaverNet.GET(url, d.coreObject.authToken, d.coreObject.verifyHTTPS, d.coreObject.defaultCallDelayMillis)                   # Return result of the Update Request (serializing 's' into json)
        weaverError.checkForError(response, extras=["UpdateDevice", url])
        return response
    
    def RefreshDevice(d:'Device') -> requests.Response: # Takes a prebuilt Device object and calls the API to update it. Returns unprocessed call response.
        url = d.coreObject.coreAddress + "/api/device/" + d._id + "/reload"      # Build req URL from ID's
        response = weaverNet.GET(url, d.coreObject.authToken, d.coreObject.verifyHTTPS, d.coreObject.defaultCallDelayMillis)                   # Return result of the Update Request (serializing 's' into json)
        weaverError.checkForError(response, extras=["UpdateDevice", url])
        return response
    
    def UpgradeDeviceFirmware(d:'Device', u:str) -> requests.Response: # Takes a prebuilt Device object and calls the API to update it. Returns unprocessed call response.
        url = d.coreObject.coreAddress + "/api/device/" + d._id + f"/upgrade"      # Build req URL from ID's
        response = weaverNet.PUT(url, d.coreObject.authToken, {"url": u}, d.coreObject.verifyHTTPS, d.coreObject.defaultCallDelayMillis)                   # Return result of the Update Request (serializing 's' into json)
        weaverError.checkForError(response, extras=["UpgradeDeviceFirmware", url])
        return response

    def UpdateUser(d:'User') -> requests.Response: # Takes a prebuilt Users object and calls the API to update it. Returns unprocessed call response.
        url = d.coreObject.coreAddress + "/api/user/" + d._id      # Build req URL from ID's
        response = weaverNet.PUT(url, d.coreObject.authToken, d.to_json(), d.coreObject.verifyHTTPS, d.coreObject.defaultCallDelayMillis)                   # Return result of the Update Request (serializing 's' into json)
        weaverError.checkForError(response, extras=["UpdateUsers", url])
        return response

    def GetChannels(core:'Core', jsonQuery:str = "") -> requests.Response: # Takes a prebuilt core object and calls the API to get the channels. Returns unprocessed call response.
        if jsonQuery != "" and not jsonQuery.startswith("?"):                   # If there is a query (e.g. "number=10") and it doesn't start with a ?
            jsonQuery = "?" + jsonQuery                                         # Prepend a ?
        url = core.coreAddress + "/api/channels" + jsonQuery                 # Now create the request url (core + /api/mwedges/ + query)
        
        response = weaverNet.GET(url, core.authToken, core.verifyHTTPS, core.defaultCallDelayMillis)   # Return the response of the GET request
        weaverError.checkForError(response, extras=["GetChannels", url])
        return response

    def UpdateChannel(channel:'Channel') -> requests.Response: # Takes a prebuilt channel object and calls the API to update it. Returns unprocessed call response.
        url = channel.coreObject.coreAddress + "/api/channel/" + channel._id
        response = weaverNet.PUT(url, channel.coreObject.authToken, channel.to_json(), channel.coreObject.verifyHTTPS, channel.coreObject.defaultCallDelayMillis)
        weaverError.checkForError(response, extras=["UpdateChannel", url])
        return response
    
    def CreateChannel(channel:'Channel') -> requests.Response: # Takes a prebuilt channel object and calls the API to create it. Returns unprocessed call response.
        url = channel.coreObject.coreAddress + "/api/channel"
        response = weaverNet.POST(url, channel.coreObject.authToken, channel.to_json(), channel.coreObject.verifyHTTPS, channel.coreObject.defaultCallDelayMillis)
        weaverError.checkForError(response, extras=["CreateChannel", url])
        return response
    
    def DeleteChannel(channel:'Channel') -> requests.Response: # Takes a prebuilt channel object and calls the API to delete it. Returns unprocessed call response.
        url = channel.coreObject.coreAddress + f"/api/channel/{channel._id}" 
        response = weaverNet.DELETE(url, channel.coreObject.authToken, channel.coreObject.verifyHTTPS, channel.coreObject.defaultCallDelayMillis)
        weaverError.checkForError(response, extras=["DeleteChannel", url])
        return response  
      
    def DeleteSource(source:'Source') -> requests.Response: # Takes a prebuilt source object and calls the API to delete it. Returns unprocessed call response.
        url = source.edgeObject.coreObject.coreAddress + f"/api/mwedge/{source.edgeObject._id}/source/{source.id}"
        response = weaverNet.DELETE(url, source.edgeObject.coreObject.authToken, source.edgeObject.coreObject.verifyHTTPS, source.edgeObject.coreObject.defaultCallDelayMillis)
        weaverError.checkForError(response, extras=["DeleteSource", url])
        return response
    
    def DeleteOutput(output:'Output') -> requests.Response: # Takes a prebuilt output object and calls the API to delete it. Returns unprocessed call response.
        url = output.edgeObject.coreObject.coreAddress + f"/api/mwedge/{output.edgeObject._id}/output/{output.id}" 
        response = weaverNet.DELETE(url, output.edgeObject.coreObject.authToken, output.edgeObject.coreObject.verifyHTTPS, output.edgeObject.coreObject.defaultCallDelayMillis)
        weaverError.checkForError(response, extras=["DeleteOutput", url])
        return response
    
    def DeleteStream(stream:'Stream') -> requests.Response: # Takes a prebuilt stream object and calls the API to delete it. Returns unprocessed call response.
        url = stream.edgeObject.coreObject.coreAddress + f"/api/mwedge/{stream.edgeObject._id}/stream/{stream.id}" 
        response = weaverNet.DELETE(url, stream.edgeObject.coreObject.authToken, stream.edgeObject.coreObject.verifyHTTPS, stream.edgeObject.coreObject.defaultCallDelayMillis)
        weaverError.checkForError(response, extras=["DeleteStream", url])
        return response   
    
    def ClearStats(object) -> requests.Response: # Clear stats on source, output or stream
        objtype = type(object).__name__.lower().replace("weaver.", "")
        url = object.edgeObject.coreObject.coreAddress + f"/api/mwedge/{object.edgeObject._id}/{objtype}/{object.id}/resetStats"
        response = weaverNet.POST(url, object.edgeObject.coreObject.authToken, {}, object.edgeObject.coreObject.verifyHTTPS, object.edgeObject.coreObject.defaultCallDelayMillis)
        return response

string_types = (type(b''), type(u''))
def deprecated(reason):
    """
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.
    """

    if isinstance(reason, string_types):

        # The @deprecated is used with a 'reason'.
        #
        # .. code-block:: python
        #
        #    @deprecated("please, use another function")
        #    def old_function(x, y):
        #      pass

        def decorator(func1):

            if inspect.isclass(func1):
                fmt1 = "Call to deprecated class {name} ({reason})."
            else:
                fmt1 = "Call to deprecated function {name} ({reason})."

            @functools.wraps(func1)
            def new_func1(*args, **kwargs):
                warnings.simplefilter('always', DeprecationWarning)
                warnings.warn(
                    fmt1.format(name=func1.__name__, reason=reason),
                    category=DeprecationWarning,
                    stacklevel=2
                )
                warnings.simplefilter('default', DeprecationWarning)
                return func1(*args, **kwargs)

            return new_func1

        return decorator

    elif inspect.isclass(reason) or inspect.isfunction(reason):

        # The @deprecated is used without any 'reason'.
        #
        # .. code-block:: python
        #
        #    @deprecated
        #    def old_function(x, y):
        #      pass

        func2 = reason

        if inspect.isclass(func2):
            fmt2 = "Call to deprecated class {name}."
        else:
            fmt2 = "Call to deprecated function {name}."

        @functools.wraps(func2)
        def new_func2(*args, **kwargs):
            warnings.simplefilter('always', DeprecationWarning)
            warnings.warn(
                fmt2.format(name=func2.__name__),
                category=DeprecationWarning,
                stacklevel=2
            )
            warnings.simplefilter('default', DeprecationWarning)
            return func2(*args, **kwargs)

        return new_func2

    else:
        raise TypeError(repr(type(reason)))


def generateId(length: int = 48) -> str:
    """
    Generates a random hexadecimal string of a given length.

    Note: This is not cryptographically secure. Use for non-sensitive
    purposes like generating random IDs.

    Args:
        length: The desired length of the hexadecimal string.

    Returns:
        A random hexadecimal string of the specified length.
    """
    return ''.join(random.choice(string.hexdigits.lower()) for _ in range(length))

def compareVersions(version_a: str, version_b: str, return_if_tie: True):
    """
    Compares two version strings.

    If version a > b, return True. If a < b, return False. 
    If a == b, return the value of return_if_tie.
    Handles version formats like 'a.b.c' and ignores suffixes like '-beta1'.

    Args:
        version_a: The first version string.
        version_b: The second version string.
        return_if_tie: The boolean value to return if the versions are equal.

    Returns:
        The result of the comparison.
    """
    # Isolate the main version number by splitting on any suffix
    main_version_a = version_a.split('-')[0]
    main_version_b = version_b.split('-')[0]

    # Split version strings into parts and convert them to integers
    parts_a = [int(p) for p in main_version_a.split('.')]
    parts_b = [int(p) for p in main_version_b.split('.')]

    # Get the length of the longer version number for iteration
    max_len = max(len(parts_a), len(parts_b))

    for i in range(max_len):
        # Use 0 if a version part is missing (e.g., comparing '1.2' with '1.2.0')
        v_a = parts_a[i] if i < len(parts_a) else 0
        v_b = parts_b[i] if i < len(parts_b) else 0

        if v_a > v_b:
            return True
        if v_a < v_b:
            return False
            
    # If the loop completes without returning, the versions are identical
    return return_if_tie

# Channel Class
class Channel:   
    # Channel, Source subclass
    class Source:
        class Options:
            class Srt:
                def __init__(self, data: dict = "{}") -> 'Channel.Source.Options.Srt': # Constructor. Take dict/str representation of data to construct from
                    if not data:
                        data = json.loads("{}")
                    self.encrypted = data.get("encrypted") # AES encryption
                    self.passphrase: str = data.get("passphrase") # <str> SRT passphrase
                    self.chunkSize: int = data.get("chunkSize") # <int> SRT Chunk size

                def __str__(self):
                    return json.dumps(self.to_json())
                
                def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
                    return self.__str__()

                def to_json(self) -> dict: # Convert to cleaned json dict
                    my_json = weaverValidation.ValidateConfiguration({
                        "encrypted": self.encrypted,
                        "passphrase": self.passphrase,
                        "chunkSize": self.chunkSize
                    }, type(self))
                    return weaverNet.cleanJson(my_json)
                
            class Biss2:
                def __init__(self, data: dict = "{}") -> 'Channel.Source.Options.Biss2': # Constructor. Take dict/str representation of data to construct from
                    if not data:
                        data = json.loads("{}")
                    self.encrypted: bool = data.get("encrypted") # <bool> Biss encrypted?
                    self.oddKey: str = data.get("oddKey") # <str> SRT passphrase
                    self.evenKey: str = data.get("evenKey") # <int> SRT Chunk size

                def __str__(self):
                    return json.dumps(self.to_json())
                
                def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
                    return self.__str__()
                
                def to_json(self) -> dict: # Convert to cleaned json dict
                    my_json = weaverValidation.ValidateConfiguration({
                        "encrypted": self.encrypted,
                        "oddKey": self.oddKey,
                        "evenKey": self.evenKey
                    }, type(self))
                    return weaverNet.cleanJson(my_json)
                
            def __init__(self, data_raw: dict | str = "{}") -> 'Channel.Source.Options': # Constructor. Take dict/str representation of data to construct from
                if not data_raw:
                    data_raw = json.loads("{}")
                if type(data_raw) == str:
                    data = json.loads(data_raw)
                else:
                    data = data_raw
                self.srt: Channel.Source.Options.Srt = Channel.Source.Options.Srt(data.get("srt")) # <Channel.Source.Options.Srt> Not instantiable.
                self.biss2: Channel.Source.Options.Biss2 = Channel.Source.Options.Biss2(data.get("biss2")) # <Channel.Source.Options.Srt> Not instantiable.

            def __str__(self):
                return json.dumps(self.to_json())
            
            def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
                return self.__str__()

           
            def to_json(self) -> dict: # Convert to cleaned json
                try:
                    if self:
                        my_json = weaverValidation.ValidateConfiguration({
                            "srt": self.srt.to_json(),
                            "biss2": self.biss2.to_json()
                        }, type(self))
                        return weaverNet.cleanJson(my_json)
                    else:
                        return None
                except:
                    return None

        def __init__(self, data_raw: dict | str) -> 'Channel.Source': # Constructor. Take dict/str representation of data to construct from
            if type(data_raw) == str:
                data = json.loads(data_raw)
            else:
                data = data_raw
            self._id: str = data.get("_id") # <str> Channel Source ID
            self.address: str = data.get("address") # <str> Channel Source Address
            self.protocol: str = data.get("protocol") # <str> Channel Source Protocol
            self.geofence: str = data.get("geofence") # <str>
            self.priority: int = data.get("priority") # <int> Priority of this source over others on the channel
            try:
                self.options: Channel.Source.Options = Channel.Source.Options(data.get("options", {}))
            except:
                throwaway = 0

        def __str__(self):
            return json.dumps(self.to_json())
        
        def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
            return self.__str__()
        
        def to_json(self) -> dict: # Convert to cleaned json
            if self:
                if self.options:
                    my_json = weaverValidation.ValidateConfiguration({
                        "_id": self._id,
                        "address": self.address,
                        "protocol": self.protocol,
                        "geofence": self.geofence,
                        "priority": self.priority,
                        "options": self.options.to_json()
                    }, type(self))
                else:
                    my_json = weaverValidation.ValidateConfiguration({
                        "_id": self._id,
                        "address": self.address,
                        "protocol": self.protocol,
                        "geofence": self.geofence,
                        "priority": self.priority
                    }, type(self))
                return weaverNet.cleanJson(my_json)
            else:
                return None

    def __init__(self, data_raw: dict | str, core: 'Core') -> 'Channel': # Constructor. Take dict/str representation of data to construct from, and the core object on which the channel is found
        if type(data_raw) == str:
            data = json.loads(data_raw)
        else:
            data = data_raw
        self._id: str = data.get("_id")  # <str> Channel ID
        self.enabled: bool = data.get("enabled") # <bool>
        self.number: int = data.get("number") # <int> Channel Number
        self.name: str = data.get("name") # <str> Channel Name
        self.createdAt: str = data.get("createdAt") # <str> Created Timestamp
        self.updatedAt: str = data.get("updatedAt") # <str> Updated Timestamp
        try: # I think this if / elif is wrong way round -- shouldn't the json.loads be if category type is str?
            if type (data.get("category") == str):
                self.category: str = data.get("category")
            elif type (data.get("category" == dict)):
                self.category = json.loads(data.get("category")).get("_id")
            else:
                self.category = None
        except:
            self.category = Channel.Category(json.loads("{}"))
        self.__v = data.get("__v")
        self.epgChannel = data.get("epgChannel")
        if data.get("sources"):
            self.sources: List[Channel.Source] = [Channel.Source(source_data) for source_data in data.get("sources")] # <Channel.Source[]> Objects of all sources on this channel
        else:
            self.sources: List[Channel.Source] = []
        self.coreObject: Core = core # <Weaver.Core> Associated tx core object

    def __str__(self):
        return json.dumps(self.to_json())
    
    def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
        return self.__str__()
    
    def to_json(self) -> dict: # Convert to cleaned json
        my_json = weaverValidation.ValidateConfiguration({
            "_id": self._id,
            "enabled": self.enabled,
            "number": self.number,
            "name": self.name,
            "category": self.category,
            "__v": self.__v,
            "epgChannel": self.epgChannel,
            "sources": [source.to_json() for source in self.sources]
        }, type(self))
        return weaverValidation.ValidateConfiguration(weaverNet.cleanJson(my_json), type(self))

    def Update(self) -> bool:
        """
        Perform API call to update channel with the locally made changes.

        Returns:
            The boolean outcome of the API call.
        """
        try:
            resp = weaverApi.UpdateChannel(self)
            return True
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return False
    
    def Delete(self) -> bool:
        """
        Delete channel from tx core.

        Returns:
            The boolean outcome of the API call.
        """
        try:
            resp = weaverApi.DeleteChannel(self)
            return not weaverError.checkForError(resp)
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return False

class Device:
    class Network:
        def __init__(self, data_raw: dict | str) -> 'Device.Network': # Constructor. Take dict/str representation of data to construct from
            if type(data_raw) == str:
                data = json.loads(data_raw)
            else:
                data = data_raw
            self.dhcp: bool = data.get("dhcp") # <bool> 
            self.ip: str = data.get("ip") # <str> 
            self.gateway: str = data.get("gateway") # <str> 
            self.dns: str = data.get("dns") # <str>
            self.mask: str = data.get("mask") # <str>
            self.externalIp: str = data.get("externalIp") # <str>
            self.ntpServer: str = data.get("ntpServer") # <str>
            self.timeZone: str = data.get("timeZone") # <str>

        def __str__(self):
            return json.dumps(self.to_json())
        
        def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
            return self.__str__()
        
        def to_json(self) -> dict: # Convert to uncleaned json
            if self:
                return weaverValidation.ValidateConfiguration({
                    "dhcp": self.dhcp,
                    "ip": self.ip,
                    "gateway": self.gateway,
                    "dns": self.dns,
                    "mask": self.mask,
                    "externalIp": self.externalIp,
                    "ntpServer": self.ntpServer,
                    "timeZone":self.timeZone
                }, type(self))
            else:
                return weaverValidation.ValidateConfiguration({
                    "dhcp": self.dhcp,
                    "ip": self.ip,
                    "gateway": self.gateway,
                    "dns": self.dns,
                    "mask": self.mask,
                    "externalIp": self.externalIp,
                    "ntpServer": self.ntpServer,
                    "timeZone":self.timeZone
                }, type(self))

    def __init__(self, coreObject: 'Core', Json: dict = "{}") -> 'Device': # Constructor. Take the core object this device belongs to, and  dict/str representation of data to construct from
        if not Json:
            Json = json.loads("{}")
        if isinstance(Json, str):
            data = json.loads(Json)
        else:
            data = Json
        self._id:str = data.get("_id") # <str> Device ID
        self.serial: str = data.get("serial") # <str> Device serial number / ID
        self.clientVersion: str = data.get("online") # <str> Device agent version
        self.name: str = data.get("name") # <str> Device name
        self.manufacturer: str = data.get("manufacturer") # <str> Device manufacturer
        self.mac: str = data.get("mac") # <str> Device MAC address
        self.version: str = data.get("version") # <str> Device firmware version
        self.model: str = data.get("model") # <str>
        self.online: bool = data.get("online") # <bool>
        self.configuredAddress: str = data.get("configuredAddress") # <str>
        self.debug: bool = data.get("debug") # <bool>
        self.checkedAt: str = data.get("checkedAt") # <str> Timestamp device last checked in
        self.lastRebooted: str = data.get("lastRebooted") # <str> Timestamp of last device reboot
        self.lastRefreshed: str = data.get("lastRefreshed") # <str> Timestamp of last device refresh
        self.licensed: bool = data.get("licensed") # <bool>
        self.location: str = data.get("location") # <str> Device location
        self.updatedAt: str = data.get("updatedAt") # <str> Timestamp of last device information update
        self.createdAt: str = data.get("createdAt") # <str> Timestamp of device creation / first connection to this tx core
        self.powerState = data.get("powerState")
        self.requiresRebootAt: str = data.get("requiresRebootAt") # <str> Timestamp device should next be rebooted at / by
        try:
            self.channel: Channel = Channel(data.get("channel"), coreObject) # Channel object (in line with channel.md in docs) representing currently playing channel
        except:
            self.channel = None
        self.ip_address = data.get("network").get("ip") # <str> Device IP Address. This is a temporary value, eventually all of network will be pulled, and this value WILL BE DEPRECATED AND REMOVED!! You have been warned.
        self.coreObject: Core = coreObject
        try:
            self.network: Device.Network = Device.Network(data.get("network", {})) # Constructor
        except:
            throwaway = 0

    def __str__(self):
        return json.dumps(self.to_json())
    
    def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
        return self.__str__()
    
    def Update(self) -> bool:
        """
        Perform API call to update device with the locally made changes

        Returns:
            The boolean outcome of the API call.
        """
        try:
            resp = weaverApi.UpdateDevice(self)
            return True
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return False
        
    def Reboot(self) -> bool:
        """
        Request that the device reboot.

        Returns:
            The boolean outcome of the API call.
        """
        try:
            respt = weaverApi.RebootDevice(self)
            return True
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
        return False
        
    def Refresh(self) -> bool: # Refresh device
        """
        Request that the device refresh

        Returns:
            The boolean outcome of the API call.
        """
        try:
            resp = weaverApi.RefreshDevice(self)
            return True
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
        return False
    
    def Reload(self) -> bool: # Alias for Refresh
        """
        Request that the device refresh

        Returns:
            The boolean outcome of the API call.
        """
        return self.Refresh()

    def UpgradeFirmware(self, url: str) -> str:
        """
        Requests that the device performs a firmware upgrade using the firmware at the supplied URL.

        Args:
            url: String URL to where the firmware package is available to be pulled.

        Returns:
            The boolean outcome of the API call (not the outcome of the upgrade).
        """
        try:
            resp = weaverApi.UpgradeDeviceFirmware(self, url).text
            return resp
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return False

    def to_json(self) -> dict: # Convert to cleaned json
        dirty = {
            "_id": self._id,
            "serial": self.serial,
            "clientVersion": self.clientVersion,
            "name": self.name,
            "manufacturer": self.manufacturer,
            "mac": self.mac,
            "version": self.version,
            "model": self.model,
            "online": self.online,
            "configuredAddress": self.configuredAddress,
            "debug": self.debug,
            "checkedAt": self.checkedAt,
            "lastRebooted": self.lastRebooted,
            "lastRefreshed": self.lastRefreshed,
            "licensed": self.licensed,
            "location": self.location,
            "updatedAt": self.updatedAt,
            "createdAt": self.createdAt,
            "powerState": self.powerState,
            "requiresRebootAt": self.requiresRebootAt,
            "network": self.network.to_json()
        }
        return weaverValidation.ValidateConfiguration(weaverNet.cleanJson(dirty), type(self))

class User:
    def __init__(self, coreObject: 'Core', Json: dict = "{}") -> 'User': # Constructor. Take the core object this users belongs to, and  dict/str representation of data to construct from
        if not Json:
            Json = json.loads("{}")
        if isinstance(Json, str):
            data = json.loads(Json)
        else:
            data = Json
        self._id:str = data.get("_id") # <str> Device ID
        self.deviceLimited: bool = data.get("deviceLimited") 
        self.deviceLimit: int = data.get("deviceLimit")
        self.logonLimited: bool = data.get("logonLimited") 
        self.logonLimit: int = data.get("logonLimit")
        self.username: str = data.get("username")
        self.provider: str = data.get("provider")
        self.admin: bool = data.get("admin")
        self.tokenTimeout: int = data.get("tokenTimeout")
        self.coreObject = coreObject

    def __str__(self):
        return json.dumps(self.to_json())
    
    def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
        return self.__str__()
    
    def Update(self) -> bool:
        """
        Peform API call to update user with locally made changes.

        Returns:
            The boolean outcome of the API call.
        """
        try:
            resp = weaverApi.UpdateUser(self)
            return True
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return False

    def to_json(self) -> dict: # Convert to cleaned json
        dirty = {
            "_id": self._id,
            "deviceLimited": self.deviceLimited,
            "deviceLimit": self.deviceLimit,
            "logonLimited": self.logonLimited,
            "logonLimit": self.logonLimit,
            "username": self.username,
            "provider": self.provider,
            "admin": self.admin,
            "tokenTimeout": self.tokenTimeout,
        }
        return weaverValidation.ValidateConfiguration(weaverNet.cleanJson(dirty), type(self))

class Output:
    class Options:
        def __init__(self, options_data_input: str = "") -> 'Output.Options': # Constructor. Take dict/str representation of data to construct from
            if isinstance(options_data_input, str):
                options_data = json.loads(options_data_input)
            else:
                options_data = options_data_input
            self.type: str = options_data.get("type") # <str> Output type
            self.networkInterface: str = options_data.get("networkInterface") # <str> Network interface IP. E.g., if ui: "eno1 [1.2.3.4]" then enter "1.2.3.4"
            self.hostAddress: str = options_data.get("hostAddress") # <str> Host address in IP form for SRT. E.g., if ui: "eno1 [1.2.3.4]" then enter "1.2.3.4"
            self.maxConnections: int = options_data.get("maxConnections") # <int> Maximum number of concurrent connections to allow for SRT
            self.maxBandwidth: int = options_data.get("maxBandwidth") # <int> Max bandwidth for SRT
            self.chunkSize: int = options_data.get("chunkSize") # <int> Chunk size
            self.streamId: str = options_data.get("streamId") # <str> Stream ID for SRT streams (optional)
            self.retransmitAlgorithm = options_data.get("retransmitAlgorithm") # SRT retransmit algorithm to use
            self.latency: int = options_data.get("latency") # <int> SRT latency in ms
            self.serviceType = options_data.get("serviceType") #
            self.ttl: int = options_data.get("ttl") # <int> TTL
            self.encryption: int = options_data.get("encryption") # <int> Encryption type (e.g. 32 = AES256)
            self.encryptionType = options_data.get("encryptionType") # Scrambling type (i.e. biss2)
            self.encryptionPercentage: int = options_data.get("encryptionPercentage") # <int>
            self.encryptionKeyParity = options_data.get("encryptionKeyParity") # Odd or Even key parity
            self.encryptionOddKey: str = options_data.get("encryptionOddKey") # <str> Biss2 Odd Key
            self.encryptionEvenKey: str = options_data.get("encryptionEvenKey") # <str> Biss2 Even Key
            self.logLevel = options_data.get("logLevel") # SRT Log level
            self.srtVersion: str = options_data.get("srtVersion") # <str> SRT Version (1.4.4 or 1.5.1)
            self.hostPort: int = options_data.get("hostPort") # <int>
            self.address: str = options_data.get("address") # <str>
            self.port: int = options_data.get("port") # <int>
            self.passphrase: str = options_data.get("passphrase") # <str>
            self.outputOneTTL: int = options_data.get("outputOneTTL") # <int>
            self.outputOneNetworkInterface: str = options_data.get("outputOneNetworkInterface") # <str>
            self.outputOneAddress: str = options_data.get("outputOneAddress") # <str>
            self.outputOnePort: int = options_data.get("outputOnePort") # <int>
            self.outputTwoTTL: int = options_data.get("outputTwoTTL") # <int>
            self.outputTwoNetworkInterface: str = options_data.get("outputTwoNetworkInterface") # <str>
            self.outputTwoAddress: str = options_data.get("outputTwoAddress") # <str>
            self.outputTwoPort: int = options_data.get("outputTwoPort") # <int>
            self.preserveHeaders: bool = options_data.get("preserveHeaders") # <bool>
            self.pathDelay: int = options_data.get("pathDelay") # <int>
            self.bindDevice: str = options_data.get("bindDevice") # <str> SRT process device to bind to

        def __str__(self):
            return json.dumps(self.to_json())
        
        def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
            return self.__str__()

        def to_json(self) -> dict: # Convert to uncleaned json
            return weaverValidation.ValidateConfiguration({
                "type": self.type,
                "networkInterface": self.networkInterface,
                "hostAddress": self.hostAddress,
                "maxConnections": self.maxConnections,
                "maxBandwidth": self.maxBandwidth,
                "chunkSize": self.chunkSize,
                "streamId": self.streamId,
                "retransmitAlgorithm": self.retransmitAlgorithm,
                "latency": self.latency,
                "serviceType": self.serviceType,
                "ttl": self.ttl,
                "encryption": self.encryption,
                "encryptionType": self.encryptionType,
                "encryptionPercentage": self.encryptionPercentage,
                "encryptionKeyParity": self.encryptionKeyParity,
                "encryptionOddKey": self.encryptionOddKey,
                "encryptionEvenKey": self.encryptionEvenKey,
                "logLevel": self.logLevel,
                "srtVersion": self.srtVersion,
                "hostPort": self.hostPort,
                "address": self.address,
                "port": self.port,
                "outputOneTTL": self.outputOneTTL,
                "outputOneNetworkInterface": self.outputOneNetworkInterface,
                "outputOneAddress": self.outputOneAddress,
                "outputOnePort": self.outputOnePort,
                "outputTwoTTL": self.outputTwoTTL,
                "outputTwoNetworkInterface": self.outputTwoNetworkInterface,
                "outputTwoAddress": self.outputTwoAddress,
                "outputTwoPort": self.outputTwoPort,
                "preserveHeaders": self.preserveHeaders,
                "pathDelay": self.pathDelay,
                "passphrase": self.passphrase,
                "bindDevice": self.bindDevice
            }, type(self))

    def __init__(self, edge: 'Edge', Json: dict | str = "{}") -> 'Output': # Constructor. Take the edge object this output belongs to, and dict/str representation of data to construct from
        if isinstance(Json, str):
            data = json.loads(Json)
        else:
            data = Json
        self.edgeObject: Edge = edge # <Weaver.Edge>
        self.stream: str = data.get("stream") # <str> ID of the stream that this output is on
        self.options: Output.Options = self.Options(data.get("options", {})) # <Output.Options>
        self.muteOnError: bool = data.get("muteOnError") # <bool>
        self.muteOnErrorPeriod: int = data.get("muteOnErrorPeriod", 0) # <int>
        self.xor: bool = data.get("xor") # <bool>
        self.xorPaused: bool = data.get("xorPaused") # <bool>
        self.name: str = data.get("name") # <str>
        self.protocol = data.get("protocol")
        self.id: str = data.get("id") # <str>
        self.paused: bool = data.get("paused", False) # <bool>
        self.active: bool = data.get("active", False) # <bool>
        self.stopped: bool = data.get("stopped", False) # <bool>
        self.mwedge: str = data.get("mwedge") # <str> ID of the tx edge that this output is on
        self.tags: str = data.get("tags") # <str>

    def __str__(self):
        return json.dumps(self.to_json())
    
    def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
        return self.__str__()

    def to_json(self) -> dict: # Convert to cleaned json
        my_json = weaverValidation.ValidateConfiguration({
            "stream": self.stream,
            "options": self.options.to_json(),
            "muteOnErrorPeriod": self.muteOnErrorPeriod,
            "muteOnError": self.muteOnError,
            "xor": self.xor,
            "xorPaused": self.xorPaused,
            "name": self.name,
            "protocol": self.protocol,
            "id": self.id,
            "paused": self.paused,
            "active": self.active,
            "stopped": self.stopped,
            "mwedge": self.mwedge,
            "tags": self.tags
        }, type(self))
        return weaverValidation.ValidateConfiguration(weaverNet.cleanJson(my_json), type(self))
    
    def drop_dash_seven(self, selectedSide: int = 1, name: str = "") -> 'Output': # Convert one leg of a 2022-7 output to a standalone output object
        """
        Take a 2022-7 source, and reformat it as a single standalone source based.

        Args:
            selectedSide: The number of the source within the 2022-7 source to convert
            name: The name to give the source.

        Returns:
            Weaver.Output of the standalone source.
        """
        if self.protocol != "2022-7":
            raise weaverError.InternalError(extras=["Output.drop_dash_seven", f"id={self._d}", "Cannot run Output.drop_dash_seven on an output that isn't 2022-7!"])
        notDashSeven = Output(self.edgeObject)
        if name == "" and self.name:
            notDashSeven.name = self.name
        else:
            notDashSeven.name = name
        notDashSeven.protocol = "RTP"
        notDashSeven.options = Output.Options(self.options.to_json())

        notDashSeven.options.outputOneAddress = None
        notDashSeven.options.outputOneNetworkInterface = None
        notDashSeven.options.outputOnePort = None
        notDashSeven.options.outputOneTTL = None

        notDashSeven.options.outputTwoAddress = None
        notDashSeven.options.outputTwoNetworkInterface = None
        notDashSeven.options.outputTwoPort = None
        notDashSeven.options.outputTwoTTL = None

        notDashSeven.edgeObject = self.edgeObject

        if selectedSide == 1:
            notDashSeven.options.address = self.options.outputOneAddress
            notDashSeven.options.networkInterface = self.options.outputOneNetworkInterface
            notDashSeven.options.port = self.options.outputOnePort
            notDashSeven.options.ttl = self.options.outputOneTTL
        else:
            notDashSeven.options.address = self.options.outputTwoAddress
            notDashSeven.options.networkInterface = self.options.outputTwoNetworkInterface
            notDashSeven.options.port = self.options.outputTwoPort
            notDashSeven.options.ttl = self.options.outputTwoTTL

        return notDashSeven

    def Update(self, refreshCache: bool = True) -> bool: # Push local changes to the output to its tx edge via the tx core API. Returns True/False whether succeeded
        """
        Perform API call to update output with the locally made changes.

        Returns:
            The boolean outcome of the API call.
        """
        try:
            resp = weaverApi.UpdateOutput(self)    # Update yerself!
            if refreshCache:
                self.edgeObject.configCache = None # Clear the cache on the core because it has now changed
            return True
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return False

    def ClearStats(self) -> bool: # Clear stats on output
        """
        Clears stats on the output.

        Returns:
            The boolean outcome of the API call.
        """
        try:
            resp = weaverApi.ClearStats(self)
            return True
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return False

    @deprecated("This function is deprecated and will be removed in a future version. Use 'ClearStats' instead.")
    def ResetStats(self) -> bool:
        """
        Clears stats on the output.

        Returns:
            The boolean outcome of the API call.
        """
        self.ClearStats()

    def Delete(self) -> bool: # Delete this output
        """
        Perform API call to delete the output.

        Returns:
            The boolean outcome of the API call.
        """
        try:
            resp = weaverApi.DeleteOutput(self)
            return True
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return False

# Source Class
class Source:
    class Options:
        def __init__(self, options_data_input: str, edgeObject: 'Edge' = None, parentSource: 'Source' = None) -> 'Source.Options': # Constructor. Take dict/str representation of data to construct from, and the edge and source on which the source is based
            if isinstance(options_data_input, str):
                options_data = json.loads(options_data_input)
            else:
                options_data = options_data_input
            self.buffer: int = options_data.get("buffer") # <int> Buffer size in ms for RTP sources
            self.parentSource: Source = parentSource # <Weaver.Source> The Source object that a 2022-7 source belonged to (only relevant if it was broken out)
            self.sourceOne: Source.Options.DashSevenSource = self.DashSevenSource(options_data.get("sourceOne", {}), edgeObject, self.parentSource) # <Source.Options.DashSevenSource>
            self.sourceTwo: Source.Options.DashSevenSource = self.DashSevenSource(options_data.get("sourceTwo", {}), edgeObject, self.parentSource) # <Source.Options.DashSevenSource>
            self.sourceThree: Source.Options.DashSevenSource = self.DashSevenSource(options_data.get("sourceThree", {}), edgeObject, self.parentSource) # <Source.Options.DashSevenSource>
            self.decryptionType = options_data.get("decryptionType") # Scrambling decryption type (e.g. biss2)
            self.limitBitrate: bool = options_data.get("limitBitrate") # <bool> Whether to limit bitrate
            self.tcap: bool = options_data.get("tcap") # <bool> Whether to enable triggered captions
            self.decryptionOddKey: str = options_data.get("decryptionOddKey") # <str> Binary, Biss2 odd key
            self.decryptionEvenKey: str = options_data.get("decryptionEvenKey") # <str> Binary, Biss2 even key
            self.maxBitrateLimit: int = options_data.get("maxBitrateLimit") # <int> Maximum bitrate limit (if set)
            self.bitrateCappingEvent = options_data.get("bitrateCappingEvent") # How to limit bitrate (cap or disable)
            self.passphrase: str = options_data.get("passphrase") # <str> SRT passphrase
            self.hostPort: int = options_data.get("hostPort") # <int> Host port
            self.hostAddress: str = options_data.get("hostAddress") # <str> Host address in IP form for SRT. E.g., if ui: "eno1 [1.2.3.4]" then enter "1.2.3.4"
            self.bindDevice: str = options_data.get("bindDevice") # <str> SRT process bind device
            self.latency: int = options_data.get("latency") # <int> Latency in ms for SRT stream
            self.address: str = options_data.get("address") # <str> IP Address / DNS
            self.type: int | str = options_data.get("type") # <int | str> For SRT sources, this is 0 or 1 depending on Listener/Caller. For -7, it might be whether it's MPEGTS or NDI.
            self.encryption = options_data.get("encryption") # SRT Encrpytion (32 = AES256)
            self.srtVersion: str = options_data.get("srtVersion") # <str> SRT Version (1.4.4 or 1.5.1)
            self.chunkSize: int = options_data.get("chunkSize") # <int> Chunk size
            self.port: int = options_data.get("port") # <int> Port to use
            self.captureTriggers: Source.Options.CaptureTriggers = self.CaptureTriggers(options_data.get("captureTriggers", {})) # <Source.Options.CaptureTriggers> Object container capture trigger options
            self.enableCorrection: bool = options_data.get("enableCorrection") # <bool> Whether to enable correction on RTP sources
            self.filterSsrc = options_data.get("filterSsrc") # SSRC to filter
            self.networkInterface: str = options_data.get("networkInterface") # <str> Network interface IP. E.g., if ui: "eno1 [1.2.3.4]" then enter "1.2.3.4"
            self.useFEC: bool = options_data.get("useFEC") # <bool> Whether to use FEC
            self.fecColumnPort = options_data.get("fecColumnPort") # Port to use for FEC Columns
            self.fecRowPort = options_data.get("fecRowPort") # Port to use for FEC Rows
            self.preserveHeaders: bool = options_data.get("preserveHeaders") # <bool> Whether to preserve the RTP headers on a RTP-chunked source
            self.SSRCStickiness: str = options_data.get("SSRCStickiness") # How to handle SSRC changes
            self.command: str = options_data.get("command") # For test gen sources, which command to use, ffmpeg or gstreamer
            self.ffmpegPattern: str = options_data.get("ffmpegPattern") # For test gen sources, which pattern to use
            self.serviceName: str = options_data.get("serviceName") # For test gen sources, the service name to use
            self.resolution: str = options_data.get("resolution") # For test gen sources, the video resolution to use. (e.g. '1920x1080' or '320x180')
            self.videoBitrate: int = options_data.get("videoBitrate") # For test gen sources, bitrate to use in kbps
            self.framerate: int = options_data.get("framerate") # For test gen sources, video framerate
            self.addRTPHeaders: bool = options_data.get("addRTPHeaders") # For test gen sources, whether to add RTP headers.
            self.transmission: bool = options_data.get("transmission") # Select multicast or unicast mode. 0 = Unicast, 1 = Multicast

        def __str__(self):
            return json.dumps(self.to_json())
        
        def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
            return self.__str__()

        def to_json(self) -> dict: # Convert to uncleaned json
            return weaverValidation.ValidateConfiguration({
                "buffer": self.buffer,
                "decryptionType": self.decryptionType,
                "limitBitrate": self.limitBitrate,
                "tcap": self.tcap,
                "decryptionOddKey": self.decryptionOddKey,
                "decryptionEvenKey": self.decryptionEvenKey,
                "maxBitrateLimit": self.maxBitrateLimit,
                "bitrateCappingEvent": self.bitrateCappingEvent,
                "type": self.type,
                "hostAddress": self.hostAddress,
                "bindDevice": self.bindDevice,
                "hostPort": self.hostPort,
                "latency": self.latency,
                "passphrase": self.passphrase,
                "srtVersion": self.srtVersion,
                "encryption": self.encryption,
                "chunkSize": self.chunkSize,
                "address": self.address,
                "port": self.port,
                "sourceOne": self.sourceOne.to_json(),
                "sourceTwo": self.sourceTwo.to_json(),
                "sourceThree": self.sourceThree.to_json(),
                "captureTriggers": self.captureTriggers.to_json(),
                "enableCorrection": self.enableCorrection,
                "filterSsrc": self.filterSsrc,
                "networkInterface": self.networkInterface,
                "useFEC": self.useFEC,
                "fecColumnPort": self.fecColumnPort,
                "fecRowPort": self.fecRowPort,
                "preserveHeaders": self.preserveHeaders,
                "SSRCStickiness": self.SSRCStickiness,
                "command": self.command,
                "ffmpegPattern": self.ffmpegPattern,
                "serviceName": self.serviceName,
                "resolution": self.resolution,
                "videoBitrate": self.videoBitrate,
                "framerate": self.framerate,
                "addRTPHeaders": self.addRTPHeaders,

                "transmission": self.transmission
            }, type(self))

        class DashSevenSource:
            def __init__(self, source_data: dict, edgeObject: 'Edge' = None, parentSource: 'Source' = None) -> 'Source.Options.DashSevenSource': # Constructor. Take dict/str representation of data to construct from, and the edge and source on which the source is based
                try:
                    self.enabled: bool = source_data.get("enabled") # <bool>
                    self.protocol = source_data.get("protocol") # Protocol for the source
                    self.transmission = source_data.get("transmission") # 
                    self.sourceAddress: str = source_data.get("sourceAddress") # <str>
                    self.enableCorrection: bool = source_data.get("enableCorrection") # <bool>
                    self.buffer: int = source_data.get("buffer") # <int>
                    self.filterSsrc = source_data.get("filterSsrc")
                    self.networkInterface: str = source_data.get("networkInterface") # <str>
                    self.useFEC: bool = source_data.get("useFEC") # <bool>
                    self.decryptionType = source_data.get("decryptionType") # Scrambling type, e.g. biss2
                    self.limitBitrate: bool = source_data.get("limitBitrate") # <bool> Whether to cap bitrate
                    self.port: int = source_data.get("port") # <int>
                    self.address: str = source_data.get("address") # <str>
                    self.fecColumnPort = source_data.get("fecColumnPort") # Port to use for FEC Columns
                    self.fecRowPort = source_data.get("fecRowPort") # Port to use for FEC Rows
                    self.decryptionOddKey: str = source_data.get("decryptionOddKey") # <str> Binary, Biss2 odd key
                    self.decryptionEvenKey: str = source_data.get("decryptionEvenKey") # <str> Binary, Biss2 even key
                    self.maxBitrateLimit = source_data.get("maxBitrateLimit") # Action to take on bitrate limit (cap or pause)
                    self.bitrateCappingEvent = source_data.get("bitrateCappingEvent")
                    self.edgeObject: Edge = edgeObject # <Weaver.Edge>
                    self.parentSource: Source = parentSource # <Weaver.Source> Source object on which this DashSevenSource resides.
                    self.passphrase: str = source_data.get("passphrase") # <str> SRT Passphrase (if used)
                    self.encryption: int = source_data.get("encryption") # <int> STR encryption level. 32 = AES256, etc.
                    self.hostAddress: str = source_data.get("hostAddress") # use this to specify NIC in -7 SRT sources
                    self.bindDevice: str = source_data.get("bindDevice")
                except:
                    return None # Probably not enabled / configured

            def __str__(self):
                return json.dumps(self.to_json())
            
            def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
                return self.__str__()
   
            def to_json(self) -> dict: # Convert to uncleaned json
                if self:
                    return weaverValidation.ValidateConfiguration({
                        "enabled": self.enabled,
                        "protocol": self.protocol,
                        "transmission": self.transmission,
                        "sourceAddress": self.sourceAddress,
                        "enableCorrection": self.enableCorrection,
                        "buffer": self.buffer,
                        "filterSsrc": self.filterSsrc,
                        "networkInterface": self.networkInterface,
                        "useFEC": self.useFEC,
                        "decryptionType": self.decryptionType,
                        "limitBitrate": self.limitBitrate,
                        "port": self.port,
                        "address": self.address,
                        "fecColumnPort": self.fecColumnPort,
                        "fecRowPort": self.fecRowPort,
                        "decryptionOddKey": self.decryptionOddKey,
                        "decryptionEvenKey": self.decryptionEvenKey,
                        "maxBitrateLimit": self.maxBitrateLimit,
                        "bitrateCappingEvent": self.bitrateCappingEvent,
                        "passphrase": self.passphrase,
                        "encryption": self.encryption,
                        "hostAddress": self.hostAddress,
                        "bindDevice": self.bindDevice
                    }, type(self))
                else:
                    return None
                
            def as_source(self, edgeObject: 'Edge' = None, name: str = "") -> 'Source': # Extract this DashSevenSource leg from the 2022-7 it belongs to, adapting it into a standalone Source object. 
                """
                Refactor this 2022-7 sub-source as a standalone source.

                Args:
                    edgeObject: The edge to default the refactored source onto (if different from the original/parent)
                    name: The name to give the refactored source

                Returns:
                    Weaver.Source object of the refactored source.
                """
                if edgeObject == None:
                    edgeObject = self.edgeObject
                standalone = Source(edge=edgeObject)
                standalone.protocol = self.protocol

                if name == "" and self.parentSource:
                    standalone.name = self.parentSource.name
                else:
                    standalone.name = name
                standalone.options = Source.Options(self.to_json())

                if self.parentSource:
                    standalone.options.preserveHeaders = self.parentSource.options.preserveHeaders

                return standalone

        class CaptureTriggers:
            def __init__(self, capture_data: dict) -> 'Source.Options.CaptureTriggers': # Constructor. Take dict/str representation of data to construct from
                self.zeroBitrate: bool = capture_data.get("zeroBitrate") # <bool> Whether to trigger on zero bitrate
                self.TSSyncLoss: bool = capture_data.get("TSSyncLoss") # <bool> Whether to capture on TSSync loss
                self.lowBitrate: bool = capture_data.get("lowBitrate") # <bool> Whether to trigger on bitrate below threshold
                self.lowBitrateThreshold: int = capture_data.get("lowBitrateThreshold") # <int> Threshold to trigger lowBitrate at
                self.CCErrorsInPeriod: bool = capture_data.get("CCErrorsInPeriod") # <bool> Whether to trigger on CC Errors in Period
                self.CCErrorsInPeriodThreshold: int = capture_data.get("CCErrorsInPeriodThreshold") # <int> Threshold to trigger CCErrorsInPeriod at
                self.CCErrorsInPeriodTime: int = capture_data.get("CCErrorsInPeriodTime") # <int> Time period to monitor for CCErrorsInPeriod in ms
                self.missingPacketsInPeriod: bool = capture_data.get("missingPacketsInPeriod") # <bool> Whether to trigger on missing packets in period
                self.missingPacketsInPeriodThreshold: int = capture_data.get("missingPacketsInPeriodThreshold") # <int> Threshold of missing packets to trigger missingPacketsInPeriod at
                self.missingPacketsInPeriodTime: int = capture_data.get("missingPacketsInPeriodTime") # <int> Time period to monitor for missingPacketsInPeriod in ms

            def __str__(self):
                return json.dumps(self.to_json())
            
            def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
                return self.__str__()

            def to_json(self) -> dict: # Convert to uncleaned json
                if self:
                    return weaverValidation.ValidateConfiguration({
                        "zeroBitrate": self.zeroBitrate,
                        "TSSyncLoss": self.TSSyncLoss,
                        "lowBitrate": self.lowBitrate,
                        "lowBitrateThreshold": self.lowBitrateThreshold,
                        "CCErrorsInPeriod": self.CCErrorsInPeriod,
                        "CCErrorsInPeriodThreshold": self.CCErrorsInPeriodThreshold,
                        "CCErrorsInPeriodTime": self.CCErrorsInPeriodTime,
                        "missingPacketsInPeriod": self.missingPacketsInPeriod,
                        "missingPacketsInPeriodThreshold": self.missingPacketsInPeriodThreshold,
                        "missingPacketsInPeriodTime": self.missingPacketsInPeriodTime
                    }, type(self))
                else:
                    return None

    def __init__(self, edge: 'Edge', Json: dict | str = "{}") -> 'Source':
        if isinstance(Json, str):
            data = json.loads(Json)
        else:
            data = Json
        self._id: str = data.get("_id") # <str> Deprecated
        self.stream: str = data.get("stream") # <str> ID of the Stream that this source in on
        self.priority: int = data.get("priority") # <int> Source priority (for failover)
        self.options: Source.Options = self.Options(data.get("options", {}), edge, self) # <Source.Options> The source's options
        self.protocol: str = data.get("protocol") # <str> The source protocol
        self.monitorOnly: bool = data.get("monitorOnly") # <bool> Whether this source in an XOROMT-enabled stream should be used for monitoring only
        self.name: str = data.get("name") # <str> The name of the source
        self.id: str = data.get("id") # <str> The ID of the source
        self.tags: str = data.get("tags") # <str> Optional tags/labels for the source
        self.paused: bool = data.get("paused", False) # <bool> Whether the source is paused
        self.active: bool = data.get("active", False) # <bool> Whether the source is active
        self.etr290Enabled: bool = data.get("etr290Enabled", False) # <bool> Whether ETR290 monitoring is enabled
        self.stopped: bool = data.get("stopped", False) # <bool>
        self.exhausted: bool = data.get("exhausted", False) # <bool>
        self.mwedge: str = data.get("mwedge") # <str> ID of the tx edge that this source is on
        self.passive: bool = data.get("passive", False) # <bool> Is it a passive source
        self.edgeObject: Edge = edge # <Weaver.Edge> tx edge object 

    def __str__(self):
        return json.dumps(self.to_json())
    
    def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
        return self.__str__()

    def to_json(self) -> dict: # Convert to cleaned json
        my_json = weaverValidation.ValidateConfiguration({
            "_id": self._id, # I don't think this is necessary either
            "stream": self.stream,
            "priority": self.priority,
            "options": self.options.to_json(),
            "protocol": self.protocol,
            "monitorOnly": self.monitorOnly,
            "name": self.name,
            "id": self.id,
            "paused": self.paused,
            "active": self.active,
            "etr290Enabled": self.etr290Enabled,
            "stopped": self.stopped,
            "exhausted": self.exhausted,
            "passive": self.passive,
            "tags": self.tags
        }, type(self))
        return weaverValidation.ValidateConfiguration(weaverNet.cleanJson(my_json), type(self))

    def Update(self, refreshCache: bool = True) -> bool:
        """
        Perform API call to update source with the locally made changes.

        Returns:
            The boolean outcome of the API call.
        """
        try:
            resp = weaverApi.UpdateSource(self)    # Update yerself!
            return True
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return False

    def ClearStats(self) -> bool: # Clear stats on source
        """
        Resets stats on the source.

        Returns:
            The boolean outcome of the API call.
        """
        try:
            resp = weaverApi.ClearStats(self)
            return True
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return False
        
    @deprecated("This function is deprecated and will be removed in a future version. Use 'ClearStats' instead.")
    def ResetStats(self) -> bool: # Alias for ClearStats
        """
        Reset stats on the source.

        Returns:
            The boolean outcome of the API call.
        """
        self.ClearStats()

    def Delete(self) -> bool: # Delete this source
        try:
            resp = weaverApi.DeleteSource(self)
            return True
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return False

#Stream Class
class Stream:
    class Options:
        class FailoverTriggers:
            def __init__(self, options_data_input: dict | str) -> 'Stream.Options.FailoverTriggers': # Constructor. Take dict/str representation of data to construct from
                if isinstance(options_data_input, str):
                    options_data = json.loads(options_data_input)
                else:
                    options_data = options_data_input
                self.zeroBitrate: bool = options_data.get("zeroBitrate") # <bool> Whether to failover on zero bitrate
                self.TSSyncLoss: bool = options_data.get("TSSyncLoss") # <bool> Whether to failover on TS sync loss
                self.lowBitrate: bool = options_data.get("lowBitrate") # <bool> Whether to failover on low bitrate
                self.lowBitrateThreshold:int = options_data.get("lowBitrateThreshold") # <int> Threshold to trigger failover for low bitrate
                self.CCErrorsInPeriod: bool = options_data.get("CCErrorsInPeriod") # <bool> Whether to failover on CC Errors in Period
                self.CCErrorsInPeriodThreshold:int = options_data.get("CCErrorsInPeriodThreshold") # <int> Threshold to trigger failover for excessive CC errors
                self.CCErrorsInPeriodTime: int = options_data.get("CCErrorsInPeriodTime") # <int> Time period to monitor for CC Error failover
                self.missingPacketsInPeriod: bool = options_data.get("missingPacketsInPeriod") # <bool> Whether to failover on missing packets in period
                self.missingPacketsInPeriodThreshold: int = options_data.get("missingPacketsInPeriodThreshold") # <int> Threshold to trigger failover for missing packets
                self.missingPacketsInPeriodTime: int = options_data.get("missingPacketsInPeriodTime") # <int> Time period to monitor for missing packets failover
                self.nullBitratePercentageThreshold: int = options_data.get("nullBitratePercentageThreshold") # <int> Percentage NULLs in TS to trigger failover

            def __str__(self):
                return json.dumps(self.to_json())
            
            def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
                return self.__str__()
            
            def to_json(self) -> dict: # Convert to cleaned json
                my_json = weaverValidation.ValidateConfiguration({
                    "zeroBitrate": self.zeroBitrate,
                    "TSSyncLoss": self.TSSyncLoss,
                    "lowBitrate": self.lowBitrate,
                    "lowBitrateThreshold": self.lowBitrateThreshold,
                    "CCErrorsInPeriod": self.CCErrorsInPeriod,
                    "CCErrorsInPeriodThreshold": self.CCErrorsInPeriodThreshold,
                    "CCErrorsInPeriodTime": self.CCErrorsInPeriodTime,
                    "missingPacketsInPeriod": self.missingPacketsInPeriod,
                    "missingPacketsInPeriodThreshold": self.missingPacketsInPeriodThreshold,
                    "missingPacketsInPeriodTime": self.missingPacketsInPeriodTime,
                    "nullBitratePercentageThreshold": self.nullBitratePercentageThreshold
                }, type(self))
                return weaverValidation.ValidateConfiguration(weaverNet.cleanJson(my_json), type(self))

        class OutputMuteTriggers:
            def __init__(self, options_data_input: dict | str) -> 'Stream.Options.OutputMuteTriggers': # Constructor. Take dict/str representation of data to construct from
                if isinstance(options_data_input, str):
                    options_data = json.loads(options_data_input)
                else:
                    options_data = options_data_input
                self.zeroBitrate: bool = options_data.get("zeroBitrate") # <bool> Whether to mute on zero bitrate
                self.TSSyncLoss: bool = options_data.get("TSSyncLoss") # <bool> Whether to mute on TS sync loss
                self.lowBitrate: bool = options_data.get("lowBitrate") # <bool> Whether to mute on low bitrate
                self.lowBitrateThreshold: int = options_data.get("lowBitrateThreshold") # <int> Threshold to trigger mute for low bitrate
                self.CCErrorsInPeriod: bool = options_data.get("CCErrorsInPeriod") # <bool> Whether to mute on CC Errors in Period
                self.CCErrorsInPeriodThreshold:int = options_data.get("CCErrorsInPeriodThreshold") # <int> Threshold to trigger mute for excessive CC errors
                self.CCErrorsInPeriodTime:int = options_data.get("CCErrorsInPeriodTime") # <int> Time period to monitor for CC Error mute
                self.missingPacketsInPeriod: bool = options_data.get("missingPacketsInPeriod") # <bool> Whether to mute on missing packets in period
                self.missingPacketsInPeriodThreshold:int = options_data.get("missingPacketsInPeriodThreshold") # <int> Threshold to trigger mute for missing packets
                self.missingPacketsInPeriodTime:int = options_data.get("missingPacketsInPeriodTime") # <int> Time period to monitor for missing packets mute
                self.nullBitratePercentageThreshold:int = options_data.get("nullBitratePercentageThreshold") # <int> Percentage NULLs in TS to trigger mute

            def __str__(self):
                return json.dumps(self.to_json())
            
            def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
                return self.__str__()

            def to_json(self) -> dict: # Convert to cleaned json
                my_json = weaverValidation.ValidateConfiguration({
                    "zeroBitrate": self.zeroBitrate,
                    "TSSyncLoss": self.TSSyncLoss,
                    "lowBitrate": self.lowBitrate,
                    "lowBitrateThreshold": self.lowBitrateThreshold,
                    "CCErrorsInPeriod": self.CCErrorsInPeriod,
                    "CCErrorsInPeriodThreshold": self.CCErrorsInPeriodThreshold,
                    "CCErrorsInPeriodTime": self.CCErrorsInPeriodTime,
                    "missingPacketsInPeriod": self.missingPacketsInPeriod,
                    "missingPacketsInPeriodThreshold": self.missingPacketsInPeriodThreshold,
                    "missingPacketsInPeriodTime": self.missingPacketsInPeriodTime,
                    "nullBitratePercentageThreshold": self.nullBitratePercentageThreshold
                }, type(self))
                return weaverValidation.ValidateConfiguration(weaverNet.cleanJson(my_json), type(self))

        def __init__(self, options_data_input: dict | str) -> 'Stream.Options': # Constructor. Take dict/str representation of data to construct from
            if isinstance(options_data_input, str):
                options_data = json.loads(options_data_input)
            else:
                options_data = options_data_input
            self.failoverTriggers: Stream.Options.FailoverTriggers = Stream.Options.FailoverTriggers(options_data.get("failoverTriggers", {})) # <Stream.Options.FailoverTriggers>
            self.outputMuteTriggers: Stream.Options.OutputMuteTriggers = Stream.Options.OutputMuteTriggers(options_data.get("outputMuteTriggers", {})) # <Stream.Options.OutputMuteTriggers>
            self.failoverMode = options_data.get("failoverMode") # Failover mode (reverting, floating etc.)
            self.failoverRevertTime: int = options_data.get("failoverRevertTime") # <int> Period of time main source should be good before failback in ms
            self.failoverWaitTime: int = options_data.get("failoverWaitTime") # <int> Period of time main source should be bad before failover in ms
            self.showXOROMT: bool = options_data.get("showXOROMT") # <bool> Whether to use XOROMT options.
    
        def __str__(self):
            return json.dumps(self.to_json())
        
        def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
            return self.__str__()

        def to_json(self) -> dict: # Convert to cleaned json
            my_json = weaverValidation.ValidateConfiguration({
                "failoverTriggers": self.failoverTriggers.to_json(),
                "outputMuteTriggers": self.outputMuteTriggers.to_json(),
                "failoverMode": self.failoverMode,
                "failoverRevertTime": self.failoverRevertTime,
                "failoverWaitTime": self.failoverWaitTime,
                "showXOROMT": self.showXOROMT
            }, type(self))
            return weaverValidation.ValidateConfiguration(weaverNet.cleanJson(my_json), type(self))

    def __init__(self, edgeObject, Json: dict | str = "{}") -> 'Stream': # Constructor. Take object of the edge the stream is on, and dict/str representation of data to construct from
        if isinstance(Json, str):
            data = json.loads(Json)
        else:
            data = Json
        self.options: Stream.Options = Stream.Options(data.get("options", {})) # <Stream.Options>
        self.name: str = data.get("name") # <str> Stream name
        self.id: str = data.get("id") # <str> Stream ID
        self.enableThumbnails: bool = data.get("enableThumbnails") # <bool> Whether to enable thumbnailing on the stream
        self.mwedge: str = data.get("mwedge") # <str> ID of the tx edge that this stream is on
        self.edgeObject: Edge = edgeObject # <Weaver.Edge>
        self.state = data.get("state")

        self.options: Stream.Options = Stream.Options(data.get("options", {})) # <Stream.Options.OutputMuteTriggers>
        self.name = data.get("name")
        self.id = data.get("id")
        self.enableThumbnails = data.get("enableThumbnails", False)
        self.mwedge = data.get("mwedge")

    def __str__(self):
        return json.dumps(self.to_json())
    
    def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
        return self.__str__()

    def to_json(self) -> dict: # Convert to cleaned json
        my_json = weaverValidation.ValidateConfiguration({
            "state": self.state,
            "options": self.options.to_json(),
            "name": self.name,
            "id": self.id,
            "enableThumbnails": self.enableThumbnails,
            "mwedge": self.mwedge
        }, type(self))
        return weaverValidation.ValidateConfiguration(weaverNet.cleanJson(my_json), type(self))

    ##Custom, not API-Native ways
    def GetSources(self) -> List[Source]:
        """
        Fetch array of Weaver.Source objects representing all sources on this stream.

        Returns:
            Array of Weaver.Source objects on this stream.
        """
        try:
            plainText = self.edgeObject.configCache
            if plainText == None:
                resp = weaverApi.GetEdgeById(self.edgeObject.coreObject, self.edgeObject._id) # "plainText" is now a string of json...
                plainText = resp.text
            Json = json.loads(plainText)                        # Convert the string to JSON
            sources = []                                        # Create an array for the sources
            for configuredSource in Json['configuredSources']:  # For every key in 'configuredSources'
                newSource = Source(self.edgeObject, configuredSource)      # Create source from JSON
                if newSource.stream == self.id:
                    newSource.edgeObject = self.edgeObject
                    sources.append(newSource)                   # Append to array
            return sources                                      # Return array
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return []
        
    def GetSourcesByName(self, __name: str) -> List[Source]: # Get list of outputs on the stream by name
        """
        Fetch array of Weaver.Source objects representing all sources on this stream, whose name matches the given search term

        Args:
            __name: The name to search for

        Returns:
            Array of Weaver.Source objects matching the search on this stream.
        """
        try:
            plainText = self.edgeObject.configCache
            if plainText == None:
                resp = weaverApi.GetEdgeById(self.edgeObject.coreObject, self.edgeObject._id) # "plainText" is now a string of json...
                plainText = resp.text
            Json = json.loads(plainText)                        # Convert the string to JSON
            sources = []                                        # Create an array for the sources
            for configuredSource in Json['configuredSources']:  # For every key in 'configuredSources'
                newSource = Source(self.edgeObject, configuredSource)                            # Create a new output
                if newSource.stream == self.id:
                    newSource.edgeObject = self.edgeObject
                    if newSource.name == __name:
                        sources.append(newSource)               # Append to array
            return sources                                      # Return array
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return []

        ##Custom, not API-Native ways

    def GetOutputs(self) -> List[Output]:
        """
        Fetch array of Weaver.Output objects representing all outputs on this stream.

        Returns:
            Array of Weaver.Output objects matching the search on this stream.
        """
        try:
            plainText = self.edgeObject.configCache
            if plainText == None:
                resp = weaverApi.GetEdgeById(self.edgeObject.coreObject, self.edgeObject._id) # "plainText" is now a string of json...
                plainText = resp.text
            Json = json.loads(plainText)                        # Convert the string to JSON
            outputs = []                                        # Create an array for the sources
            for configuredOutput in Json['configuredOutputs']:  # For every key in 'configuredSources'
                newOutput = Output(self.edgeObject, configuredOutput)                            # Create a new output
                if newOutput.stream == self.id:
                    newOutput.edgeObject = self.edgeObject
                    outputs.append(newOutput)                       # Append to array
            return outputs                                      # Return array
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return []
        
    def GetOutputsByName(self, __name: str) -> List[Output]: # Get list of outputs on the stream by name
        """
        Fetch array of Weaver.Output objects representing all outputs on this stream, whose name match the given search term.

        Args:
            __name: The name to search for.

        Returns:
            Array of Weaver.Output objects matching the search term on this stream.
        """
        try:
            plainText = self.edgeObject.configCache
            if plainText == None:
                resp = weaverApi.GetEdgeById(self.edgeObject.coreObject, self.edgeObject._id) # "plainText" is now a string of json...
                plainText = resp.text
            Json = json.loads(plainText)                        # Convert the string to JSON
            outputs = []                                        # Create an array for the sources
            for configuredOutput in Json['configuredOutputs']:  # For every key in 'configuredSources'
                newOutput = Output(self.edgeObject, configuredOutput)                            # Create a new output
                if newOutput.stream == self.id:
                    newOutput.edgeObject = self.edgeObject
                    if newOutput.name == __name:
                        outputs.append(newOutput)               # Append to array
            return outputs                                      # Return array
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return []

    def Create(self, origin_objects: Source | Output | List[Source | Output], newgen_generate_other_ids = True) -> Source | Output | List[Source | Output]:
        """
        Takes a source or output object, or an array of any combination of source and output objects, and creates them on the given stream.

        Note: If an array is provided, this uses the multi-create API endpoint (api/mwedge/:_id) if tx edge version is 1.46.0 or later, and tx core version is 5.41.0 or later, otherwise falls back to creating them one by one via the relevant CreateSource or CreateOutput APIs.

        Args:
            origin_object: A source or output object, or a list of any combination of stream source or output objects to create

        Returns:
            The created object(s). If only one object is created, returns that object. If multiple objects are created, returns the list of objects.
        """
        if len(origin_objects) == 1 and newgen_generate_other_ids: # If it's a one-item-long list and we don't care about the ID...
            origin_objects = origin_objects[0]          # Rather than use the list, convert it to just the one item. (So the next logic works)
        if type(origin_objects) == Source:
            return self.CreateSource(origin_objects)
        elif type(origin_objects) == Output:
            return self.CreateOutput(origin_objects)
        else:                                           # We have more than one item, time to see how we handle it...
            if compareVersions(self.edgeObject.version, "1.46.0", return_if_tie=True) and compareVersions(self.edgeObject.coreObject.version, "5.41.0", return_if_tie=True):    # We'll use the create-multiple capabilities... not yet implemented tho.
                sources = []
                outputs = []
                for origin_object in origin_objects:
                    object = copy.deepcopy(origin_object)
                    object.stream = self.id
                    object.mwedge = self.edgeObject._id
                    object.edgeObject = self
                    if type(object) == Source:
                        sources.append(object)
                    elif type(object) == Output:
                        outputs.append(object)
                    object.id = None
                return weaverApi.CreateMultiple(self.edgeObject.coreObject, self.edgeObject, [], sources, outputs)
            else:
                output_objects = []
                for origin_object in origin_objects:
                    if type(origin_object) == Source:
                        output_objects.append(self.CreateSource(origin_objects))
                    elif type(origin_object) == Output:
                        output_objects.append(self.CreateOutput(origin_objects))
                return output_objects
        return None

    def CreateSource(self, s_origin: Source) -> Source:
        """
        Take the given source object, and create it on this stream.
        Automatically sets the 'stream' and 'mwedge' fields on the given source object such that they line up with the stream on which they are to be created.

        Args:
            s_origin: The source to create.

        Returns:
            The Weaver.Source returned from the API response.
        """
        try:
            s = copy.deepcopy(s_origin)
            s.mwedge = self.edgeObject._id                      # Set the source's "mwedge" entry to the ID of this edge, as this is where we are creating the source!
            s.edgeObject = self.edgeObject
            s.stream = self.id
            s.id = 0                                            # Wipe the ID attached to the passed source object, as it will be overwritten when creating the source
            resp = weaverApi.CreateSource(s)       # Create source, and save the API response to 'plainTextResponse'
            plainTextResponse = resp.text
            Json = json.loads(plainTextResponse)
            s = Source(self.edgeObject, Json)                              # Rebuild 's' from the JSON handed back by the API (setting s._id to the ID of the newly created stream in the process)
            if self.edgeObject.cachingEnabled:
                self.edgeObject.configCache = None              # Clear the cache on the core because it has now changed
            return s                                            # Pass the new source object back to the caller.
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return None

    def CreateOutput(self, o_origin: Output) -> Output:
        """
        Take the given output object, and create it on this stream.
        Automatically sets the 'stream' and 'mwedge' fields on the given output object such that they line up with the stream on which they are to be created.

        Args:
            o_origin: The output to create.

        Returns:
            The Weaver.Output returned from the API response.
        """
        try:
            o = copy.deepcopy(o_origin)
            o.mwedge = self.edgeObject._id                      # Set the output's "mwedge" entry to the ID of this edge, as this is where we are creating the output!
            o.edgeObject = self.edgeObject
            o.stream = self.id
            o.id = 0                                            # Wipe the ID attached to the passed output object, as it will be overwritten when creating the output
            resp = weaverApi.CreateOutput(o)       # Create output, and save the API response to 'plainTextResponse'
            plainTextResponse = resp.text
            Json = json.loads(plainTextResponse)
            o = Output(self.edgeObject, Json)                              # Rebuild 'o' from the JSON handed back by the API (setting o._id to the ID of the newly created stream in the process)
            if self.edgeObject.cachingEnabled:
                self.edgeObject.configCache = None              # Clear the cache on the core because it has now changed
            return o                                            # Pass the new output object back to the caller.
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return None

    def Update(self, refreshCache: bool = True) -> bool: # Push local changes to the output to its tx edge via the tx core API. Returns True/False whether succeeded
        """
        Perform API call to update stream with locally made changes.

        Returns:
            The outcome of the API call.
        """
        try:
            weaverApi.UpdateStream(self)    # Update yerself!
            if refreshCache:
                self.edgeObject.configCache = None # Clear the cache on the core because it has now changed
            return True
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return False

    def ClearStats(self) -> bool: # Clear stats on all sources and outputs on the stream
        """
        Clear stats of all sources and outputs on this stream.

        Returns:
            The outcome of the API call.
        """
        try:
            resp = weaverApi.ClearStats(self)
            return True
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return False
        
    @deprecated("This function is deprecated and will be removed in a future version. Use 'ClearStats' instead.")
    def ResetStats(self) -> bool: # Alias for ClearStats
        """
        Clear stats of all sources and outputs on this stream.

        Returns:
            The outcome of the API call.
        """
        self.ClearStats()

    def Delete(self) -> bool: # Delete this stream
        """
        Perform the API call to delete the stream.

        Returns:
            The outcome of the API call
        """
        try:
            resp = weaverApi.DeleteStream(self)
            return True
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return False

#Edge Class
class Edge:
    class UpgradeStatus:
        def __init__(self, Json: dict | str = "{}") -> 'Edge.UpgradeStatus': # Constructor. Take dict/str representation of data to construct from
            if isinstance(Json, str):
                data = json.loads(Json)
            else:
                data = Json
            try:
                self.time: str = data.get("time") # <str> Upgrade Status most recent update time
                self._type = data.get("_type")
                self.message: str = data.get("message") # <str> Current upgrade status
            except:
                throwaway = 0

        def to_json(self) -> dict: # Convert to cleaned json
            my_json = weaverValidation.ValidateConfiguration({
                "time": self.time,
                "_type": self._type,
                "message": self.message
            }, type(self))
            return weaverValidation.ValidateConfiguration(weaverNet.cleanJson(my_json), type(self))

    class CloudLicense:
        class CloudLicensePool:
            def __init__(self, Json: dict | str = "{}") -> 'Edge.CloudLicense.CloudLicensePool': # Constructor. Take dict/str representation of data to construct from
                if isinstance(Json, str):
                    data = json.loads(Json)
                else:
                    data = Json
                try:
                    self.id: str = data.get("id") # <str> Cloud license pool ID
                    self.units: int = data.get("units") # <int> Number of assigned units
                except:
                    throwaway = 0

            def to_json(self) -> dict: # Convert to cleaned json
                my_json = weaverValidation.ValidateConfiguration({
                    "id": self.id,
                    "units": self.units
                }, type(self))
                return weaverNet.cleanJson(my_json)
            
            def __str__(self):
                return json.dumps(self.to_json())
            
            def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
                return self.__str__()

        def __init__(self, Json: dict | str = "{}") -> 'Edge.CloudLicense': # Constructor. Take dict/str representation of data to construct from
            if isinstance(Json, str):
                data = json.loads(Json)
            else:
                data = Json
            try:
                self.enabled: bool = data.get("enabled") # <bool>
                if data.get("pools"):
                    self.pools: List[Edge.CloudLicense.CloudLicensePool] = [Edge.CloudLicense.CloudLicensePool(cloudLicensePool_data) for cloudLicensePool_data in data.get("pools")] # <Edge.cloudLicense.cloudLicensePool[]> Array of all license pools on this edge
                else:
                    self.pools = []
            except:
                throwaway = 0
        
        def to_json(self) -> dict: # Convert to uncleaned json
            my_json = weaverValidation.ValidateConfiguration({
                "enabled": self.enabled,
                "pools": [pool.to_json() for pool in self.pools]
            }, type(self))
            return weaverNet.cleanJson(my_json)
        
        def __str__(self):
            return json.dumps(self.to_json())
        
        def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
            return self.__str__()
  
    def __init__(self, coreObject: 'Core', Json: dict | str = "{}", cachingEnabled: bool = False) -> 'Edge': # Constructor. Take tx core object, json data (either as dict or str).
        if isinstance(Json, str):
            data = json.loads(Json)
        else:
            data = Json
        self.clientId: str = data.get("clientId") # <str> Edge clientId
        self._id: str = data.get("_id") # <str> Edge ID
        self.externalIpAddress = data.get("externalIpAddress") # <str> External IP address
        self.httpServerPort: int = data.get("httpServerPort") # <int>
        self.ipAddresses = data.get("ipAddresses") # IP Addresses in array
        self.mwcore: str = data.get("mwcore") # <str> tx core URL. On some versions may be `txcore`
        self.txcore: str = data.get("txcore") # <str> tx core URL. On some versions may be `mwcore`
        self.name: str = data.get("name") # <str> tx edge name
        self.online: bool = data.get("online") # <bool> Whether the edge is online
        self.topTalkersEnabled: bool = data.get("topTalkersEnabled") # <bool> Whether Top Talkers is enabled
        self.updatedAt: str = data.get("updatedAt") # <str> Timestamp of last update
        self.version: str = data.get("version") # <str> tx edge version
        self.createdAt: str = data.get("createdAt") # <str> Timestamp of creation / first connection to the tx core.
        self.upgradeStatus: Edge.UpgradeStatus = Edge.UpgradeStatus(data.get("upgradeStatus", {})) # <Edge.UpgradeStatus>
        self.cloudLicense: Edge.CloudLicense = Edge.CloudLicense(data.get("cloudLicense", {})) # <Edge.CloudLicense>
        self.coreObject: Core = coreObject # <Core> Core object that this edge is on
        self.cachingEnabled: bool = cachingEnabled
        self.configCache: str | None = None
        if self.cachingEnabled:
            self.configCache = json.dumps(data)
        if self.txcore:
            self.__initial_core: str = self.txcore # <str> URL to remember current tx core address. This is used to identify whether the address is changed, and - if not - not include it in update API calls to prevent unnecessary tx edge disconnect/reconnects
        else:
            self.__initial_core: str = self.mwcore # <str> URL to remember current tx core address. This is used to identify whether the address is changed, and - if not - not include it in update API calls to prevent unnecessary tx edge disconnect/reconnects

    def __str__(self):
        return json.dumps(self.to_json())
    
    def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
        return self.__str__()

    def to_json(self) -> dict: # Convert to cleaned json
        core_value = None
        if self.txcore and self.__initial_core != self.txcore:
            core_value = self.txcore
        elif self.mwcore and self.__initial_core != self.mwcore:
            core_value = self.mwcore
        my_json = weaverValidation.ValidateConfiguration({
            "clientId": self.clientId,
            "_id": self._id,
            "externalIpAddress": self.externalIpAddress,
            "httpServerPort": self.httpServerPort,
            "ipAddresses": self.ipAddresses,
            "mwcore": core_value,
            "txcore": core_value,
            "name": self.name,
            "online": self.online,
            "topTalkersEnabled": self.topTalkersEnabled,
            "updatedAt": self.updatedAt,
            "upgradeStatus": {
                "time": self.upgradeStatus.time,
                "_type": self.upgradeStatus._type,
                "message": self.upgradeStatus.message
            },
            "version": self.version,
            "createdAt": self.createdAt,
            "cloudLicense": self.cloudLicense.to_json()
        }, type(self))
        return weaverValidation.ValidateConfiguration(weaverNet.cleanJson(my_json), type(self))
    
    def GetOutputs(self) -> List[Output]:
        """
        Fetch array of Weaver.Output objects representing all outputs on this edge.

        Returns:
            Array of Weaver.Output objects on this edge.
        """
        try:
            plainText = self.configCache
            if plainText == None:
                plainText = weaverApi.GetEdgeById(self.coreObject, self._id).text # "plainText" is now a string of json...
                if self.cachingEnabled == True:
                    self.configCache = plainText

            if not "configuredOutputs" in plainText:
                return []
            Json = json.loads(plainText)                        # Convert the string to JSON
            outputs = []                                        # Create an array for the outputs
            for configuredOutput in Json['configuredOutputs']:  # For every key in 'configuredOutputs'
                newOutput = Output(self, configuredOutput)      # Create a new output
                outputs.append(newOutput)                       # Append to array
            return outputs                                      # Return array
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return []

    def GetOutputsByName(self, __name: str) -> List[Output]: # Get list of outputs on the stream by name
        """
        Fetch array of Weaver.Output objects representing all outputs on this edge, whose name match the given search term.

        Args:
            __name: The name to search for.

        Returns:
            Array of Weaver.Output objects matching the search term on this edge.
        """
        try:
            plainText = self.configCache
            if plainText == None:
                resp = weaverApi.GetEdgeById(self.coreObject, self._id) # "plainText" is now a string of json...
                plainText = resp.text
            Json = json.loads(plainText)                        # Convert the string to JSON
            outputs = []                                        # Create an array for the sources
            for configuredOutput in Json['configuredOutputs']:  # For every key in 'configuredSources'
                newOutput = Output(self, configuredOutput)                            # Create a new output
                if newOutput.name == __name:
                    outputs.append(newOutput)               # Append to array
            return outputs                                  # Return array
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return []

    def GetSources(self) -> List[Source]: # Return all sources on this tx edge
        """
        Fetch array of Weaver.Source objects representing all sources on this edge.

        Returns:
            Array of Weaver.Source objects on this edge.
        """
        try:
            plainText = self.configCache
            if plainText == None:
                plainText = weaverApi.GetEdgeById(self.coreObject, self._id).text # "plainText" is now a string of json...
                if self.cachingEnabled == True:
                    self.configCache = plainText

            if not "configuredSources" in plainText:
                return []
            Json = json.loads(plainText)                        # Convert the string to JSON
            sources = []                                        # Create an array for the sources
            for configuredSource in Json['configuredSources']:  # For every key in 'configuredSources'
                newSource = Source(self, configuredSource)      # Create a new source
                sources.append(newSource)                       # Append to array
            return sources                                      # Return array
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return []
        
    def GetSourcesByName(self, __name: str) -> List[Source]: # Get list of outputs on the stream by name
        """
        Fetch array of Weaver.Source objects representing all sources on this edge, whose name match the given search term.

        Args:
            __name: The name to search for.

        Returns:
            Array of Weaver.Source objects matching the search term on this edge.
        """
        try:
            plainText = self.configCache
            if plainText == None:
                resp = weaverApi.GetEdgeById(self.coreObject, self._id) # "plainText" is now a string of json...
                plainText = resp.text
            Json = json.loads(plainText)                        # Convert the string to JSON
            sources = []                                        # Create an array for the sources
            for configuredSource in Json['configuredSources']:  # For every key in 'configuredSources'
                newSource = Source(self, configuredSource)                            # Create a new output
                if newSource.name == __name:
                    sources.append(newSource)               # Append to array
            return sources                                      # Return array
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return []

    def GetStreams(self) -> List[Stream]: # Return all streams on this tx edge
        """
        Fetch array of Weaver.Stream objects representing all streans on this edge.

        Returns:
            Array of Weaver.Stream objects on this edge.
        """
        try:
            plainText = self.configCache
            if plainText == None:
                plainText = weaverApi.GetEdgeById(self.coreObject, self._id).text # "plainText" is now a string of json...
                if self.cachingEnabled == True:
                    self.configCache = plainText
            if not "configuredStreams" in plainText:
                return []
            Json = json.loads(plainText)                        # Convert the string to JSON
            streams = []                                        # Create an array for the sources
            for configuredStream in Json['configuredStreams']:  # For every key in 'configuredSources'
                newStream = Stream(self, configuredStream)      # Create a new source
                streams.append(newStream)                       # Append to array
            return streams                                      # Return array
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return []

    def GetStreamById(self, _id: str) -> Stream:
        """
        Fetch a stream by its ID

        Args:
            _id: The ID of the stream to fetch.

        Returns:
            Weaver.Stream with the matching ID.
        """
        try:
            plainText = self.configCache
            if plainText == None:
                plainText = weaverApi.GetEdgeById(self.coreObject, self._id).text # "plainText" is now a string of json...
                if self.cachingEnabled == True:
                    self.configCache = plainText
            
            if not "configuredStreams" in plainText:
                return None
            Json = json.loads(plainText)                        # Convert the string to JSON
            for configuredStream in Json['configuredStreams']:  # For every key in 'configuredSources'
                newStream = Stream(self, configuredStream)      # Create a new source
                if newStream.id == _id:
                    return newStream                            # Append to array
            return None                                         # Return array
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return None

    def GetStreamsByName(self, _name: str) -> List[Stream]: 
        """
        Fetch array of Weaver.Stream objects representing all streams on this edge, whose name match the given search term.

        Args:
            __name: The name to search for.

        Returns:
            Array of Weaver.Stream objects matching the search term on this edge.
        """
        try:
            plainText = self.configCache
            if plainText == None:
                plainText = weaverApi.GetEdgeById(self.coreObject, self._id).text # "plainText" is now a string of json...
                if self.cachingEnabled == True:
                    self.configCache = plainText
            
            if not "configuredStreams" in plainText:
                return None
            Json = json.loads(plainText)                        # Convert the string to JSON
            streams = []
            for configuredStream in Json['configuredStreams']:  # For every key in 'configuredSources'
                newStream = Stream(self, configuredStream)      # Create a new source
                if newStream.name == _name:
                    streams.append(newStream)                   # Append to array
            return streams                                      # Return array
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return None
    
    def CreateStream(self, st_origin: Stream) -> Stream: # Create a stream
        """
        Take the given stream object, and create it on this edge.
        Automatically sets the 'mwedge' fields on the given stream object such that they line up with the tx edge on which they are to be created.

        Args:
            st_origin: The stream to create.

        Returns:
            The Weaver.Stream returned from the API response.
        """
        try:
            st = copy.deepcopy(st_origin)
            st.mwedge = self._id                                # Set the stream's "mwedge" entry to the ID of this edge, as this is where we are creating the stream!
            st.edgeObject = self
            st.id = "0"                                         # Wipe the ID attached to the passed stream object, as it will be overwritten when creating the stream
            plainTextResponse = weaverApi.CreateStream(st).text # Create stream, and save the API response to 'plainTextResponse'
            Json = json.loads(plainTextResponse)
            st = Stream(self, Json)                             # Rebuild 's' from the JSON handed back by the API (setting s._id to the ID of the newly created stream in the process)
            if self.cachingEnabled:
                self.configCache = None                         # Clear the cache on the core because it has now changed
            return st                                           # Pass the new stream object back to the caller.7
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return None

    def Create(self, origin_objects: Stream | Source | Output | List[Stream | Source | Output], newgen_generate_stream_ids = True, newgen_generate_other_ids = True) -> Stream | Source | Output | List[Stream | Source | Output]:
        """
        Takes a stream, source or output object, or an array of any combination of stream source and output objects, and creates them on the given edge.

        Note: If an array is provided, this uses the multi-create API endpoint (api/mwedge/:_id) if tx edge version is 1.46.0 or later, and tx core version is 5.41.0 or later, otherwise falls back to creating them one by one via the relevant CreateSource, CreateStream or CreateOutput APIs.

        Args:
            origin_object: A stream, source or output object, or a list of any combination of stream source or output objects to create
            newgen_generate_stream_ids: (Only applies to multi-create API calls). Defaults to TRUE. Whether to have tx core generate random IDs for the streams. If you wish to pre-link sources and outputs to streams, you will need to give them UNIQUE IDs to the streams, and you MUST set newgen_generate_stream_ids to FALSE. You can use the generateId() function to help with this.
            newgen_generate_other_ids: (Only applies to multi-create API calls). Defaults to TRUE. Whether to have tx core generate random IDs for the sources and outputs. Useful only if you want to predefine the IDs for particular sources and objects. Be careful, as IDs must be unique across a whole edge (not just across a stream). You can use the generateId() function to help with this.

        Returns:
            The created object(s). If only one object is created, returns that object. If multiple objects are created, returns the list of objects.
        """
        if len(origin_objects) == 1 and newgen_generate_stream_ids: # If it's a one-item-long list, and we don't care about its id...
            origin_objects = origin_objects[0]          # Rather than use the list, convert it to just the one item. (So the next logic works)
        if type(origin_objects) == Stream:              # If it's just a stream, source or output, handle it normally, otherwise...
            return self.CreateStream(origin_objects)
        elif type(origin_objects) == Source:
            return self.CreateSource(origin_objects)
        elif type(origin_objects) == Output:
            return self.CreateOutput(origin_objects)
        else:                                           # We have more than one item, time to see how we handle it...
            if compareVersions(self.version, "1.46.0", return_if_tie=True) and compareVersions(self.coreObject.version, "5.41.0", return_if_tie=True):    # We'll use the create-multiple capabilities... not yet implemented tho.
                streams = []
                sources = []
                outputs = []
                for origin_object in origin_objects:
                    object = copy.deepcopy(origin_object)
                    object.mwedge = self._id
                    object.edgeObject = self
                    if not type(object) == Stream or newgen_generate_stream_ids == True: # If this is a source/output, or it's a stream but we've been set to regen IDs, clear the ID
                        object.id = None
                    if type(object) == Stream:
                        streams.append(object)
                    elif type(object) == Source:
                        sources.append(object)
                    elif type(object) == Output:
                        outputs.append(object)
                return weaverApi.CreateMultiple(self.coreObject, self, streams, sources, outputs)
            else:
                output_objects = []
                for origin_object in origin_objects:
                    if type(origin_object) == Stream:              # If it's just a stream, source or output, handle it normally, otherwise...
                        output_objects.append(self.CreateStream(origin_object))
                    elif type(origin_object) == Source:
                        output_objects.append(self.CreateSource(origin_object))
                    elif type(origin_object) == Output:
                        output_objects.append(self.CreateOutput(origin_object))
                return output_objects
        return None

    def CreateSource(self, s_origin: Source) -> Source:
        """
        Take the given source object, and create it on this edge.
        Automatically sets the 'mwedge' fields on the given source object such that they line up with the tx edge on which they are to be created.

        Args:
            s_origin: The source to create.

        Returns:
            The Weaver.Source returned from the API response.
        """
        try:
            s = copy.deepcopy(s_origin)
            s.mwedge = self._id                                 # Set the source's "mwedge" entry to the ID of this edge, as this is where we are creating the source!
            s.edgeObject = self
            s.id = 0                                            # Wipe the ID attached to the passed source object, as it will be overwritten when creating the source
            plainTextResponse = weaverApi.CreateSource(s).text  # Create source, and save the API response to 'plainTextResponse'
            Json = json.loads(plainTextResponse)
            s = Source(self, Json)                              # Rebuild 's' from the JSON handed back by the API (setting s._id to the ID of the newly created stream in the process)
            if self.cachingEnabled:
                self.configCache = None                         # Clear the cache on the core because it has now changed
            return s                                            # Pass the new source object back to the caller.
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return None

    def CreateOutput(self, o_origin: Output) -> Output: 
        """
        Take the given output object, and create it on this edge.
        Automatically sets the 'mwedge' fields on the given output object such that they line up with the tx edge on which they are to be created.

        Args:
            o_origin: The source to create.

        Returns:
            The Weaver.Output returned from the API response.
        """
        try:
            o = copy.deepcopy(o_origin)
            o.mwedge = self._id                                 # Set the output's "mwedge" entry to the ID of this edge, as this is where we are creating the output!
            o.edgeObject = self
            o.id = 0                                            # Wipe the ID attached to the passed output object, as it will be overwritten when creating the output
            plainTextResponse = weaverApi.CreateOutput(o).text  # Create output, and save the API response to 'plainTextResponse'
            Json = json.loads(plainTextResponse)
            o = Output(self, Json)                              # Rebuild 'o' from the JSON handed back by the API (setting o._id to the ID of the newly created stream in the process)
            if self.cachingEnabled:
                self.configCache = None                         # Clear the cache on the core because it has now changed
            return o                                            # Pass the new output object back to the caller.
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return None

    def Update(self, refreshCache: bool = True) -> bool:
        """
        Perform API call to update edge with locally made changes

        Args:
            refreshCache: Whether to forcibly refresh local cache of the edge.

        Returns:
            Outcome of the API call.
        """
        try:
            weaverApi.UpdateEdge(self)                          # Update yerself!
            if refreshCache:
                self.configCache = None                         # Clear the cache on the core because it has now changed
            return True
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return False

    @deprecated("This function is deprecated and will be removed in a future version. Use 'Update()' instead.")
    def UpdateEdge(self, refreshCache: bool = True) -> bool:
        """
        Perform API call to update edge with locally made changes

        Args:
            refreshCache: Whether to forcibly refresh local cache of the edge.

        Returns:
            Outcome of the API call.
        """
        self.Update(refreshCache)

    def DeleteSourceById(self, id: str) -> bool:
        """
        Delete a source by its ID.

        Args:
            id: The ID of the source to delete.

        Returns:
            Outcome of the API call
        """
        s = Source(self)
        s.id = id
        return s.Delete()
    
    def DeleteStreamById(self, id: str) -> bool:
        """
        Delete a stream by its ID.

        Args:
            id: The ID of the stream to delete.

        Returns:
            Outcome of the API call
        """
        s = Stream(self)
        s.id = id
        return s.Delete()
    
    def DeleteOutputById(self, id: str) -> bool:
        """
        Delete an output by its ID.

        Args:
            id: The ID of the output to delete.

        Returns:
            Outcome of the API call
        """
        o = Output(self)
        o.id = id
        return o.Delete()

#Core Class
class Core:
    # All the available variables...
    def __init__(self, address: str, token: str = "", verifyHTTPS: bool = True, defaultCallDelayMillis: int = 10, bypassHttpConfirmation: bool = False) -> 'Core': # Constructor. Take URL and (optionally) token
        self.defaultCallDelayMillis = defaultCallDelayMillis # <int> Number of milliseconds to pause after API calls to prevent overloading of the tx core
        if not "http" in address:
            address = f"https://{address}"
        if not "https://" in address:
            print("You are connecting to tx core via HTTP only. This is insecure, and can also cause some issues/inconsistencies in the tx core API.")
            print("Weaver recommends switching to HTTPS. If you have a self-signed certificate, you can skip its verification by creating the core with 'verifyHTTPS=False' to avoid issues")
            print("What would you like to do? [Enter desired number, then press ENTER]\n")
            print("[1] Continue script execution via HTTP. (You can bypass this warning in future by creating the core with 'bypassHttpConfirmation=True')")
            print("[2] Switch to HTTPS, but bypass verification of the SSL certificate (if it's self-signed) (recommended)")
            print("[3] Switch to HTTPS and require SSL certificate verification")
            print("[Anything else] Exit script")
            if bypassHttpConfirmation:
                print("bypassHttpConfirmation is set, skipping this warning and continuing with HTTP")
            else:
                selected_option = input()
                if selected_option == "1":
                    print("Continuing via HTTP...")
                elif selected_option == "2":
                    print("Switching to HTTPS without mandatory SSL verification")
                    address = address.replace("http://", "https://")
                    verifyHTTPS = False
                elif selected_option == "3":
                    print("Switching to HTTPS with mandatory SSL verification")
                    address = address.replace("http://", "https://")
                    verifyHTTPS = True
                else:
                    exit()
        self.coreAddress: str = address              # <str> tx core URL / DNS / IP
        self.verifyHTTPS:bool = verifyHTTPS          # <bool> Whether to verify HTTPS certs
        if token == "":                         # If no token given
            self.Authenticate()                 # Request to auth
        else:                                   # Otherwise
            self.authToken: str = token              # <str> API Token
            self.authenticated: bool = True           # <bool> Whether an API token is held (NOT whether the API token is valid.)
        self.version = weaverApi.GetCoreVersion(self)

    def __str__(self):
        try:
            currentUser = str(json.loads(weaverApi.GetCurrentUser(self).text)['username'])
        except:
            currentUser = ""
        return(f"Connected to tx core {self.coreAddress} as {currentUser}. Core version {self.version}.\n- Call Delay: {self.defaultCallDelayMillis}\n- Verifying HTTPS: {self.verifyHTTPS}")
    
    def __repr__(self): # This should be improved, ideally, but it's an initial failsafe.
        currentUser = ""
        actual_auth = self.authenticated
        try:
            currentUser = str(json.loads(weaverApi.GetCurrentUser(self).text)['username'])
            actual_auth = True
        except:
            currentUser = "(invalid auth)"
            actual_auth = False
        return json.dumps({'coreAddress': self.coreAddress, 'version': self.version, 'defaultCallDelayMills': self.defaultCallDelayMillis, 'verifyHTTPS': self.verifyHTTPS, 'auth': {'authenticated': actual_auth, 'authToken': 'REDACTED', 'currentUser': currentUser}})

    def Authenticate(self, username: str = "null", password: str = "null") -> bool: # Authenticate/Login via username and password
        """
        Fetch an API token by authentication with the given user credentials

        Args:
            username: Username
            password: Password

        Returns:
            Boolean, whether authentication was successful.
        """
        if username == "null":                                                          # If not been given username
            print("Enter username for " + self.coreAddress)                             # Ask user for it
            username = input()                                                          
        if password == "null":                                                                             # If not been given password
            print("You must supply a password in the function. For security it cannot be entered at CLI.") # Inform user
            return False                                                                                   # Reject auth
        self.authToken = weaverApi.GetAuthKey(self.coreAddress, username, password)     # Get to set token
        if len(self.authToken) > 10:                                                    # If token len > 10 (true for valid token, false for "Wrong!")
            self.authenticated: bool = True                                                   # Set authed to true
        return self.authenticated                                                       # Return auth status

    def GetDevices(self, jsonQuery: str = "online=true&limit=-1") -> List[Device]:
        """
        Fetch array of Weaver.Device objects representing devices on the tx core that match the jsonQuery.

        Args:
            jsonQuery: The query to apply to the URL, for example 'online=true&limit=-1'

        Returns:
            Array of matching Weaver.Device objects
        """
        try:
            resp = weaverApi.GetDevices(self, jsonQuery)
            plainText = resp.text
            Json = json.loads(plainText)
            devices = []
            for row in Json['rows']:
                devices.append(Device(self, row))
            return devices
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return []

    def GetUsers(self, jsonQuery: str = "limit=-1") -> List[User]:
        """
        Fetch array of Weaver.User objects representing user on the tx core that match the jsonQuery.

        Args:
            jsonQuery: The query to apply to the URL, for example 'limit=-1'

        Returns:
            Array of matching Weaver.User objects
        """
        try:
            resp = weaverApi.GetUsers(self, jsonQuery)
            plainText = resp.text
            Json = json.loads(plainText)
            users = []
            for row in Json['rows']:
                users.append(User(self, row))
            return users
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return []

    def GetEdges(self, jsonQuery: str = "online=true&limit=-1", enableCache: bool = False) -> List[Edge]: # Get tx edges, takes optional query
        """
        Fetch array of Weaver.Edge objects representing edges on the tx core that match the jsonQuery.

        Args:
            jsonQuery: The query to apply to the URL, for example 'online=true&limit=-1'
            enableCache: Whether to enable config caching on the edge, which can slightly reduce number of GET API calls required.

        Returns:
            Array of matching Weaver.Edge objects
        """
        try:
            resp = weaverApi.GetEdges(self, jsonQuery) 
            plainText = resp.text
            # Pass to weaverApi, return result
            Json = json.loads(plainText)                                                    # Convert the string to JSON
            edges = []                                                                      # Create an array for the edges
            for row in Json['rows']:                                                        # For every key in 'configuredSources'
                newEdge = Edge(self, row, cachingEnabled=enableCache)                       # Create a new edge
                edges.append(newEdge)                                                       # Append to array
            return edges
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return []

    def GetEdgeById(self, id: str, enableCache: bool = False) -> Edge: # Get MWEdge by ID, take ID
        """
        Fetch Weaver.Edge object of the edge with the specified ID

        Args:
            id: The ID of the edge to fetch
            enableCache: Whether to enable local caching of the config. Can slightly reduce the number of GET requests used.

        Returns:
            Weaver.Edge of the edge.
        """
        try:
            resp = weaverApi.GetEdgeById(self, id)
            plainText = resp.text
            response = json.loads(plainText)
            result = Edge(self, response, cachingEnabled=enableCache)
            return result                                                                   # Return Edge object.
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return None

    def GetChannels(self, jsonQuery: str = "limit=-1") -> List[Channel]: # Get all channels on the tx core (with optional query/filter)
        """
        Fetch array of Weaver.Channel objects representing channels on the tx core that match the jsonQuery.

        Args:
            jsonQuery: The query to apply to the URL, for example 'limit=-1'

        Returns:
            Array of matching Weaver.Channel objects
        """
        try:
            response = weaverApi.GetChannels(self, jsonQuery)
            jsonrows = json.loads(response.text)['rows']
            channels = []
            for row in jsonrows:
                channel = Channel(row, self)
                channels.append(channel)
            return channels
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return []
        
    def Create(self, o_origin: Channel) -> Channel: # This will need populating with other types (e.g. Users) as implemented...
        """
        Create the given object on the tx core

        Args:
            o_origin: The object to create. At the moment, only supports Channels.

        Returns:
            Object representing the created object.
        """
        try:
            if type(o_origin) == Channel:
                return self.CreateChannel(o_origin)
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return []
    
    def CreateChannel(self, channel: Channel) -> Channel:
        """
        Create IPTV channel on the core from the provided channel object

        Args:
            channel: Channel to create.

        Returns:
            Weaver.Channel of the created object
        """
        try:
            channel.coreObject = self
            channel._id = None
            channel.updatedAt = None
            channel.createdAt = None
            i = 0
            while i < len(channel.sources):
                tempSource = channel.sources[i]
                tempSource._id = None
                channel.sources[i] = tempSource
                i += 1
            plainTextResponse = weaverApi.CreateChannel(channel).text
            Json = json.loads(plainTextResponse)
            c = Channel(Json, self)
            return c
        except Exception as e:
            if quitOnError:
                if (e.message):
                    print(e.message)
                else:
                    print(e)
                exit()
            return None

    def DeleteChannelById(self, id: str) -> bool: # Delete Channel by its string ID
        """
        Delete via API the channel with the specified ID.

        Args:
            id: The ID of the channel to delete.

        Returns:
            The outcome of the API call.
        """
        c = Channel("{}", self)
        c._id = id
        return c.Delete()
