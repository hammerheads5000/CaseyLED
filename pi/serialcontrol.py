import serial
import serial.tools.list_ports

try:
    _serial_port = serial.Serial(
            port='/dev/ttyACM1',
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS)
    if not _serial_port.is_open:
        _serial_port.open()
except:
    print('failed top open /dev/ttyACM1')
    try:
        _serial_port = serial.Serial(
                port='/dev/ttyACM0',
                baudrate=115200,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS)
        if not _serial_port.is_open:
            _serial_port.open()
    except Exception as e:
        raise e

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
GRADIENT_CODE = 0b0111 # 3 bytes for color 1, 3 bytes for color 2
MOVING_PULSES_CODE = 0b0100 # 4 bits for # pulses, 4 bits for decay, 1 speed byte, 3 for color
SET_PIXEL_CODE = 0b0101 # 1 byte for idx, 3 bytes for color
SET_RANGE_CODE = 0b0110 # 2 bytes for start + end idx, 3 bytes for color

# Non-Destructive Control Codes
BRIGHTNESS_CODE = 0b1000 # 1 byte for brightness level
BREATHING_CODE = 0b1001 # 1 byte 

def send_config(id: int, pin: int, length: int):
    length_byte0 = (length >> 8) & (0b11)
    byte0 = ((pin & 0b11111) << 2) | length_byte0
    byte1 = length & 0xFF
    send_control_code(id, CONFIG_STRIP_CODE, [byte0, byte1])
    
def send_control_code(id: int, code: int, data: (list[int] | int) = []):
    if isinstance(data, list):
        for i in range(len(data)):
            if data[i] == 3:
                data[i] = 4
        _serial_port.write(bytes([0xFF, id << 4 | code] + data))
    else:
        if data == 3:
            data = 4

        _serial_port.write(bytes([0xFF, id << 4 | code, data]))
    
