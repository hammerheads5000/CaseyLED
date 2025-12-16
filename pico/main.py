import time
from argb import *
from machine import Pin, UART
import neopixel
import rusb
from _thread import start_new_thread

UPDATE_FREQUENCY = 50 # hz

STRIPS = {
    'Left': {
        'Pin': Pin.board.GP10,
        'Count': 106,
    },
    'Right': {
        'Pin': Pin.board.GP4,
        'Count': 105,
    },
    'Workbench': {
        'Pin': Pin.board.GP8,
        'Count': 140,
    },
    'Shelf': {
        'Pin': Pin.board.GP6,
        'Count': 140,
    },
}

# LED Strip IDs
LEFT_ID = 0b000
RIGHT_ID = 0b001
SHELF_ID = 0b010
WORKBENCH_ID = 0b011

# Destructive Control codes
OFF_CODE = 0b00000
SOLID_CODE = 0b00001 # 3 bytes of color
RAINBOW_CODE = 0b00010 # 1 byte for speed
GRADIENT_CODE = 0b00011 # 3 bytes for color 1, 3 bytes for color 2

# Non-Destructive Control Codes
BRIGHTNESS_CODE = 0b10000 # 1 byte for brightness level
BREATHING_CODE = 0b10001 # 1 byte

DATA_LENGTH = {
    OFF_CODE: 0,
    SOLID_CODE: 3,
    RAINBOW_CODE: 1,
    GRADIENT_CODE: 6,
    BRIGHTNESS_CODE: 1,
    BREATHING_CODE: 1,
}


def apply_control(strips, patterns, strip_id, control_code, data):
    led_count = 0
    idx = 0
    if strip_id==LEFT_ID:
        led_count = STRIPS['Left']['Count']
        idx = 0
    elif strip_id == RIGHT_ID:
        led_count = STRIPS['Right']['Count']
        idx = 1
    elif strip_id == WORKBENCH_ID:
        led_count = STRIPS['Workbench']['Count']
        idx = 2
    elif strip_id == SHELF_ID:
        led_count = STRIPS['Shelf']['Count']
        idx = 3
        
    if control_code == OFF_CODE:
        patterns[idx] = Pattern.off(led_count)
    elif control_code == SOLID_CODE:
        color = (data[0], data[1], data[2])
        patterns[idx] = Pattern.solid(color, led_count)
    elif control_code == RAINBOW_CODE:
        patterns[idx] = RainbowPattern(led_count, 1.5/UPDATE_FREQUENCY, 2.0)
    elif control_code == GRADIENT_CODE:
        startcolor = (data[0], data[1], data[2])
        endcolor = (data[3], data[4], data[5])
        patterns[idx] = MovingPattern(Pattern.gradient(startcolor, endcolor, led_count), 20)
    elif control_code == BRIGHTNESS_CODE:
        patterns[idx].set_brightness(data[0]/255)
    
    strips[idx].apply_pattern(patterns[idx])
    strips[idx].show()
            
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
        strip_id = control_code >> 5
        control_code &= 0b00011111
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
            strip_id = control_code >> 5
            control_code &= 0b00011111
            data_len = DATA_LENGTH[control_code]
            continue

        data.append(int(buffer[0]))

    return strip_id, control_code, data

def main():
    patterns = [
        Pattern.off(STRIPS['Left']['Count']),
        Pattern.off(STRIPS['Right']['Count']),
        Pattern.off(STRIPS['Workbench']['Count']),
        Pattern.off(STRIPS['Shelf']['Count'])
    ]
    strips = [
        LEDStrip(STRIPS['Left']['Pin'], STRIPS['Left']['Count']),
        LEDStrip(STRIPS['Right']['Pin'], STRIPS['Right']['Count']),
        LEDStrip(STRIPS['Workbench']['Pin'], STRIPS['Workbench']['Count']),
        LEDStrip(STRIPS['Shelf']['Pin'], STRIPS['Shelf']['Count'])
    ]
    
    while True:
        # get input
        check, buffer0 = check_input()
        if check:
            strip_id, control_code, data = read_data(buffer0, timeout_ms=100)
            apply_control(strips, patterns, strip_id, control_code, data)
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
