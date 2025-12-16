import serial
import serial.tools.list_ports

_serial_port = serial.Serial(
        port='/dev/ttyACM0',
        baudrate=9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS)
if not _serial_port.isOpen():
    _serial_port.open()

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

def send_control_code(id, code, data: (list[int] | int) = []):
    if isinstance(data, list):
        _serial_port.write([0xFF, id << 5 | code] + data)
    else:
        _serial_port.write([0xFF, id << 5 | code, data])
    
