from nicegui import ui
import nextmatch
import serialcontrol as ser

ID_DICT = {ser.LEFT_ID: 'Left', ser.RIGHT_ID: 'Right', ser.SHELF_ID: 'Shelf', ser.WORKBENCH_ID: 'Workbench'}
PATTERN_DICT = {ser.OFF_CODE: 'Off', ser.RAINBOW_CODE: 'Rainbow', ser.SOLID_CODE: 'Solid', ser.GRADIENT_CODE: 'Gradient'}    

def hex_color_to_list(hex):
    byte = int(hex[1:], 16)
    return [byte >> 16, (byte >> 8) & 0xFF, byte & 0xFF]

def strip_section(id):
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
                ser.send_control_code(id, ser.OFF_CODE)
            case ser.RAINBOW_CODE:
                ser.send_control_code(id, ser.RAINBOW_CODE)
                ser.send_control_code(id, ser.BRIGHTNESS_CODE, brightness.value)
            case ser.SOLID_CODE:
                print(color)
                ser.send_control_code(id, ser.SOLID_CODE, hex_color_to_list(color.value))
                ser.send_control_code(id, ser.BRIGHTNESS_CODE, brightness.value)
            case ser.GRADIENT_CODE:
                ser.send_control_code(id, ser.GRADIENT_CODE, hex_color_to_list(startcolor.value) + hex_color_to_list(endcolor.value))
                ser.send_control_code(id, ser.BRIGHTNESS_CODE, brightness.value)
        ui.notify(f'{ID_DICT[id]} Strip updated')
    
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

    ui.label(f'{ID_DICT[id]} Strip')
    pattern_toggle = ui.toggle(PATTERN_DICT, on_change=lambda event: change_pattern(event.value), value=ser.RAINBOW_CODE)
    
    brightness_label = ui.label('Brightness:')
    brightness = ui.slider(min=0, max=255, step = 1, value = 128)
    
    color_label = ui.label('Color:')
    color = ui.color_input(value="#0A0E5E", preview=True)

    startcolor_label = ui.label('Start Color:')
    startcolor = ui.color_input(value="#018607", preview=True)
    
    endcolor_label = ui.label('End Color:')
    endcolor = ui.color_input(value="#0009B8", preview=True)
    
    ui.button('Update', on_click=update)
    ui.separator()
    
    change_pattern(pattern_toggle.value)
    
def root():
    for id in ID_DICT.keys():
        strip_section(id)
    
def main():
    ui.run(root)

if __name__ in {'__main__', '__mp_main__'}:
    main()
