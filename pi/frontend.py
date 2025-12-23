from nicegui import binding, ui
import serialcontrol as ser
import json

def hex_str_to_rgb(hex: str) -> list[int]:
    if hex[0] == '#': # strip leading '#'
        hex = hex[1:]
    if len(hex) == 2: # duplicate single value to three
        hex *= 3
    byte = int(hex, 16)
    return [byte >> 16, (byte >> 8) & 0xFF, byte & 0xFF]

@binding.bindable_dataclass
class Pattern:
    name: str = ''
    control_code: int = -1
    numeric_params: dict[str, int] = {}
    color_params: dict[str, str] = {} # stored as hex strings
    
    def generate_bytes(self, strip_id: int) -> list[int]:
        return [strip_id << 4 + self.control_code] + self.numeric_bytes() + self.numeric_bytes()
    
    def color_bytes(self) -> list[int]:
        output = []
        for color in self.color_params.values():
            output += hex_str_to_rgb(color)
            
        return output
    
    def numeric_bytes(self) -> list[int]:
        return list(self.numeric_params.values())
    
    def asdict(self) -> dict:
        return {
            'Name': self.name,
            'Control Code': self.control_code,
            'Numeric': self.numeric_params,
            'Color': self.color_params
        }
        
    def property_panel(self, pattern_select: ui.select, update) -> None:
        with ui.card().bind_visibility_from(pattern_select, value=self.name):
            for param, val in self.numeric_params.items():
                ui.label(param)
                ui.slider(min=0, max=254, step=1, value=val,
                        on_change=update)
            for param, color in self.color_params.items():
                ui.label(param)
                ui.color_input(value=color, preview=True,
                        on_change=lambda e: self.set_color_param(param, e.value))
        
    def set_numeric_param(self, param: str, value: int) -> None:
        self.numeric_params[param] = value
        
    def set_color_param(self, param: str, value: str) -> None:
        self.color_params[param] = value
        
    def get_preview_classes(self) -> str:
        return ''

class Off(Pattern):
    def __init__(self) -> None:
        super().__init__('Off', 0b0000, {}, {})
    
    def get_preview_classes(self) -> str:
        return 'border border-gray-700 !bg-none'
        
class Solid(Pattern):
    def __init__(self, color: str, brightness: int=255) -> None:
        super().__init__('Solid', 0b0001, {'Brightness': brightness}, {'Color': color})

    def get_preview_classes(self) -> str:
        return f'border-none !bg-[{self.color_params['Color']}]'
class Rainbow(Pattern):
    def __init__(self, speed: int = 20, scale: int = 20, brightness: int=255) -> None:
        super().__init__('Rainbow', 0b0010, {'Speed': speed, 'Scale': scale, 'Brightness': brightness}, {})

    def get_preview_classes(self) -> str:
        return 'border-none !bg-linear-to-r/decreasing from-violet-700 via-[#00FF00] to-violet-700'
class Gradient(Pattern):
    def __init__(self, start: str, end: str, brightness: int=255) -> None:
        super().__init__('Gradient', 0b0111, {'Brightness': brightness}, {'Start Color': start, 'End Color': end})

    def get_preview_classes(self) -> str:
        return f'border-none !bg-linear-to-r from-[{self.color_params['Start Color']}] to-[{self.color_params['End Color']}]'
class Breathing(Pattern):
    def __init__(self, speed: int, color: str, brightness: int=255) -> None:
        super().__init__('Breathing', 0b0010, {'Speed': speed, 'Brightness': brightness}, {'Color': color})

    def get_preview_classes(self) -> str:
        return f'border-none !bg-[{self.color_params['Color']}]'
@binding.bindable_dataclass
class Preset:
    name: str
    
    def asdict(self):
        return {'Name': self.name}

@binding.bindable_dataclass
class StripPreset(Preset):
    pattern: Pattern
    
    def asdict(self):
        return {
            'Name': self.name,
            'Pattern': self.pattern
        }

@binding.bindable_dataclass
class GlobalPreset(Preset):
    patterns: list[Pattern]
    
    def asdict(self):
        return {
            'Name': self.name,
            'Patterns': self.patterns
        }

def save_config():
    with open('config.json', 'w') as f:
        json.dump({'Strips': [strip for strip in strips]}, f, indent=4)

def init_strips():
    with open('config.json') as f:
        configs = json.load(f)['Strips']
        for i in range(len(configs)):
            strips.append(Strip.fromdict(configs[i]))
            ser.send_config(i, strips[i].pin, strips[i].length)
            
def update_config():
    with open('config.json') as f:
        configs = json.load(f)['Strips']
        for i in range(len(strips)):
            strips[i].configure(configs[i])
            ser.send_config(i, strips[i].pin, strips[i].length)

class Strip:
    def __init__(self, name: str, pin: int, length: int, pattern: Pattern = Off(), preset: Preset | None = None) -> None:
        self.name = name
        self.pin = pin
        self.length = length
        self.pattern = pattern
        self.preset = preset
        self._patterns = []
        for cls in Pattern.__subclasses__():
            if isinstance(pattern, cls):
                self._patterns.append(pattern)
            else:
                self._patterns.append(cls())
    
    @classmethod
    def fromdict(cls, config: dict):
        return cls(config['Name'], config['Pin'], config['Length'])
        
    def asdict(self) -> dict:
        return {
            'Name': self.name,
            'Pin': self.pin,
            'Length': self.length,
            'Pattern': self.pattern.asdict(),
            'Preset': self.preset.asdict() if self.preset else None,
        }

    def set_pattern(self, pattern: Pattern):
        self.pattern = pattern
        
    def configure(self, config: dict):
        self.name = config['Name']
        self.pin = config['Pin']
        self.length = config['Length']
        
    @ui.refreshable_method
    def ui_select(self):
        with ui.button().classes('w-full p-2').props('color=grey-10 align="left" no-caps') as button:
            ui.label(f'{self.name} Strip')
            ui.card().classes('no-shadow grow h-3 p-0 w-full ' + self.pattern.get_preview_classes())
        return button
            
    def ui_panel(self):
        with ui.card().classes('w-full') as card:
            
    
strips: list[Strip]
presets: list[StripPreset]
global_presets: list[GlobalPreset]