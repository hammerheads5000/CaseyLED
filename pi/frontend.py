from nicegui import app, ui
import nextmatch
import serialcontrol as ser
import json

PATTERN_DICT = {ser.OFF_CODE: 'Off', ser.RAINBOW_CODE: 'Rainbow', ser.SOLID_CODE: 'Solid', ser.GRADIENT_CODE: 'Gradient'}    

def hex_color_to_list(hex) -> list[int]:
    byte = int(hex[1:], 16)
    return [byte >> 16, (byte >> 8) & 0xFF, byte & 0xFF]

def save_config():
    global config
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)
        
def get_config() -> dict[str, dict]:
    with open('config.json') as f:
        return json.load(f)
    
def update_config():
    global config
    config = get_config()
    root.refresh()

def config_strip(strip_id: int, pin: int, name: str, length: int, reversed: bool):
    global config
    if str(strip_id) in config.keys():
        config[str(strip_id)]['Name'] = name
        config[str(strip_id)]['Pin'] = pin
        config[str(strip_id)]['Length'] = length
        config[str(strip_id)]['Reversed'] = reversed
    else:
        config[str(strip_id)] = {
            'Name': name,
            'Pin': pin,
            'Length': length,
            'Reversed': reversed
        }
    save_config()
    root.refresh()
    
class StripPanel:
    def __init__(self, strip_id: int, pattern_displays: list[ui.card]):
        global config
        self.name = config[str(strip_id)]['Name']
        self.current_pattern_classes = 'border border-gray-700 bg-none'
        self.strip_id = strip_id
        self.pattern_display = pattern_displays[strip_id]

        with ui.card().classes('w-full') as card:
            self.card = card
            self.config_dialog = config_popup(strip_id)

            with ui.row().classes('items-center w-full'):
                ui.label(f"{self.name} Strip").classes('text-lg font-bold grow')
                ui.button(icon='settings', on_click=lambda: self.config_dialog.open()).tooltip('Configure Strip').classes('justify-self-end')
                
            self.pattern_toggle = ui.toggle(PATTERN_DICT, on_change=self.update_pattern_ui, value=ser.OFF_CODE)
            
            self.brightness_label = ui.label('Brightness:')
            self.brightness = ui.slider(min=0, max=255, step = 1, value = 255)
            
            self.color_label = ui.label('Color:')
            self.color = ui.color_input(value="#DDAA88", preview=True)

            self.startcolor_label = ui.label('Start Color:')
            self.startcolor = ui.color_input(value="#FFFFFF", preview=True)
            
            self.endcolor_label = ui.label('End Color:')
            self.endcolor = ui.color_input(value="#0009B8", preview=True)
            
            ui.button('Update', on_click=self.update).tooltip('Apply pattern to strip')      
            
    def update_pattern_ui(self):
        match self.pattern_toggle.value:
            case ser.OFF_CODE:
                self.show_brightness(False)
                self.show_color(False)
                self.show_gradient(False)
            case ser.RAINBOW_CODE:
                self.show_brightness(True)
                self.show_color(False)
                self.show_gradient(False)
            case ser.SOLID_CODE:
                self.show_brightness(True)
                self.show_color(True)
                self.show_gradient(False)
            case ser.GRADIENT_CODE:
                self.show_brightness(True)
                self.show_color(False)
                self.show_gradient(True)
                
    def update(self):
        match self.pattern_toggle.value:
            case ser.OFF_CODE:
                ser.send_control_code(self.strip_id, ser.OFF_CODE)
                self.pattern_display.classes(remove=self.current_pattern_classes, add='border border-gray-700 !bg-none')
                self.current_pattern_classes = 'border border-gray-700 !bg-none'
            case ser.RAINBOW_CODE:
                ser.send_control_code(self.strip_id, ser.RAINBOW_CODE)
                ser.send_control_code(self.strip_id, ser.BRIGHTNESS_CODE, self.brightness.value)
                self.pattern_display.classes(remove=self.current_pattern_classes, add='border-none !bg-linear-to-r/decreasing from-violet-700 via-[#00FF00] to-violet-700')
                self.current_pattern_classes = 'border-none !bg-linear-to-r/decreasing from-violet-700 via-[#00FF00] to-violet-700'
            case ser.SOLID_CODE:
                ser.send_control_code(self.strip_id, ser.SOLID_CODE, hex_color_to_list(self.color.value))
                ser.send_control_code(self.strip_id, ser.BRIGHTNESS_CODE, self.brightness.value)
                self.pattern_display.classes(remove=self.current_pattern_classes, add=f'border-none !bg-[{self.color.value}]')
                self.current_pattern_classes = f'border-none !bg-[{self.color.value}]'
            case ser.GRADIENT_CODE:
                ser.send_control_code(self.strip_id, ser.GRADIENT_CODE, hex_color_to_list(self.startcolor.value) + hex_color_to_list(self.endcolor.value))
                ser.send_control_code(self.strip_id, ser.BRIGHTNESS_CODE, self.brightness.value)
                self.pattern_display.classes(remove=self.current_pattern_classes, add=f'border-none !bg-linear-to-r from-[{self.startcolor.value}] to-[{self.endcolor.value}]')
                self.current_pattern_classes = f'border-none !bg-linear-to-r from-[{self.startcolor.value}] to-[{self.endcolor.value}]'

    def show_brightness(self, should_show: bool):
        self.brightness_label.set_visibility(should_show)
        self.brightness.set_visibility(should_show)
            
    def show_color(self, should_show: bool):
        self.color_label.set_visibility(should_show)
        self.color.set_visibility(should_show)
        
    def show_gradient(self, should_show: bool):
        self.startcolor_label.set_visibility(should_show)
        self.startcolor.set_visibility(should_show)
        self.endcolor_label.set_visibility(should_show)
        self.endcolor.set_visibility(should_show)

    def set_visibility(self, should_show: bool):
        self.card.set_visibility(should_show)
        self.update_pattern_ui()

def config_popup(strip_id=-1) -> ui.dialog:
    def _config(strip_id: int, pin: int, name: str, length: int, reversed: bool):
        config_strip(strip_id, pin, name, length, reversed)
        dialog.close()
    with ui.dialog() as dialog, ui.card():
        title = ui.label()
        name_input = ui.input(label='Name')
        pin_input = ui.number(label='Pin', format='%d')
        length_input = ui.number(label='Length', format='%d')
        reversed_input = ui.checkbox('Reversed')
        if strip_id == -1:
            title.set_text('Add Strip')
            strip_id = len(config.keys())
        else:
            title.set_text('Configure Strip')
            pin_input.set_value(config[str(strip_id)]['Pin'])
            length_input.set_value(config[str(strip_id)]['Length'])
            name_input.set_value(config[str(strip_id)]['Name'])
            reversed_input.set_value(config[str(strip_id)]['Reversed'])
        ui.button('Configure strip', on_click=lambda: _config(strip_id, int(pin_input.value), name_input.value, int(length_input.value), reversed_input.value))
    return dialog

def strip_selection_card(strip_id, strip_buttons: list[ui.button], strip_panels: list[StripPanel]) -> ui.card:
    current_pattern_display = None
    with ui.button(on_click=lambda e: select_strip(strip_id, strip_buttons, strip_panels)).classes('w-full !bg-neutral-900 justify-start') as button:
        ui.label(f"{config[str(strip_id)]['Name']} Strip").classes('text-lg')
        current_pattern_display = ui.card().classes('no-shadow border border-gray-700 bg-none grow h-3 p-0 w-full')
        strip_buttons.append(button)
    
    return current_pattern_display

def select_strip(strip_id: int, strip_buttons: list[ui.button], strip_panels: list[StripPanel]):
    for button in strip_buttons:
        button.classes(remove='!bg-neutral-700', add='!bg-neutral-900')
        
    strip_buttons[strip_id].classes(remove='!bg-neutral-900', add='!bg-neutral-700')
         
    for panel in strip_panels:
        panel.set_visibility(False)
    
    strip_panels[strip_id].set_visibility(True)
    
@ui.refreshable
def root() -> None:
    with ui.row():
        ui.button('Add Strip +', on_click=config_popup)
        ui.button(icon='refresh', on_click=update_config).tooltip('Refresh Configuration from config.json')
    strip_buttons: list[ui.button] = []
    pattern_displays: list[ui.card] = []
    strip_panels: list[StripPanel] = []
    with ui.row(align_items='stretch').classes('w-full'):
        with ui.column().classes('w-[25%] gap-0'):
            for strip_id in config.keys():
                pattern_displays.append(strip_selection_card(int(strip_id), strip_buttons, strip_panels))
        ui.card().classes('grow')
        with ui.column().classes('w-[30%] justify-self-end'):
            for strip_id in config.keys():
                strip_panels.append(StripPanel(int(strip_id), pattern_displays))
                strip_panels[-1].set_visibility(False)
    
def main():
    root()
    ui.run(title='CaseyLED Controller', native=True, dark=True, favicon='🌟', window_size=(1280, 720))

config = get_config()
current_patterns = [ser.OFF_CODE for _ in config.keys()]

if __name__ in {'__main__', '__mp_main__'}:
    main()
