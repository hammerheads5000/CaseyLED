from dataclasses import dataclass, field
import traceback
import nextmatch
from nicegui import events, ui, app, run
import serialcontrol as ser
import json
from typing import Callable
import cam
import asyncio

def handle_key(e: events.KeyEventArguments):
    if e.key.f8 and e.action.keydown and 'Off' in global_presets.keys():
        apply_global_preset(global_presets['Off'])
    elif e.key.f9 and e.action.keydown and 'Main' in global_presets.keys():
        apply_global_preset(global_presets['Main'])

keyboard = ui.keyboard(on_key=handle_key)

def hex_str_to_rgb(hex: str) -> list[int]:
    if hex[0] == '#': # strip leading '#'
        hex = hex[1:]
    if len(hex) == 2: # duplicate single value to three
        hex *= 3
    byte = int(hex, 16)
    return [byte >> 16, (byte >> 8) & 0xFF, byte & 0xFF]

class EnhancedJSONEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, (Pattern, StripPreset, GlobalPreset, Strip)):
                return o.asdict()
            return super().default(o)

@dataclass
class Pattern:
    name: str = ''
    control_code: int = -1
    preview_classes: str = ''
    numeric_params: dict[str, int] = field(default_factory=dict)
    color_params: dict[str, str] = field(default_factory=dict) # stored as hex strings
    
    def generate_bytes(self) -> list[int]:
        return self.numeric_bytes() + self.color_bytes()
    
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
        
    @classmethod
    def fromdict(cls, pattern_dict):
        match pattern_dict['Name']:
            case 'Off':
                return cls.off()
            case 'Solid':
                return cls.solid(pattern_dict['Color']['Color'], pattern_dict['Numeric']['Brightness'])
            case 'Rainbow':
                return cls.rainbow(pattern_dict['Numeric']['Speed'], pattern_dict['Numeric']['Scale'], pattern_dict['Numeric']['Brightness'])
            case 'Gradient':
                return cls.gradient(pattern_dict['Color']['Start Color'], pattern_dict['Color']['End Color'], pattern_dict['Numeric']['Brightness'])
            case 'Breathing':
                return cls.breathing(pattern_dict['Numeric']['Speed'], pattern_dict['Color']['Color'], pattern_dict['Numeric']['Brightness'])
            case 'Match':
                return QueuingPattern(pattern_dict['Numeric']['Brightness'])
        log_error(f'ERROR: failed to parse pattern from dict with name {pattern_dict["Name"]}')
        return cls()
        
    def property_panel(self, pattern_select: ui.select, update) -> None:
        with ui.element().classes('w-full').bind_visibility_from(pattern_select, target_name='value', value=self.name):
            for param, val in self.numeric_params.items():
                ui.label(param)
                ui.slider(min=0, max=254, step=1, value=val,
                        on_change=update).bind_value(self.numeric_params, param)
            for param, color in self.color_params.items():
                ui.label(param)
                ui.color_input(value=color, preview=True,
                        on_change=update).bind_value(self.color_params, param)
        
    def set_numeric_param(self, param: str, value: int) -> None:
        self.numeric_params[param] = value
        
    def set_color_param(self, param: str, value: str) -> None:
        self.color_params[param] = value
        
    @classmethod
    def off(cls):
        return cls('Off', ser.OFF_CODE, 'border border-gray-700 !bg-none', {}, {})
    
    @classmethod
    def solid(cls, color: str='#DDAA88', brightness: int=255):
        return cls('Solid', ser.SOLID_CODE, f'border-none !bg-[{color}]', {'Brightness': brightness}, {'Color': color})
        
    @classmethod
    def rainbow(cls, speed: int = 20, scale: int = 20, brightness: int=255):
        return cls('Rainbow', ser.RAINBOW_CODE, 'border-none !bg-linear-to-r/decreasing from-violet-700 via-[#00FF00] to-violet-700', {'Speed': speed, 'Scale': scale, 'Brightness': brightness}, {})
    
    @classmethod
    def gradient(cls, start: str='#FFFFFF', end: str='#0009B8', brightness: int=255):
        return cls('Gradient', ser.GRADIENT_CODE, f'border-none !bg-linear-to-r from-[{start}] to-[{end}]', {'Brightness': brightness}, {'Start Color': start, 'End Color': end})
    
    @classmethod
    def breathing(cls, speed: int=80, color: str='#0009B8', brightness: int=255):
        return cls('Breathing', ser.BREATHING_CODE, f'border-none !bg-[{color}]', {'Speed': speed, 'Brightness': brightness}, {'Color': color})

@dataclass
class QueuingPattern(Pattern):
    status: str = 'Queuing soon'

    def __init__(self, brightness: int=255, status='Queuing soon'):
        self.name = 'Match'
        self.status = status
        self.numeric_params = {'Brightness': brightness}
        self.color_params = {'Color': '#FFFFFF'}
        self.preview_classes = f'border-none !bg-[#FFFFFF]'
        self.control_code = ser.SOLID_CODE

    def update(self, color: str, status: str):
        self.preview_classes = f'border-none !bg-[{color}]'
        self.color_params = {'Color': color}
        self.status = status
        if status in ['On deck', 'Now queuing', 'On field']:
            self.control_code = ser.BREATHING_CODE
        else:
            self.control_code = ser.SOLID_CODE

    def numeric_bytes(self) -> list[int]:
        if self.status == 'On field':
            return [100, self.numeric_params['Brightness']]
        elif self.status == 'On deck':
            return [50, self.numeric_params['Brightness']]
        elif self.status == 'Now queuing':
            return [25, self.numeric_params['Brightness']]
        return [self.numeric_params['Brightness']]

@dataclass
class StripPreset(dict):
    name: str
    pattern: Pattern
    
    def asdict(self):
        return {
            'Name': self.name,
            'Pattern': self.pattern.asdict()
        }
    
    @classmethod
    def fromdict(cls, preset: dict):
        return cls(preset['Name'], Pattern.fromdict(preset['Pattern']))

@dataclass
class GlobalPreset:
    name: str
    patterns: list[Pattern]
    
    def asdict(self):
        return {
            'Name': self.name,
            'Patterns': [pattern.asdict() for pattern in self.patterns]
        }
        
    @classmethod
    def fromdict(cls, global_preset: dict):
        return cls(global_preset['Name'], list(map(Pattern.fromdict, global_preset['Patterns'])))

def save_config():
    with open('/home/hammerheads/CaseyLED/pi/config.json', 'w') as f:
        json.dump({'Strips': [strip.asdict() for strip in strips]}, f, cls=EnhancedJSONEncoder, indent=4)

def init_strips():
    try:
        with open('/home/hammerheads/CaseyLED/pi/config.json') as f:
            configs = json.load(f)['Strips']
            for i in range(len(configs)):
                strips.append(Strip.fromdict(configs[i]))
                ser.send_config(i, strips[i].pin, strips[i].length)
    except (KeyError, json.decoder.JSONDecodeError):
        log_error('ERROR: failed to parse config.json')
            
def update_config():
    with open('/home/hammerheads/CaseyLED/pi/config.json') as f:
        configs = json.load(f)['Strips']
        for i in range(min(len(strips), len(configs))):
            strips[i].configure(configs[i])
            ser.send_config(i, strips[i].pin, strips[i].length)
        if len(strips) < len(configs):
            for i in range(len(strips),len(configs)):
                strips.append(Strip.fromdict(configs[i]))
                ser.send_config(i, strips[i].pin, strips[i].length)
        elif len(strips) > len(configs):
            for i in range(len(configs), len(strips)): strips.pop()
    root.refresh()
            
async def save_presets():
    with open('/home/hammerheads/CaseyLED/pi/presets.json', 'w') as f:
        json.dump({name: preset.asdict() for name, preset in presets.items()}, f, indent=4)
        
    for strip in strips:
        await strip.ui_panel.refresh()
        
def load_presets():
    presets.clear()
    try:
        with open('/home/hammerheads/CaseyLED/pi/presets.json') as f:
            presets_json: dict = json.load(f)
            for name, preset in presets_json.items():
                presets[name] = StripPreset.fromdict(preset)
    except (KeyError, json.decoder.JSONDecodeError):
        log_error('ERROR: failed to parse presets.json')

def save_global_presets():
    with open('/home/hammerheads/CaseyLED/pi/global_presets.json', 'w') as f:
        json.dump(global_presets, f, cls=EnhancedJSONEncoder, indent=4)
        
    global_preset_dropdown.refresh()
        
def load_global_presets():
    global_presets.clear()
    try:
        with open('/home/hammerheads/CaseyLED/pi/global_presets.json') as f:
            global_presets_json: dict = json.load(f)
            for name, global_preset in global_presets_json.items():
                global_presets[name] = GlobalPreset.fromdict(global_preset)
    except (KeyError, json.decoder.JSONDecodeError):
        log_error('ERROR: failed to parse global_presets.json')

def save_global_preset(name: str):
    patterns = [Pattern.fromdict(s.pattern.asdict()) for s in strips]
    global_presets[name] = GlobalPreset(name, patterns)
    save_global_presets()

def delete_global_preset(name: str):
    if name in global_presets.keys():
        global_presets.pop(name)
    save_global_presets()
        
def apply_global_preset(preset: GlobalPreset):
    for i in range(min(len(strips), len(preset.patterns))):
        strips[i].set_pattern(preset.patterns[i])
        strips[i].update()
        strips[i].reload_ui()
        
async def generic_delete_popup(thing_to_delete: str) -> bool:
    with ui.dialog() as dialog, ui.card():
        ui.label(f'Are you sure you want to delete this {thing_to_delete}?')
        with ui.row().classes('w-full'):
            ui.button(icon='delete', color='red', on_click=lambda: dialog.submit('Yes'))
            ui.button('Back', on_click=dialog.close)
            
        result = await dialog
        return result == 'Yes'
    
async def add_strip_popup() -> None:
    def _add_strip(name: str, pin: int, length: int):
        strips.append(Strip(name, pin, length))
        save_config()
        dialog.close()
        root.refresh()
        
    with ui.dialog() as dialog, ui.card():
        ui.label('Add strip')
        name_input = ui.input(label='Name', validation=name_validation)
        pin_input = ui.number(label='Pin', format='%d', validation=number_range_validation('Pin', 31))
        length_input = ui.number(label='Length', format='%d', validation=number_range_validation('Length', 255))
        ui.button('Add strip +', on_click=lambda: _add_strip(name_input.value, int(pin_input.value), int(length_input.value)))
    
    await dialog
    
name_validation: dict[str, Callable[[str], bool]] = {
    'Name cannot be empty': lambda val: len(val)>0,
    'Name cannot exceed 60 characters': lambda val: len(val) <= 60
}

def number_range_validation(field: str, max: int) -> dict[str, Callable[[int], bool]]:
    return {
        f'You must enter a {field}': lambda i: i is not None,
        f'{field} must be non-negative': lambda i: i >= 0,
        f'{field} must not exceed {max}': lambda i: i <= max
    }
    
@ui.refreshable
def global_preset_dropdown():
    def _load(preset: GlobalPreset):
        apply_global_preset(preset)
        dropdown.close()
    async def _delete(name: str):
        result = await generic_delete_popup('preset')
        if result:
            dropdown.close()
            delete_global_preset(name)
    with ui.dropdown_button('Load Global Preset', auto_close=False) as dropdown:
        for name, preset in global_presets.items():
            with ui.item().props('square'):
                ui.button(name, on_click=(lambda _,preset=preset: _load(preset))).classes('grow').props('square')
                ui.button(icon='delete', color='red', on_click=(lambda _,preset=preset:_delete(preset.name))).props('square')
    
async def save_global_preset_popup():
    with ui.dialog() as dialog, ui.card():
        ui.label('Save Preset')
        name_input = ui.input(label='Name', validation=name_validation)
        dialog.on('keydown.enter', lambda: dialog.submit(name_input.value))
        ui.button(icon='save', on_click=lambda: dialog.submit(name_input.value))
        
    name = await dialog
    if name is not None:
        save_global_preset(name)

class Strip:
    def __init__(self, name: str, pin: int, length: int, pattern: Pattern = Pattern.off(), preset: StripPreset | None = None) -> None:
        self.name = name
        self.pin = pin
        self.length = length
        self.pattern = pattern
        self._patterns = {'Off': Pattern.off(), 'Solid': Pattern.solid(), 'Rainbow': Pattern.rainbow(), 'Gradient': Pattern.gradient(), 'Breathing': Pattern.breathing(), 'Match': QueuingPattern()}
        self.panel_visible = False
    
    @classmethod
    def fromdict(cls, config: dict):
        return cls(config['Name'], config['Pin'], config['Length'])
        
    def asdict(self) -> dict:
        return {
            'Name': self.name,
            'Pin': self.pin,
            'Length': self.length,
            'Pattern': self.pattern.asdict(),
        }

    def set_pattern(self, pattern: Pattern):
        self.pattern = self._patterns[pattern.name]
        self.pattern.control_code = pattern.control_code
        self.pattern.preview_classes = pattern.preview_classes
        for k in self.pattern.numeric_params.keys():
            self.pattern.numeric_params[k] = pattern.numeric_params[k]
        for k in self.pattern.color_params.keys():
            self.pattern.color_params[k] = pattern.color_params[k]
        self.pattern_select.set_value(self.pattern.name)
        
        
    def configure(self, config: dict):
        self.name = config['Name']
        self.pin = config['Pin']
        self.length = config['Length']
        self.set_pattern(Pattern.fromdict(config['Pattern']))
        
    def _select(self):
        for strip in strips:
            strip.selection_button.props(remove='color=blue-grey-8', add='color=grey-10')
            strip.set_panel_visible(False)
        self.selection_button.props(remove='color=grey-10', add='color=blue-grey-8')
        self.set_panel_visible(True)
        
    @ui.refreshable_method
    def ui_select(self):
        with ui.button(on_click=self._select).classes('w-full p-2').props('color=grey-10 align="left" no-caps') as button:
            ui.label(f'{self.name} Strip')
            ui.card().classes('no-shadow grow h-3 p-0 w-full ' + self.pattern.preview_classes)
        
        self.selection_button = button
            
    async def config_popup(self):
        def _config_strip(name: str, pin: int, length: int):
            self.name = name
            self.pin = pin
            self.length = length
            ser.send_config(strips.index(self), self.pin, self.length)
            dialog.close()
        
        async def _delete_strip():
            if await generic_delete_popup('strip'):
                dialog.close()
                delete_strip(self)
            
        with ui.dialog() as dialog, ui.card().classes(''):
            ui.label('Strip config').classes('text-lg')
            name_input = ui.input(label='Name', value=self.name, validation=name_validation).classes('p-0')
            pin_input = ui.number(label='Pin', value=self.pin, format='%d', validation=number_range_validation('Pin', 31)).classes('p-0')
            length_input = ui.number(label='Length', value=self.length, format='%d', validation=number_range_validation('Length', 255)).classes('p-0 mb-2')
            with ui.row().classes('w-full'):
                ui.button('Configure', on_click=lambda: _config_strip(name_input.value, int(pin_input.value), int(length_input.value)))
                ui.button(icon='delete', color='red', on_click=_delete_strip)
        
        await dialog
    
    async def save_preset_popup(self):
        with ui.dialog() as dialog, ui.card():
            ui.label('Save Preset')
            name_input = ui.input(label='Name', validation=name_validation)
            dialog.on('keydown.enter', lambda: dialog.submit(name_input.value))
            ui.button(icon='save', on_click=lambda: dialog.submit(name_input.value))
            
        name = await dialog
        if name is not None:
            await self.save_preset(name)

    async def save_preset(self, name: str):
        presets[name] = StripPreset(name, Pattern.fromdict(self.pattern.asdict()))
        await save_presets()

    async def delete_preset(self, name: str):
        presets.pop(name)
        await save_presets()
            
    def load_preset(self, preset: StripPreset):
        self.set_pattern(preset.pattern)
        self.update()
        self.ui_panel.refresh()
            
    def reload_ui(self):
        self.ui_panel.refresh() # type: ignore
        self.ui_select.refresh()
        
    def update(self):
        ser.send_control_code(strips.index(self), self.pattern.control_code, self.pattern.generate_bytes())
        self.ui_select.refresh()
            
    def set_panel_visible(self, visible: bool):
        self.panel_visible = visible
        
    def preset_dropdown(self):
        def _load(preset: StripPreset):
            self.load_preset(preset)
            dropdown.close()
        async def _delete(name: str):
            result = await generic_delete_popup('preset')
            if result:
                dropdown.close()
                await self.delete_preset(name)
        with ui.dropdown_button('Load', auto_close=False) as dropdown:
            for name, preset in presets.items():
                with ui.item().classes('p-0').props('square no-shadow'):
                    ui.button(name, on_click=(lambda _,preset=preset: _load(preset))).classes('grow').props('square')
                    ui.button(icon='delete', color='red', on_click=(lambda _,preset=preset:_delete(preset.name))).props('square')
            
    async def _select_pattern(self, name: str):
        self.set_pattern(self._patterns[name])
        self.update()
        await self.ui_select.refresh()
            
    @ui.refreshable_method
    def ui_panel(self):
        with ui.card().classes('w-full').bind_visibility_from(self, 'panel_visible'):
            with ui.row().classes('items-center w-full'):
                ui.label(f"{self.name} Strip").classes('text-lg font-bold grow')
                ui.button(icon='settings', on_click=self.config_popup).tooltip('Configure Strip').classes('justify-self-end')
        
            with ui.row().classes('w-full items-center'):
                ui.label('Preset: ').classes('text-base grow')
                with ui.button_group():
                    self.preset_dropdown()
                    ui.button(icon='save', on_click=self.save_preset_popup).tooltip('Save preset')
            
            self.pattern_select = ui.select(list(self._patterns.keys()), label='Pattern', on_change=lambda e: self._select_pattern(e.value), value=self.pattern.name).classes('w-full')
            
            for name in self._patterns.keys():
                self._patterns[name].property_panel(self.pattern_select, self.update)

            
def delete_strip(strip: Strip):
    id = strips.index(strip)
    strips.remove(strip)
    ser.send_control_code(id, ser.DELETE_STRIP_CODE)
    save_config()
    root.refresh()

def update_queue_lights():
    color, station, status = '#FFFFFF', 1, 'Queuing soon'
    nexus = nextmatch.get_nexus_station()
    #tba = nextmatch.get_tba_station()
    if not isinstance(nexus, str):
        color, station, status = nexus
    else:
        log_warning(nexus)
        # if tba:
        #     color, station = tba
        
    if color == 'red':
        color = '#FF0000'
    elif color == 'blue':
        color = '#0000FF'
        
    for i in range(len(strips)):
        if isinstance(strips[i].pattern, QueuingPattern):
            strips[i].pattern.update(color, status) # type: ignore
            strips[i].update()
            strips[i].reload_ui()

def update_battery_statuses():
    statuses = cam.read_battery_vals()
    for i in range(10):
        if statuses[i] == 'r':
            battery_statuses[i].props(add='color=red', remove='color=green')
        else:
            battery_statuses[i].props(add='color=green', remove='color=red')

def log(txt: str):
    print(txt)
    # _log.push(txt)
def log_serial(txt: str):
    print(txt)
    # _log.push(txt, classes='text-blue')
def log_debug(txt: str):
    print(txt)
    # _log.push(txt, classes='text-grey')
def log_warning(txt: str):
    print(txt)
    # _log.push(txt, classes='text-orange')
def log_error(txt: str):
    print(txt)
    # _log.push(txt, classes='text-red')

strips: list[Strip] = []
presets: dict[str, StripPreset] = {}
global_presets: dict[str, GlobalPreset] = {}
global_preset_select: ui.select
# _log: ui.log
battery_statuses: list[ui.icon] = []

@ui.refreshable
def root():
    global _log
    with ui.tabs() as tabs:
        led_tab = ui.tab('LEDs')
        log_tab = ui.tab('Log')
    
    with ui.tab_panels(tabs, value=led_tab).classes('w-full'):
        with ui.tab_panel(led_tab):
            with ui.row():
                global_preset_dropdown()
                ui.button(icon='save', on_click=save_global_preset_popup).tooltip('Save global preset')
                ui.button('Add Strip +', on_click=add_strip_popup)
                ui.button(icon='refresh', on_click=update_config).tooltip('Refresh Configuration from config.json')
            with ui.row(align_items='stretch', wrap=False).classes('w-full'):
                with ui.column().classes('w-54 gap-0'):
                    for strip in strips:
                        strip.ui_select()
                    with ui.grid(columns=2).classes('mt-10 w-30 place-items-center shadow-3 py-5 rounded-md'):
                        for i in range(10):
                            battery_statuses.append(ui.icon('circle', size='large').props('color=red'))
                ui.element().classes('grow')
                with ui.column().classes('w-65 justify-self-end'):
                    for strip in strips:
                        strip.ui_panel()
        
        # with ui.tab_panel(log_tab):
        #     _log = ui.log().classes('w-full')
        
def update_serial_log():
    lines = ser.read_buffer() or []
    for line in lines:
        log_serial(line)

async def cam_init():
    await run.io_bound(cam.init)

@app.on_page_exception
def timeout_error_page(exception: Exception) -> None:
    if not isinstance(exception, ser.serial.SerialTimeoutException):
        raise exception
    print('Timeout error!')
    with ui.column().classes('absolute-center items-center gap-8'):
        ui.icon('sym_o_timer', size='xl')
        ui.label(f'{exception}').classes('text-2xl')
        ui.code(traceback.format_exc(chain=False))

def main():
    load_presets()
    load_global_presets()
    init_strips()
    root()
    app.timer(10, update_queue_lights)
    # app.timer(1, update_serial_log)
    app.timer(5, update_battery_statuses)
    ui.run(title='CaseyLEDs', dark=True, favicon='🌟', reload=False)
    
def on_exit():
    pass
    # cam.close()
    # ser.close()

if __name__ in {'__main__', '__mp_main__'}:
    try:
        main()
    finally:
        on_exit()