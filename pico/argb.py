from neopixel import NeoPixel
import math

def hueToRgb(p, q, t):
    if t < 0: t += 1
    if t > 1: t -= 1
    if t < 1/6: return p + (q - p) * 6 * t
    if t < 1/2: return q
    if t < 2/3: return p + (q - p) * (2/3 - t) * 6
    return p

def hslToRgb(h, s, l):
    if s == 0:
        r = g = b = l
    else:
        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q
        r = hueToRgb(p, q, h + 1/3)
        g = hueToRgb(p, q, h)
        b = hueToRgb(p, q, h - 1/3)
        
    return (round(r * 255), round(g * 255), round(b * 255))
        

class LEDStrip:
    def __init__(self, pin, num_leds):
        self.num_leds = num_leds
        self.buffer = NeoPixel(pin, num_leds)
        
    def set_range(self, start, buffer_view):
        for i in range(len(buffer_view)):
            self.buffer[start+i] = buffer_view[i]
            
    def apply_pattern(self, pattern):
        self.set_range(pattern.start, pattern.get_buffer_view())
        
    def show(self):
        self.buffer.write()
            
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
        buffer_view = [color_start]*length
        return Pattern(start, buffer_view)
    
    @staticmethod
    def rainbow(length: int, start: int = 0):
        hues = [h/length for h in range(length)]
        buffer_view = [hslToRgb(h, 1, 0.5) for h in hues]
        return Pattern(start, buffer_view)
    
    @staticmethod
    def wave(color, length: int, start: int = 0):
        for i in range(length):
            val = .5*math.sin((2*math.pi*i)/50)+.5
            buffer_view[i] = (color[0]*val, color[1]*val, color[2]*val)
    
    def offest(self, offset: int):
        offset = (offset + len(self.buffer_view)) % len(self.buffer_view)
        self.buffer_view = self.buffer_view[offset:] + self.buffer_view[:offset]
        
    def tile(self, tiles: int):
        self.buffer_view = (self.buffer_view * tiles)[::tiles]

class AnimatedPattern(Pattern):
    def __init__(self, pattern: Pattern):
        super().__init__(pattern.start, pattern.buffer_view)
        
    def update(self):
        pass
    
class RainbowPattern(AnimatedPattern):
    def __init__(self, length: int, speed: float, scale: float):
        super().__init__(Pattern.rainbow(length))
        self.speed = speed
        self.length = length
        self.scale = scale
        self.shift = 0.0
        
    def update(self):
        hues = [(h*self.scale/self.length + self.shift) % 1 for h in range(self.length)]
        self.buffer_view = [hslToRgb(h, 1, 0.5) for h in hues]
        self.shift += self.speed
        self.shift %= 1
        
    
class MovingPattern(AnimatedPattern):
    def __init__(self, pattern: Pattern, speed: int):
        super().__init__(pattern)
        self.speed = speed
        
    def set_speed(speed: int):
        self.speed = speed
        
    def update(self):
        self.offest(self.speed)
        
class WavePattern(AnimatedPattern):
    def __init__(self, color, length, speed: int):
        pattern = Pattern.wave(color, length)
        super().__init__(pattern)
        self.speed = speed
        self.storeOffset = 0
        self.buffer_view = 0
        self.length = length
        
    def set_speed(speed: int):
        self.speed = speed
        
    def update(self):
        storeOffset += self.speed
        for i in range(self.length):
            val = .5*math.sin(((2*math.pi*i)/50)+storeOffset)+.5
            self.buffer_view[i] = (self.color[0]*val, self.color[1]*val, self.color[2]*val)

class BreathingPattern(AnimatedPattern):
    def __init__(self, pattern: Pattern, period: int):
        super().__init__(pattern)
        self.period = period
        self.frame = 0
        
    def update(self):
        brightness = 0.5-0.5*math.cos(2*math.pi*self.frame/self.period)
        self.frame += 1
        self.frame %= self.period
        self.set_brightness(brightness)