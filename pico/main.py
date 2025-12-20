import time
from argb import *
from machine import Pin, UART
import neopixel
import rusb
from _thread import start_new_thread
import json

UPDATE_FREQUENCY = 50 # hz

JSON_CONFIG = 'config.json'

# Config codes
CONFIG_STRIP_CODE = 0b1111 # 1 bit for reversed,
                           # 5 bits for GPIO pin,
                           # 2 bits + 1 byte for LED #
DELETE_STRIP_CODE = 0b1110
UPDATE_FREQ_CODE = 0b1101 # 1 byte for update frequency in hz

# Destructive Control codes
OFF_CODE = 0b0000
SOLID_CODE = 0b0001 # 3 bytes of color
RAINBOW_CODE = 0b0010 # 1 byte for speed
GRADIENT_CODE = 0b0011 # 3 bytes for color 1, 3 bytes for color 2
MOVING_PULSES_CODE = 0b0100 # 4 bits for # pulses, 4 bits for decay, 1 speed byte, 3 for color

# Non-Destructive Control Codes
SET_PIXEL_CODE = 0b0101 # 1 byte for idx, 3 bytes for color
SET_RANGE_CODE = 0b0110 # 2 bytes for start + end idx, 3 bytes for color
BRIGHTNESS_CODE = 0b1000 # 1 byte for brightness level
BREATHING_CODE = 0b1001 # 1 byte 

DATA_LENGTH = {
    CONFIG_STRIP_CODE: 2,
    DELETE_STRIP_CODE: 0,
    UPDATE_FREQ_CODE: 1,
    OFF_CODE: 0,
    SOLID_CODE: 3,
    RAINBOW_CODE: 1,
    GRADIENT_CODE: 6,
    MOVING_PULSES_CODE: 5,
    SET_PIXEL_CODE: 4,
    SET_RANGE_CODE: 5,
    BRIGHTNESS_CODE: 1,
    BREATHING_CODE: 1,
}

def updateJSON(strips: list[LEDStrip], pattern_codes: list[dict[str,list]]):
    config = {'Strips': [{
        'Pin': strip.pin,
        'Length': strip.length,
        'Reversed': strip.reversed
    } for strip in strips],
              'Patterns': pattern_codes}
    with open(JSON_CONFIG, 'w') as f:
        f.write(json.dumps(config, indent=4))

def loadJSON(strips: list[LEDStrip], patterns: list[Pattern], pattern_codes: list[dict[str,list]]):
    strips.clear()
    patterns.clear()
    pattern_codes.clear()
    
    with open(JSON_CONFIG) as f:
        config = json.load(f)
        
    for strip in config['Strips']:
        strips.append(LEDStrip(strip['Pin'], strip['Length'], strip['Reversed']))
        patterns.append(Pattern.off(strip['Length']))
        
    pattern_codes.extend(config['Patterns'])
    for i in range(len(config['Patterns'])):
        for j in range(len(config['Patterns'][i]['Codes'])):
            apply_pattern(strips, patterns, pattern_codes, i, config['Patterns'][i]['Codes'][j], config['Patterns'][i]['Data'][j])

def apply_config(strips: list[LEDStrip], strip_id, data):
    reversed = bool(data[0] >> 7)
    pin = (data[0] & 0b01111100) >> 2
    length = ((data[0] & 0b11) << 8) + data[1]
    
    if strip_id < len(strips):    
        strips[strip_id].length = length
        strips[strip_id].pin = pin
        strips[strip_id].reversed = reversed
    else:
        strips.append(LEDStrip(pin, length, reversed))
        
def delete_strip(strips: list[LEDStrip], patterns: list[Pattern], pattern_codes: list[dict[str,list]], strip_id):
    strips.pop(strip_id)
    patterns.pop(strip_id)
    pattern_codes.pop(strip_id)

def apply_pattern(strips: list[LEDStrip], patterns: list[Pattern], pattern_codes: list[dict[str, list]], strip_id, control_code, data):
    led_count = strips[strip_id].length

    if control_code == OFF_CODE:
        patterns[strip_id] = Pattern.off(led_count)
        
        pattern_codes[strip_id]['Codes'].clear()
        pattern_codes[strip_id]['Data'].clear()
    elif control_code == SOLID_CODE:
        color = (data[0], data[1], data[2])
        patterns[strip_id] = Pattern.solid(color, led_count)
        
        pattern_codes[strip_id]['Codes'].clear()
        pattern_codes[strip_id]['Data'].clear()
    elif control_code == RAINBOW_CODE:
        patterns[strip_id] = RainbowPattern(led_count, data[0]*5/255/UPDATE_FREQUENCY, 2.0)
        
        pattern_codes[strip_id]['Codes'].clear()
        pattern_codes[strip_id]['Data'].clear()
    elif control_code == GRADIENT_CODE:
        startcolor = (data[0], data[1], data[2])
        endcolor = (data[3], data[4], data[5])
        patterns[strip_id] = Pattern.gradient(startcolor, endcolor, led_count)
        
        pattern_codes[strip_id]['Codes'].clear()
        pattern_codes[strip_id]['Data'].clear()
    elif control_code == BRIGHTNESS_CODE:
        patterns[strip_id].set_brightness(data[0]/255)
    elif control_code == BREATHING_CODE:
        patterns[strip_id] = BreathingPattern(patterns[strip_id], data[0]*5/255/UPDATE_FREQUENCY)
    
    pattern_codes[strip_id]['Codes'].append(control_code)
    pattern_codes[strip_id]['Data'].append(data)
    
    strips[strip_id].apply_pattern(patterns[strip_id])
    strips[strip_id].show()
            
def check_input():
    buffer = rusb.getByteBuffer()
    if not buffer:
        return False, []
    print(buffer)
    for i in range(len(buffer)):
        if buffer[i] == 0xFF:
            return True, buffer[i+1:]
    return False, []

def read_data(buffer0, timeout_ms = 100):
    last_input_time = time.ticks_ms()
   
    strip_id = 0
    control_code = None
    data = []
    data_len = 24 # arbitrary large-ish number
    if len(buffer0)> 0:
        control_code = int(buffer0[0])
        strip_id = control_code >> 4
        control_code &= 0b00001111
        data = buffer0[1:]
        data_len = DATA_LENGTH[control_code]
    while time.ticks_diff(time.ticks_ms(), last_input_time) < timeout_ms and len(data) < data_len:
        time.sleep(0.01)
        buffer = rusb.getByteBuffer()
        if not buffer:
            continue
        last_input_time = time.ticks_ms()
        if control_code is None:
            control_code = int(buffer[0])
            strip_id = control_code >> 4
            control_code &= 0b0001111
            data_len = DATA_LENGTH[control_code]
            continue

        data.append(int(buffer[0]))

    return strip_id, control_code, data

def main():
    patterns = []
    strips = []
    pattern_codes = []
    loadJSON(patterns, strips, pattern_codes)
    
    while True:
        # get input
        check, buffer0 = check_input()
        if check:
            strip_id, control_code, data = read_data(buffer0, timeout_ms=100)
            if control_code == CONFIG_STRIP_CODE:
                apply_config(strips, strip_id, data)
            elif control_code == DELETE_STRIP_CODE:
                delete_strip(strips, patterns, pattern_codes, strip_id)
            else:
                apply_pattern(strips, patterns, pattern_codes, strip_id, control_code, data)
            updateJSON(strips, pattern_codes)
            print("Received data:", strip_id, bin(control_code), data)
        
        for i in range(len(patterns)):
            if isinstance(patterns[i], AnimatedPattern):
                patterns[i].update()
                strips[i].apply_pattern(patterns[i])
            strips[i].show()
        
        # update strips
        time.sleep(1/UPDATE_FREQUENCY)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        rusb.terminateThread = True
        raise KeyboardInterrupt
