from dataclasses import dataclass
from nicegui import ui
import serialcontrol as ser
import json

def hex_str_to_rgb(hex: str) -> list[int]:
    byte = int(hex[1:], 16)
    return [byte >> 16, (byte >> 8) & 0xFF, byte & 0xFF]

@dataclass
class Pattern:
    name: str
    control_code: int
    numeric_params: dict[str, int]
    color_params: dict[str, str] # stored as hex strings
    
    def generate_bytes(self, strip_id: int) -> list[int]:
        return [strip_id << 4 + self.control_code] + self.numeric_bytes() + self.numeric_bytes()
    
    def color_bytes(self) -> list[int]:
        output = []
        for color in self.color_params.values():
            output += hex_str_to_rgb(color)
            
        return output
    
    def numeric_bytes(self) -> list[int]:
        return list(self.numeric_params.values())
    
    def to_dict(self) -> dict:
        return {
            'Name': self.name,
            'Control Code': self.control_code,
            'Numeric': self.numeric_params,
            'Color': self.color_params
        }
        
class Off(Pattern):
    def __init__(self) -> None:
        super().__init__('Off', 0b0000, {}, {})
        
class Solid(Pattern):
    def __init__(self, color: str, brightness: int=255) -> None:
        super().__init__('Solid', 0b0001, {'Brightness': brightness}, {'Color': color})

class Rainbow(Pattern):
    def __init__(self, speed: int, scale: int, brightness: int=255) -> None:
        super().__init__('Rainbow', 0b0010, {'Speed': speed, 'Scale': scale, 'Brightness': brightness}, {})
        
class Gradient(Pattern):
    def __init__(self, start: str, end: str, brightness: int=255) -> None:
        super().__init__('Gradient', 0b0111, {'Brightness': brightness}, {'Start Color': start, 'End Color': end})
        
class Breathing(Pattern):
    def __init__(self, speed: int, color: str, brightness: int=255) -> None:
        super().__init__('Rainbow', 0b0010, {'Speed': speed, 'Brightness': brightness}, {'Color': color})
                
@dataclass
class Preset:
    name: str
    pattern: Pattern
    
    def to_dict(self):
        return {
            'Name': self.name,
            'Pattern': self.pattern
        }

class Strip:
    def __init__(self, name: str, pin: int, length: int) -> None:
        self.name = name
        self.pin = pin
        self.length = length
        self.pattern: Pattern = Off()
        self.preset: Preset | None = None
        
    def config_dict(self) -> dict:
        return {
            'Name': self.name,
            'Pin': self.pin,
            'Length': self.length
        }

    def set_pattern(self, pattern: Pattern):
        self.pattern = pattern