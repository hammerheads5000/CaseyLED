from neopixel import NeoPixel
import math
from machine import Pin

def hueToRgb(p, q, t):
    if t < 0: t += 1
    if t > 1: t -= 1
    if t < 1/6: return p + (q - p) * 6 * t
    if t < 1/2: return q
    if t < 2/3: return p + (q - p) * (2/3 - t) * 6
    return p

def hslToRgb(hsl):
    h, s, l = hsl
    if s == 0:
        r = g = b = l
    else:
        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q
        r = hueToRgb(p, q, h + 1/3)
        g = hueToRgb(p, q, h)
        b = hueToRgb(p, q, h - 1/3)
        
    return (round(r * 255), round(g * 255), round(b * 255))

def rgbToHsl(r, g, b):
    r /= 255
    g /= 255
    b /= 255
    
    _max = max(r, g, b)
    _min = min(r, g, b)
    l = (_max+_min)/2
    
    if (_max == _min):
        return 0,0,l

    d = _max-_min
    s = d/(2-_max-_min) if l>0.5 else d/(_max+_min)
    if _max==r:
        h=(g-b)/d + (6 if g<b else 0)
    elif _max==g:
        h=(b-r)/d + 2
    elif _max==b:
        h=(r-g)/d + 4
    h /= 6
    
    return h, s, l
            
def lerpHsl(start_hsl, end_hsl, t):
    h = (1-t)*start_hsl[0] + t*end_hsl[0]
    s = (1-t)*start_hsl[1] + t*end_hsl[1]
    l = (1-t)*start_hsl[2] + t*end_hsl[2]
    
    return h, s, l

class LEDStrip:
    def __init__(self, pin, length, reversed=False):
        self.length = length
        self.buffer = NeoPixel(Pin(pin), length)
        self.pin = pin
        self.reversed = reversed
        
    def set_range(self, start, buffer_view):
        for i in range(len(buffer_view)):
            self.buffer[self.apply_reverse(start+i)] = buffer_view[i]
            
    def apply_reverse(self, idx):
        return self.length - 1 - idx
            
    def apply_pattern(self, pattern):
        self.set_range(pattern.start, pattern.get_buffer_view())
        
    def show(self):
        self.buffer.write()
        
    def update_pin(self, pin):
        self.pin = pin
        self.buffer = NeoPixel(Pin(pin), self.length)
            
class Pattern:
    def __init__(self, start, buffer_view, brightness: float = 1.0):
        self.start = start
        self.buffer_view = buffer_view
        self.brightness = brightness
        
    def set_brightness(self, brightness: float):
        self.brightness = brightness
        
    def get_buffer_view(self):
        return [(int(g*self.brightness), int(r*self.brightness), int(b*self.brightness)) for (g, r, b) in self.buffer_view]
        
    @staticmethod
    def solid(color, length: int, start: int = 0):
        rgb_tuple = (color[0], color[1], color[2])
        buffer_view = [rgb_tuple] * length
        return Pattern(start, buffer_view)
    
    @staticmethod
    def off(length: int, start: int = 0):
        rgb_tuple = (0, 0, 0)
        buffer_view = [rgb_tuple] * length
        return Pattern(start, buffer_view)
    
    @staticmethod
    def gradient(color_start, color_end, length: int, start: int = 0):
        start_hsl = rgbToHsl(color_start[0], color_start[1], color_start[2])
        end_hsl = rgbToHsl(color_end[0], color_end[1], color_end[2])
        buffer_view = [hslToRgb(lerpHsl(start_hsl, end_hsl, t/length)) for t in range(length)]
        
        return Pattern(start, buffer_view)
    
    @staticmethod
    def rainbow(length: int, start: int = 0):
        hues = [h/length for h in range(length)]
        buffer_view = [hslToRgb((h, 1, 0.5)) for h in hues]
        return Pattern(start, buffer_view)
    
    def offest(self, offset: int):
        offset = (offset + len(self.buffer_view)) % len(self.buffer_view)
        self.buffer_view = self.buffer_view[offset:] + self.buffer_view[:offset]
        
    def tile(self, tiles: int):
        self.buffer_view = (self.buffer_view * tiles)[::tiles]

class AnimatedPattern(Pattern):
    def __init__(self, pattern: Pattern):
        super().__init__(pattern.start, pattern.buffer_view)
        
    def update(self, t):
        pass
    
class RainbowPattern(AnimatedPattern):
    def __init__(self, length: int, speed: float, scale: int):
        super().__init__(Pattern.rainbow(length))
        self.speed = speed
        self.length = length
        self.scale = scale
        self.shift = 0.0
        
        self.hues = [(h*self.scale/self.length) % 1 for h in range(2*self.length)]
        self.colors = [hslToRgb((h, 1, 0.5)) for h in self.hues]
    def update(self, t):
        self.buffer_view = self.colors[int(self.shift*self.length):int(self.shift*self.length)+self.length]
        self.shift = self.speed*t
        self.shift %= 1
        
    
class MovingPattern(AnimatedPattern):
    def __init__(self, pattern: Pattern, speed: int):
        super().__init__(pattern)
        self.speed = speed
        
    def set_speed(self, speed: int):
        self.speed = speed
        
    def update(self, t):
        self.offest(self.speed)
        
class BreathingPattern(AnimatedPattern):
    def __init__(self, pattern: Pattern, speed: float):
        super().__init__(pattern)
        self.speed = speed
        self.frame = 0
        #self.frames = [0.5+0.5*math.cos(2*math.pi*self.frame*self.speed)
        
    def update(self, t):
        t %= 100
        brightness = 0.5+0.5*math.cos(2*math.pi*t*self.speed)
        self.set_brightness(brightness)

