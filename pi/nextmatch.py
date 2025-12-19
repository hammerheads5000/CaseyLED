import time
import requests
import json

TEAM_KEY = 'frc1540'
EVENT_KEY = '2025wass'

TBA_BASE_URL = f'https://www.thebluealliance.com/api/v3/team/{TEAM_KEY}/event/{EVENT_KEY}/matches/simple'
TBA_API_KEY = 'FpRFwcc2ADT4NcREAW1fELKVweMyTWyIf7R6z5mMs0QoWPrWyQiq4XLJLfIghsXj'

tba_prev_etag = '"cd00f5b05a82f7841e0861d7e78099adaa92475"' # str | Value of the `ETag` header in the most recently cached response by the client. (optional)
tba_next_valid_time = 0
tba_cached_response = None

def get_tba_matches():
    global tba_next_valid_time, tba_cached_response, tba_prev_etag
    
    if time.time() < tba_next_valid_time:
        return tba_cached_response
    
    api_response = requests.get(TBA_BASE_URL, headers={"X-TBA-Auth-Key": TBA_API_KEY, "If-None-Match": tba_prev_etag})
    tba_prev_etag = api_response.headers.get('ETag')
    tba_next_valid_time = time.time() + int(api_response.headers.get('Cache-Control').split('=')[1].split(',')[0])
    
    if (api_response.status_code == 304):
        return tba_cached_response
    
    tba_cached_response = api_response.json()
    
    return tba_cached_response

def get_next_match():
    matches = get_tba_matches()
    if matches is None:
        return None
    for match in matches:
        if match['actual_time'] == 1761431384:
            return match
    return None

def get_color(match):
    if not match:
        return None
    if TEAM_KEY in match['alliances']['red']['team_keys']:
        return 'red'
    elif TEAM_KEY in match['alliances']['blue']['team_keys']:
        return 'blue'
    else:
        return None