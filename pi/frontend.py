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

def strip_card(strip_id, strip_buttons: list[ui.button]) -> ui.card:
    current_pattern_display = None
    with ui.button(on_click=lambda e: select_strip(e.sender, strip_buttons)).classes('w-full !bg-gray-900') as button:
        ui.label(f"{config[str(strip_id)]['Name']} Strip").classes('text-lg font-bold')
        current_pattern_display = ui.card().classes('no-shadow border border-gray-700 bg-none grow h-3 p-0')
        strip_buttons.append(button)
    
    return current_pattern_display

def select_strip(sender: ui.element, strip_buttons: list[ui.button]):
    for button in strip_buttons:
        button.classes(remove='!bg-gray-900', add='!bg-neutral-900')
        
    sender.classes(remove='!bg-neutral-900', add='!bg-gray-900')

def strip_panel(strip_id: int):
    global config
    current_pattern_classes = 'border border-gray-700 bg-none'

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
        nonlocal current_pattern_classes
        match pattern_toggle.value:
            case ser.OFF_CODE:
                ser.send_control_code(strip_id, ser.OFF_CODE)
                current_pattern_label.set_text('Off')
                current_pattern_display.classes(remove=current_pattern_classes, add='border border-gray-700 !bg-none')
                current_pattern_classes = 'border border-gray-700 !bg-none'
            case ser.RAINBOW_CODE:
                ser.send_control_code(strip_id, ser.RAINBOW_CODE)
                ser.send_control_code(strip_id, ser.BRIGHTNESS_CODE, brightness.value)
                current_pattern_label.set_text('Rainbow')
                current_pattern_display.classes(remove=current_pattern_classes, add='border-none !bg-linear-to-r/decreasing from-violet-700 via-[#00FF00] to-violet-700')
                current_pattern_classes = 'border-none !bg-linear-to-r/decreasing from-violet-700 via-[#00FF00] to-violet-700'
            case ser.SOLID_CODE:
                ser.send_control_code(strip_id, ser.SOLID_CODE, hex_color_to_list(color.value))
                ser.send_control_code(strip_id, ser.BRIGHTNESS_CODE, brightness.value)
                current_pattern_label.set_text('Solid')
                current_pattern_display.classes(remove=current_pattern_classes, add=f'border-none !bg-[{color.value}]')
                current_pattern_classes = f'border-none !bg-[{color.value}]'
            case ser.GRADIENT_CODE:
                ser.send_control_code(strip_id, ser.GRADIENT_CODE, hex_color_to_list(startcolor.value) + hex_color_to_list(endcolor.value))
                ser.send_control_code(strip_id, ser.BRIGHTNESS_CODE, brightness.value)
                current_pattern_label.set_text('Gradient')
                current_pattern_display.classes(remove=current_pattern_classes, add=f'border-none !bg-linear-to-r from-[{startcolor.value}] to-[{endcolor.value}]')
                current_pattern_classes = f'border-none !bg-linear-to-r from-[{startcolor.value}] to-[{endcolor.value}]'
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

    with ui.card().classes('w-full'), ui.expansion(group='strips').classes('w-full') as expansion:
        config_dialog = config_popup(strip_id)

        with expansion.add_slot('header'), ui.row().classes('items-center w-full'):
            ui.label(f"{config[str(strip_id)]['Name']} Strip").classes('text-lg font-bold grow')
            current_pattern_label = ui.label('Off').classes('italic justify-self-end')
            ui.button(icon='settings', on_click=lambda: config_dialog.open()).tooltip('Configure Strip').classes('justify-self-end')
            current_pattern_display = ui.card().classes('no-shadow border border-gray-700 bg-none w-full h-3 p-0')
            
        pattern_toggle = ui.toggle(PATTERN_DICT, on_change=lambda event: change_pattern(event.value), value=ser.OFF_CODE)
        
        brightness_label = ui.label('Brightness:')
        brightness = ui.slider(min=0, max=255, step = 1, value = 255)
        
        color_label = ui.label('Color:')
        color = ui.color_input(value="#DDAA88", preview=True)

        startcolor_label = ui.label('Start Color:')
        startcolor = ui.color_input(value="#FFFFFF", preview=True)
        
        endcolor_label = ui.label('End Color:')
        endcolor = ui.color_input(value="#0009B8", preview=True)
        
        ui.button('Update', on_click=update).tooltip('Apply pattern to strip')
        
        change_pattern(pattern_toggle.value)
    
@ui.refreshable
def root() -> None:
    with ui.row():
        ui.button('Add Strip +', on_click=config_popup)
        ui.button(icon='refresh', on_click=update_config).tooltip('Refresh Configuration from config.json')
    strip_buttons = []
    current_pattern_displays = []
    for strip_id in config.keys():
        current_pattern_displays.append(strip_card(strip_id, strip_buttons))
        strip_panel(int(strip_id))
    
def main():
    with ui.button_group().classes('column'):
        with ui.button():
            ui.checkbox()
        ui.button('no')
        ui.button('why')
        ui.button('why')
    root()
    ui.run(title='CaseyLED Controller', native=True, dark=True, favicon='🌟', window_size=(600, 800))

config = get_config()

if __name__ in {'__main__', '__mp_main__'}:
    main()
