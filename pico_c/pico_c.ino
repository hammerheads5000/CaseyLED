#include <FastLED.h>

// serial setup
#define CONFIG_STRIP_CODE 0b1111
#define DELETE_STRIP_CODE 0b1110
#define UPDATE_FREQ_CODE 0b1101

#define OFF_CODE 0b0000
#define SOLID_CODE 0b0001
#define RAINBOW_CODE 0b0010
#define GRADIENT_CODE 0b0111
#define MOVING_PULSES_CODE 0b0100
#define SET_RANGE_CODE 0b0110
#define BREATHING_CODE 0b1001

#define BRIGHTNESS_CODE 0b1000

// led setup
#define MAX_STRIPS 16
#define MAX_LEN 256
#define UPDATE_FREQUENCY 60
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB

enum Pattern {
  OFF,
  SOLID,
  GRADIENT,
  RAINBOW,
  BREATHING
};

uint8_t pins[MAX_STRIPS] = {-1};
size_t lengths[MAX_STRIPS] = {0};
Pattern patterns[MAX_STRIPS] = {Pattern::OFF};
uint8_t brightnesses[MAX_STRIPS] = {255};
uint8_t speeds[MAX_STRIPS] = {0};
uint8_t scales[MAX_STRIPS] = {0};
CRGB colors[MAX_STRIPS] = {CRGB(0)};
size_t num_strips = 0;
CRGB leds[MAX_STRIPS][MAX_LEN];
CLEDController controllers[MAX_STRIPS];

void setup() {
  delay(2000);
  Serial.begin(115200);
}

void delete_strip_data(uint8_t id) {
  controllers[id].clearLedData();
  pins[id] = -1;
}

void add_strip_data(uint8_t id, uint8_t pin, size_t length) {
  controllers[id] = FastLED.addLeds<LED_TYPE, pin, COLOR_ORDER>(leds[id], length).setCorrection(TypicalLEDStrip);
  pins[id] = pin;
  lengths[id] = length;
}

void delete_strip(uint8_t id) {
  delete_strip_data(id);
  for (int i = id; i < num_strips-1; i++) {
    controllers[i] = controllers[i+1];
    pins[i] = pins[i+1];
    lengths[i] = lengths[i+1];
    patterns[i] = patterns[i+1];
    brightnesses[i] = brightnesses[i+1];
    speeds[i] = speeds[i+1];
    colors[i] = colors[i+1];
    leds[i] = leds[i+1];
  }
  num_strips--;
}

void add_strip(uint8_t pin, size_t length) {
  add_strip_data(num_strips, pin, length);
  num_strips++;
}

void apply_config(uint8_t id, uint8_t data[]) {
  // bool reversed = (bool)(data[0] >> 7);
  uint8_t pin = (data[0] & 0b01111100) >> 2;
  size_t length = ((data[0] & 0b11) << 8) + data[1];

  if (id < num_strips && (pins[id] != pin || lengths[id] != length)) {
      delete_strip_data(id);
      add_strip_data(id, pin, length);
  } else if (id == num_strips+1) {
    add_strip(pin, length);
  } else {
    Serial.println("CONFIG ERROR: strip ID out of range");
    return;
  }
  Serial.print("Strip ");
  Serial.print(id);
  Serial.print(" configured at pin ");
  Serial.print(pin);
  Serial.print(" with length ");
  Serial.println(length);
}

void apply_pattern(uint8_t id, uint8_t control_code, uint8_t data[]) {
  if (id >= num_strips) {
    Serial.println("ERROR: strip ID not found");
    return;
  }
  switch (control_code) {
    case OFF_CODE:
      patterns[id] = Pattern::OFF;
      off(id);
      break;
    case SOLID_CODE:
      patterns[id] = Pattern::SOLID;
      solid(id, CRGB(data[0], data[1], data[2]);
      break;
    case RAINBOW_CODE:
      patterns[id] = Pattern::RAINBOW;
      speeds[id] = data[0];
      break;
    case GRADIENT_CODE:
      patterns[id] = Pattern::GRADIENT;
      gradient(id, CRGB(data[0], data[1], data[2]), CRGB(data[3], data[4], data[5]));
      break;
    case BREATHING_CODE:
      patterns[id] = Pattern::BREATHING;
      speeds[id] = data[0];
      colors[id] = CRGB(data[1], data[2], data[3]));
      break;
    case BRIGHTNESS_CODE:
      brightnesses[id] = data[0];
      break;
  }
  apply_brightness(id);
}

void apply_brightness(uint8_t id) {
  nscale8(leds[id], lengths[id], brightnesses[id]);
}

//-----PATTERNS-----//
void off(uint8_t id) {
  fill_solid(leds[id], lengths[id], CRGB(0));
}

void solid(uint8_t id, CRGB color) {
  fill_solid(leds[id], lengths[id], color);
}

void gradient(uint8_t id, CRGB start, CRGB end) {
  fill_gradient(leds[id], 0, start, lengths[id], end);
}

void rainbow(uint8_t id) {
  fill_rainbow(leds[id], lengths[id], beat16(speeds[id]*scales[id]), scales[id]);
}

void breathing(uint8_t id) {
  fill_solid(leds[id], lengths[id], colors[id]);
  nscale8(leds[id], lengths[id], beatsin8(speeds[id]))
}

void set_pattern(uint8_t id, Pattern pattern) {
  patterns[id] = pattern;
  apply_brightness(id);
}

void update_strip(uint8_t id) {
  switch (patterns[id]) {
    case Pattern::RAINBOW:
      rainbow(id);
      apply_brightness(id);
      break;
    case Pattern::BREATHING:
      breathing(id);
      apply_brightness(id);
      break;
    default:
      break;
  }
}

int read_data(uint8_t buffer[], uint8_t control_code) {
  uint8_t data_len = 0;
  switch (control_code) {
    case CONFIG_STRIP_CODE:
      data_len = 2;
      break;
    case SOLID_CODE:
      data_len = 3;
      break;
    case RAINBOW_CODE:
      data_len = 1;
      break;
    case GRADIENT_CODE:
      data_len = 6;
      break;
    case BREATHING_CODE:
      data_len = 4;
      break;
    case BRIGHTNESS_CODE:
      data_len = 1;
      break;
  }
  size_t num_read = Serial.readBytes(buffer, data_len);
  if (num_read < data_len) {
    Serial.println("WARNING: Reading data timed out");
    return -1;
  }
  return 0;
}

void loop() {
  if (Serial.available() > 0 && Serial.read() == 0xFF) {
    uint8_t byte0 = Serial.read();
    uint8_t id = byte0 >> 4;
    uint8_t control_code = byte0 & 0b1111;
    uint8_t buffer[10];
    if (read_data(buffer, control_code) == 0) {
      switch (control_code) {
        case CONFIG_STRIP_CODE:
          apply_config(id, data);
          break;
        case DELETE_STRIP_CODE:
          delete_strip(id);
          break;
        default:
          apply_pattern(id, control_code, buffer);
          break;
      }
    }
  }

  for (uint8_t i = 0; i < num_strips; i++) {
    update_strip(i);
  }
  FastLED.show();
  FastLED.delay(1000/UPDATE_FREQUENCY);
}