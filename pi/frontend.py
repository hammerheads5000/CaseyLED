from nicegui import ui
import nextmatch
import serialcontrol as ser
import json

#ID_DICT = {0: 'Left', 1: 'Right', 2: 'Shelf', 3: 'Workbench'}
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

config = get_config()
    
def update_config():
    global config
    config = get_config()

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

def strip_section(strip_id: int):
    global config
    def change_pattern(pattern):
        match pattern:
            case ser.OFF_CODE:
                show_brightness(False)
                show_color(False)
                show_gradient(False)
            case ser.RAINBOW_CODE:
                show_brightness(True)
                show_color(False)
                show_gradient(False)
            case ser.SOLID_CODE:
                show_brightness(True)
                show_color(True)
                show_gradient(False)
            case ser.GRADIENT_CODE:
                show_brightness(True)
                show_color(False)
                show_gradient(True)
    
    def update():
        match pattern_toggle.value:
            case ser.OFF_CODE:
                ser.send_control_code(strip_id, ser.OFF_CODE)
            case ser.RAINBOW_CODE:
                ser.send_control_code(strip_id, ser.RAINBOW_CODE)
                ser.send_control_code(strip_id, ser.BRIGHTNESS_CODE, brightness.value)
            case ser.SOLID_CODE:
                ser.send_control_code(strip_id, ser.SOLID_CODE, hex_color_to_list(color.value))
                ser.send_control_code(strip_id, ser.BRIGHTNESS_CODE, brightness.value)
            case ser.GRADIENT_CODE:
                ser.send_control_code(strip_id, ser.GRADIENT_CODE, hex_color_to_list(startcolor.value) + hex_color_to_list(endcolor.value))
                ser.send_control_code(strip_id, ser.BRIGHTNESS_CODE, brightness.value)
        ui.notify(f'{config[str(strip_id)]['Name']} Strip updated')
    
    def show_brightness(should_show):
        brightness_label.set_visibility(should_show)
        brightness.set_visibility(should_show)
        
    def show_color(should_show):
        color_label.set_visibility(should_show)
        color.set_visibility(should_show)
        
    def show_gradient(should_show):
        startcolor_label.set_visibility(should_show)
        startcolor.set_visibility(should_show)
        endcolor_label.set_visibility(should_show)
        endcolor.set_visibility(should_show)

    with ui.card(), ui.expansion().classes('w-full') as expansion:
        config_dialog = config_popup(strip_id)

        with expansion.add_slot('header'), ui.row().classes('items-center justify-between w-full'):
            ui.label(f"{config[str(strip_id)]['Name']} Strip").classes('text-lg font-bold')
            ui.button(icon='settings', on_click=lambda: config_dialog.open())
        pattern_toggle = ui.toggle(PATTERN_DICT, on_change=lambda event: change_pattern(event.value), value=ser.OFF_CODE)
        
        brightness_label = ui.label('Brightness:')
        brightness = ui.slider(min=0, max=255, step = 1, value = 255)
        
        color_label = ui.label('Color:')
        color = ui.color_input(value="#DDAA88", preview=True)

        startcolor_label = ui.label('Start Color:')
        startcolor = ui.color_input(value="#FFFFFF", preview=True)
        
        endcolor_label = ui.label('End Color:')
        endcolor = ui.color_input(value="#0009B8", preview=True)
        
        ui.button('Update', on_click=update)
        
        change_pattern(pattern_toggle.value)
    
def root():
    with ui.row():
        ui.button('Add Strip +', on_click=config_popup)
        ui.button(icon='refresh', on_click=update_config)
    for strip_id in config.keys():
        strip_section(int(strip_id))
    
def main():
    ui.run(root, title='CaseyLED Controller', dark=True)

if __name__ in {'__main__', '__mp_main__'}:
    main()
