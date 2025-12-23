from nicegui import app, ui
import nextmatch
import serialcontrol as ser
import json

PATTERN_DICT = {ser.OFF_CODE: 'Off', ser.RAINBOW_CODE: 'Rainbow', ser.SOLID_CODE: 'Solid', ser.GRADIENT_CODE: 'Gradient', ser.BREATHING_CODE: 'Breathing'}    

def on_press(key):
    print(key, 'pressed')
    if key == keyboard.Key.f8:
        apply_global_preset('Default')
def on_release(key):
    pass
listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

def hex_color_to_list(hex) -> list[int]:
    byte = int(hex[1:], 16)
    return [byte >> 16, (byte >> 8) & 0xFF, byte & 0xFF]

def save_config():
    global configs
    with open('config.json', 'w') as f:
        json.dump({'Strips': configs}, f, indent=4)
        
def get_config() -> list[dict]:
    with open('config.json') as f:
        return json.load(f)['Strips']
    
def save_presets():
    global presets
    with open('presets.json', 'w') as f:
        json.dump(presets, f, indent=4)

    for i in range(len(strip_panels)):
        strip_panels[i].update_preset_select()
            
def save_preset(name, preset):
        
    modified_panels = [panel.preset_modified() for panel in strip_panels]
    presets[name] = preset
    
    for i in range(len(strip_panels)):
        strip_panels[i].update_preset_select()
        if not modified_panels[i]:
            strip_panels[i].load_preset()
    
def get_presets() -> dict[str,dict]:
    with open('presets.json') as f:
        return json.load(f)
    
async def delete_preset(preset):
    global presets
    with ui.dialog() as delete_dialog, ui.card():
        ui.label('Are you sure you want to delete this preset?')
        ui.button('Delete', on_click=lambda: delete_dialog.submit('Yes'), color='red')
        
    result = await delete_dialog
    if result is None:
        return
    
    if preset == 'Default':
        ui.notify("You can't delete the default preset")
        return
    if preset in presets.keys():
        presets.pop(preset)
    for panel in strip_panels:
        if panel.preset_select.value == preset:
            panel.apply_preset('Default')
    save_presets()
    
def save_global_presets():
    with open('global_presets.json', 'w') as f:
        json.dump(global_presets, f, indent=4)
            
def save_global_preset(name):
    preset = [
        panel.generate_preset() for panel in strip_panels
        ]
    global_presets[name] = preset
    global_preset_select.set_value(name)
    
def get_global_presets() -> dict[str,list[dict]]:
    with open('global_presets.json') as f:
        return json.load(f)
    
async def delete_global_preset(preset):
    global global_presets
    with ui.dialog() as delete_dialog, ui.card():
        ui.label('Are you sure you want to delete this preset?')
        ui.button('Delete', on_click=lambda: delete_dialog.submit('Yes'), color='red')
        
    result = await delete_dialog
    if result is None:
        return
    
    if preset == 'Default':
        ui.notify("You can't delete the default preset")
        return
    if preset in global_presets.keys():
        global_presets.pop(preset)
    save_global_presets()
    
def apply_global_preset(name):
    for i in range(min(len(strip_panels),len(global_presets[name]))):
        strip_panels[i].apply_preset_values(global_presets[name][i])
        strip_panels[i].update()
    
async def save_global_preset_popup():
    with ui.dialog() as dialog, ui.card():
        ui.label('Save preset as:')
        name_input = ui.input(label='Preset Name', value=global_preset_select.value or 'Default')
        dialog.on('keydown.enter', lambda: dialog.submit(name_input.value))
        ui.button(icon='save', on_click=lambda: dialog.submit(name_input.value))
    
    name = await dialog
    
    if name is not None:
        save_global_preset(name)
    save_global_presets()

def update_config():
    global configs
    configs = get_config()
    root.refresh()

async def config_strip(strip_id: int, pin: int, name: str, length: int, reversed: bool):
    global configs
    if strip_id < len(configs):
        configs[strip_id]['Name'] = name
        configs[strip_id]['Pin'] = pin
        configs[strip_id]['Length'] = length
        configs[strip_id]['Reversed'] = reversed
    else:
        configs.append({
            'Name': name,
            'Pin': pin,
            'Length': length,
            'Reversed': reversed
        })
    save_config()
    
    panel_states = []
    for panel in strip_panels:
        panel_states.append(panel.get_state())
    
    ser.send_config(strip_id, reversed, pin, length)
    
    await root.refresh()
    panel_states.append(strip_panels[-1].get_state())
    for strip_id in range(len(strip_panels)):
        strip_panels[strip_id].load_from_state(panel_states[strip_id])
        

async def delete_strip(strip_id: int):
    global configs
    configs.pop(strip_id)
    save_config()
    
    panel_states = [panel.get_state() for panel in strip_panels]
        
    panel_states.pop(strip_id)
    
    ser.send_control_code(strip_id, ser.DELETE_STRIP_CODE)
    
    await root.refresh()
    
    for strip_id in range(len(strip_panels)):
        strip_panels[strip_id].load_from_state(panel_states[strip_id])
    
class StripPanel:
    def __init__(self, strip_id: int, pattern_displays: list[ui.card]):
        global configs, presets
        self.name = configs[strip_id]['Name']
        self.current_pattern_classes = 'border border-gray-700 bg-none'
        self.strip_id = strip_id
        self.pattern_display = pattern_displays[strip_id]

        with ui.card().classes('w-full') as card:
            self.card = card
            self.config_dialog = config_popup(strip_id)

            with ui.row().classes('items-center w-full'):
                ui.label(f"{self.name} Strip").classes('text-lg font-bold grow')
                ui.button(icon='settings', on_click=lambda: self.config_dialog.open()).tooltip('Configure Strip').classes('justify-self-end')
                
            with ui.row().classes('w-full items-center'):
                self.preset_select = ui.select(list(presets.keys()), label='Preset', value='Default', on_change=self.load_preset).classes('grow')
                self.preset_save = ui.button(icon='save', on_click=self.save_preset_popup).tooltip('Save preset')
                ui.button(icon='delete', on_click=lambda: delete_preset(self.preset_select.value), color='red').tooltip('Delete preset')

            self.pattern_select = ui.select(PATTERN_DICT, label='Pattern', on_change=self.update_pattern_ui, value=ser.OFF_CODE).classes('w-full')
            
            self.brightness_label = ui.label('Brightness:')
            self.brightness = ui.slider(min=0, max=255, step = 1, value = 255)
            
            self.color_label = ui.label('Color:')
            self.color = ui.color_input(value="#DDAA88", preview=True)

            self.startcolor_label = ui.label('Start Color:')
            self.startcolor = ui.color_input(value="#FFFFFF", preview=True)
            
            self.endcolor_label = ui.label('End Color:')
            self.endcolor = ui.color_input(value="#0009B8", preview=True)
            
            self.speed_label = ui.label('Speed:')
            self.speed = ui.slider(min=1, max=255, step = 1, value = 80)
            
            ui.button('Update', on_click=self.update).tooltip('Apply pattern to strip')
            # self.load_preset()
            
    def update_preset_select(self):
        self.preset_select.set_options(list(presets.keys()))
    
    def apply_preset(self, preset_name):
        self.update_preset_select()
        self.preset_select.set_value(preset_name)
        self.load_preset()
            
    def update_pattern_ui(self):
        self.show_brightness(True)
        self.show_color(False)
        self.show_gradient(False)
        self.show_speed(False)
        match self.pattern_select.value:
            case ser.OFF_CODE:
                self.show_brightness(False)
            case ser.RAINBOW_CODE:
                self.show_speed(True)
            case ser.SOLID_CODE:
                self.show_color(True)
            case ser.GRADIENT_CODE:
                self.show_gradient(True)
            case ser.BREATHING_CODE:
                self.show_color(True)
                self.show_speed(True)
                
    def update(self):
        match self.pattern_select.value:
            case ser.OFF_CODE:
                ser.send_control_code(self.strip_id, ser.OFF_CODE)
                self.pattern_display.classes(remove=self.current_pattern_classes, add='border border-gray-700 !bg-none')
                self.current_pattern_classes = 'border border-gray-700 !bg-none'
            case ser.RAINBOW_CODE:
                ser.send_control_code(self.strip_id, ser.RAINBOW_CODE, self.speed.value)
                self.pattern_display.classes(remove=self.current_pattern_classes, add='border-none !bg-linear-to-r/decreasing from-violet-700 via-[#00FF00] to-violet-700')
                self.current_pattern_classes = 'border-none !bg-linear-to-r/decreasing from-violet-700 via-[#00FF00] to-violet-700'
            case ser.SOLID_CODE:
                ser.send_control_code(self.strip_id, ser.SOLID_CODE, hex_color_to_list(self.color.value))
                self.pattern_display.classes(remove=self.current_pattern_classes, add=f'border-none !bg-[{self.color.value}]')
                self.current_pattern_classes = f'border-none !bg-[{self.color.value}]'
            case ser.GRADIENT_CODE:
                ser.send_control_code(self.strip_id, ser.GRADIENT_CODE, hex_color_to_list(self.startcolor.value) + hex_color_to_list(self.endcolor.value))
                self.pattern_display.classes(remove=self.current_pattern_classes, add=f'border-none !bg-linear-to-r from-[{self.startcolor.value}] to-[{self.endcolor.value}]')
                self.current_pattern_classes = f'border-none !bg-linear-to-r from-[{self.startcolor.value}] to-[{self.endcolor.value}]'
            case ser.BREATHING_CODE:
                ser.send_control_code(self.strip_id, ser.BREATHING_CODE, [self.speed.value]+hex_color_to_list(self.color.value))
                self.pattern_display.classes(remove=self.current_pattern_classes, add=f'border-none !bg-[{self.color.value}]')
                self.current_pattern_classes = f'border-none !bg-[{self.color.value}]'
                
        ser.send_control_code(self.strip_id, ser.BRIGHTNESS_CODE, self.brightness.value)

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
        
    def show_speed(self, should_show: bool):
        self.speed_label.set_visibility(should_show)
        self.speed.set_visibility(should_show)

    def set_visibility(self, should_show: bool):
        self.card.set_visibility(should_show)
        self.update_pattern_ui()

    def load_from_state(self, panel_state: dict):
        self.pattern_select.set_value(panel_state['Pattern'])
        self.brightness.set_value(panel_state['Brightness'])
        self.color.set_value(panel_state['Color'])
        self.startcolor.set_value(panel_state['Start Color'])
        self.endcolor.set_value(panel_state['End Color'])
        self.speed.set_value(panel_state['Speed'])
        self.set_visibility(panel_state['Visible'])
        self.update_pattern_ui()
        self.update()
        
    def get_state(self):
        return {
                'Preset': self.preset_select.value,
                'Pattern': self.pattern_select.value,
                'Brightness': self.brightness.value,
                'Color': self.color.value,
                'Start Color': self.startcolor.value,
                'End Color': self.endcolor.value,
                'Speed': self.speed.value,
                'Visible': self.card.visible
        }
        
    def generate_preset(self):
        return {
            'Pattern': self.pattern_select.value,
            'Brightness': self.brightness.value,
            'Color': self.color.value,
            'Start Color': self.startcolor.value,
            'End Color': self.endcolor.value,
            'Speed': self.speed.value
        }
        
    async def save_preset_popup(self):
        with ui.dialog() as dialog, ui.card():
            ui.label('Save preset as:')
            name_input = ui.input(label='Preset Name', value=self.preset_select.value or 'Default')
            dialog.on('keydown.enter', lambda: dialog.submit(name_input.value))
            ui.button(icon='save', on_click=lambda: dialog.submit(name_input.value))
        
        name = await dialog
        
        if name is not None:
            save_preset(name, self.generate_preset())
            self.apply_preset(name)
        
    def preset_modified(self):
        return self.generate_preset() != presets[self.preset_select.value or 'Default']
        
    def load_preset(self):
        preset = presets[self.preset_select.value or 'Default']
        self.apply_preset_values(preset)
        
    def apply_preset_values(self, preset):
        self.pattern_select.set_value(preset['Pattern'])
        self.brightness.set_value(preset['Brightness'])
        self.color.set_value(preset['Color'])
        self.startcolor.set_value(preset['Start Color'])
        self.endcolor.set_value(preset['End Color'])
        self.speed.set_value(preset['Speed'])
        self.update()

def config_popup(strip_id=-1) -> ui.dialog:
    async def _config(strip_id: int, pin: int, name: str, length: int, reversed: bool):
        await config_strip(strip_id, pin, name, length, reversed)
        dialog.close()
    async def _delete():
        with ui.dialog() as delete_dialog, ui.card():
            ui.label('Are you sure you want to delete this strip?')
            ui.button('Delete Strip', on_click=lambda: delete_dialog.submit('Yes'), color='red')
            
        result = await delete_dialog
        if result is not None:
            await delete_strip(strip_id)
            dialog.close()
        
    with ui.dialog() as dialog, ui.card():
        title = ui.label()
        name_input = ui.input(label='Name')
        pin_input = ui.number(label='Pin', format='%d')
        length_input = ui.number(label='Length', format='%d')
        reversed_input = ui.checkbox('Reversed')
        with ui.row():
            ui.button('Configure strip', on_click=lambda: _config(strip_id, int(pin_input.value), name_input.value, int(length_input.value), reversed_input.value))
            delete_button = ui.button(icon='delete_forever', on_click=_delete, color='red')
        if strip_id == -1:
            title.set_text('Add Strip')
            strip_id = len(configs)
            delete_button.set_visibility(False)
        else:
            title.set_text('Configure Strip')
            pin_input.set_value(configs[strip_id]['Pin'])
            length_input.set_value(configs[strip_id]['Length'])
            name_input.set_value(configs[strip_id]['Name'])
            reversed_input.set_value(configs[strip_id]['Reversed'])
    return dialog

def strip_selection_card(strip_id, strip_buttons: list[ui.button]) -> ui.card:
    current_pattern_display = None
    with ui.button(on_click=lambda e: select_strip(strip_id, strip_buttons)).classes('w-full !bg-neutral-900 p-2').props('align="left" no-caps') as button:
        ui.label(f"{configs[strip_id]['Name']} Strip")
        current_pattern_display = ui.card().classes('no-shadow border border-gray-700 bg-none grow h-3 p-0 w-full')
        strip_buttons.append(button)
    
    return current_pattern_display

def select_strip(strip_id: int, strip_buttons: list[ui.button]):
    for button in strip_buttons:
        button.classes(remove='!bg-neutral-700', add='!bg-neutral-900')
        
    strip_buttons[strip_id].classes(remove='!bg-neutral-900', add='!bg-neutral-700')
         
    for panel in strip_panels:
        panel.set_visibility(False)
    
    strip_panels[strip_id].set_visibility(True)
    
@ui.refreshable
def root():
    global strip_panels, global_preset_select, global_presets
    with ui.row():
        global_preset_select = ui.select(list(global_presets.keys()), label='Global Preset', value='Default', on_change=lambda e: apply_global_preset(e.value)).classes('grow')
        global_preset_save = ui.button(icon='save', on_click=save_global_preset_popup).tooltip('Save global preset')
        ui.button(icon='delete', on_click=lambda: delete_global_preset(global_preset_select.value), color='red').tooltip('Delete preset')
        ui.button('Add Strip +', on_click=config_popup)
        ui.button(icon='refresh', on_click=update_config).tooltip('Refresh Configuration from config.json')
    strip_buttons: list[ui.button] = []
    pattern_displays: list[ui.card] = []
    strip_panels = []
    with ui.row(align_items='stretch', wrap=False).classes('w-full'):
        with ui.column().classes('w-54 gap-0'):
            for strip_id in range(len(configs)):
                pattern_displays.append(strip_selection_card(strip_id, strip_buttons))
        ui.element().classes('grow')
        with ui.column().classes('w-80 justify-self-end'):
            for strip_id in range(len(configs)):
                strip_panels.append(StripPanel(strip_id, pattern_displays))
                strip_panels[-1].set_visibility(False)
    for panel in strip_panels:
        panel.update_preset_select()
        if not panel.preset_modified():
            panel.load_preset()
    
def main():
    root()
    ui.run(title='CaseyLEDs', dark=True, favicon='🌟')

configs = get_config()
presets = get_presets()
global_presets = get_global_presets()
current_patterns = [ser.OFF_CODE]*len(configs)
strip_panels: list[StripPanel] = []

if __name__ in {'__main__', '__mp_main__'}:
    main()
