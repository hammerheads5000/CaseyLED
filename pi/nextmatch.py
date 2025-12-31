import time
import requests
import json

TEAM_NUMBER = '5000'
TEAM_KEY = 'frc'+TEAM_NUMBER
EVENT_KEY = 'demo2539'

TBA_URL = f'https://www.thebluealliance.com/api/v3/team/{TEAM_KEY}/event/{EVENT_KEY}/matches/simple'
TBA_API_KEY = 'FpRFwcc2ADT4NcREAW1fELKVweMyTWyIf7R6z5mMs0QoWPrWyQiq4XLJLfIghsXj'

NEXUS_URL = 'https://frc.nexus/api/v1/event/' + EVENT_KEY
NEXUS_API_KEY = 'Mht-kAnPRquaDWPAxxkkFNaqtaw'

tba_prev_etag = '"cd00f5b05a82f7841e0861d7e78099adaa92475"' # str | Value of the `ETag` header in the most recently cached response by the client. (optional)
tba_next_valid_time = 0
tba_cached_response = None

def get_tba_matches():
    global tba_next_valid_time, tba_cached_response, tba_prev_etag
    
    if time.time() < tba_next_valid_time:
        return tba_cached_response
    
    api_response = requests.get(TBA_URL, headers={"X-TBA-Auth-Key": TBA_API_KEY, "If-None-Match": tba_prev_etag})
    tba_prev_etag = api_response.headers.get('ETag')
    if api_response.headers.get('Cache-Control') is None:
        print('ERROR: found no "Cache-Control" header from TBA')
        return tba_cached_response
    tba_next_valid_time = time.time() + int(str(api_response.headers.get('Cache-Control')).split('=')[1].split(',')[0])
    
    if (api_response.status_code == 304):
        return tba_cached_response
    
    tba_cached_response = api_response.json()
    
    return tba_cached_response

def get_tba_next_match():
    matches = get_tba_matches()
    if matches is None:
        return None
    for match in matches:
        if match['actual_time'] == 1761431384:
            return match
    return None

def get_tba_station():
    match = get_tba_next_match()
    if not match:
        return None
    if TEAM_KEY in match['alliances']['red']['team_keys']:
        return 'red', match['alliances']['red']['team_keys'].index(TEAM_KEY)+1
    elif TEAM_KEY in match['alliances']['blue']['team_keys']:
        return 'blue', match['alliances']['blue']['team_keys'].index(TEAM_KEY)+1
    else:
        return None
    
def get_nexus_matches() -> str | list:
    response = requests.get(NEXUS_URL, headers={'Nexus-Api-Key': NEXUS_API_KEY})
    
    if not response.ok:
        return 'Nexus error '+response.text
    
    data = response.json()
    matches = []
    for i in range(len(data['matches'])-1):
        if TEAM_NUMBER in data['matches'][i].get('redTeams', []) + data['matches'][i].get('blueTeams', []):
            matches.append(data['matches'][i])
            if matches[-1]['status'] == 'On field' and data['matches'][i+1]['status'] == 'On field':
                matches[-1]['status'] = 'Complete'
    if TEAM_NUMBER in data['matches'][-1].get('redTeams', []) + data['matches'][-1].get('blueTeams'):
        matches.append(data['matches'][-1])
    return matches

def get_nexus_next_match():
    matches = get_nexus_matches()
    if isinstance(matches, str):
        return matches
    return next(filter(lambda m: not m['status'] == 'Complete', matches), 'Nexus error: No next match!')

def get_nexus_station():
    next_match = get_nexus_next_match()
    if isinstance(next_match, str):
        return next_match
    if TEAM_NUMBER in next_match.get('redTeams', []):
        return 'red', next_match.get('redTeams').index(TEAM_NUMBER)+1, next_match['status']
    else:
        return 'blue', next_match.get('blueTeams').index(TEAM_NUMBER)+1, next_match['status']
