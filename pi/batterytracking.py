import nextmatch
import time

_current_notifications = []
_far_future = int(time.time()) + 365*24*60*60
_match_batteries: dict[str, int] = {}
NUM_BATTERIES = 10

def init():
    matches = nextmatch.get_nexus_matches()
    for i in range(len(matches)):
        _match_batteries[matches[i]['label']] = i % NUM_BATTERIES # type: ignore

def remove_battery_notification(match):
    bat = _match_batteries[match['label']]
    

def get_notifications_from_match(match):
    start_time = _far_future
    if 'estimatedOnFieldTime' in match['times']:
        start_time = match['times']['estimatedOnFieldTime']//1000
    elif 'scheduledOnFieldTime' in match['times']:
        start_time = match['times']['scheduledOnFieldTime']//1000

    if time.time() > start_time - 15*60:
        

def get_notifications():
    pass