import nextmatch
import time

_far_future = int(time.time()) + 365*24*60*60
_match_batteries: dict[str, int] = {}
NUM_BATTERIES = 10

def init():
    matches = nextmatch.get_nexus_matches()
    for i in range(len(matches)):
        _match_batteries[matches[i]['label']] = i % NUM_BATTERIES + 1 # type: ignore

def remove_battery_notification(match):
    bat = _match_batteries[match['label']]
    return f'Remove battery {bat} from charger!'

def add_battery_notification(match):
    bat = _match_batteries[match['label']]
    return f'Place battery {bat} back on charger!'

def get_notifications_from_match(match, current_notifications: set[str]):
    start_time = _far_future
    if 'estimatedOnFieldTime' in match['times']:
        start_time = match['times']['estimatedOnFieldTime']//1000
    elif 'scheduledOnFieldTime' in match['times']:
        start_time = match['times']['scheduledOnFieldTime']//1000

    if match['status'] != 'Complete' and time.time() > start_time - 15*60:
        current_notifications.add(remove_battery_notification(match))
    elif match['status'] == 'Complete' and time.time() > start_time + 30*60:
        current_notifications.add(add_battery_notification(match))

def get_notifications() -> set[str]:
    current_notifications: set[str] = set()
    matches = nextmatch.get_nexus_matches()
    if isinstance(matches, str):
        return set()
    for match in matches:
        get_notifications_from_match(match, current_notifications)
        
    return current_notifications