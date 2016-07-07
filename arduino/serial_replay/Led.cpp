#include "Arduino.h"
#include "Led.h"

Led * Led::forPins(int *pins) {
  int len = sizeof(pins);
  Led* result = (Led *)malloc(sizeof(Led) * len);
  for (int i = 0; i < len; i++) {
    result[i] = Led(pins[i]);
  }
  return result;
}

Led::Led(int pin)
{
  pinMode(pin, OUTPUT);
  digitalWrite(pin, LOW);
  _pin = pin;
  _nextMillis = 0L; // Future action time
  _nextState = LOW; // Turn off in the future
  _flashCount = 0;
#if (LED_DEBUG == 1)
  Serial.print("New Led on pin ");
  Serial.println(_pin);
#endif
}

void Led::on()
{
  digitalWrite(_pin, HIGH);
  _nextMillis = 0L;
}

void Led::off()
{
  digitalWrite(_pin, LOW);
  _nextMillis = 0L;
}

void Led::flash(int count)
{
  _flashCount = count;
  digitalWrite(_pin, HIGH);
  _nextMillis = millis() + LED_ONDUTY;
  _nextState = LOW;
}

/**
 * Call tick regularly to achieve flash or auto-off functions
 */
void Led::tick()
{
  // State managment is only active when _nextMillis is non-zero
  if (_nextMillis > 0) {
    long tickTime = millis();
    if (_nextMillis <= tickTime) {
      digitalWrite(_pin, _nextState);
      // Flash logic is to schedule another HIGH cycle after going low
      if (LOW == _nextState && _flashCount-- > 0) {
        _nextMillis += LED_OFFDUTY;
        _nextState = HIGH;
        _flashCount--;
#if (LED_DEBUG == 1)
        _tickDebug(tickTime);
        Serial.println("LO");
#endif // LED_DEBUG
      } else if (HIGH == _nextState) {
        _nextMillis += LED_ONDUTY;
        _nextState = LOW;
#if (LED_DEBUG == 1)
        _tickDebug(tickTime);
        Serial.println("HI");
#endif // LED_DEBUG
      } else {
#if (LED_DEBUG == 1)
        _tickDebug(tickTime);
        Serial.println("STOPPED");
#endif // LED_DEBUG
        _nextMillis = 0L;
      }
//#if (LED_DEBUG == 1)
//    } else {
//        Serial.println("..");
//#endif // LED_DEBUG
    }
  }
}

void Led::_tickDebug(long tickTime) {
  Serial.print(_pin);
  Serial.print(": [");
  Serial.print(tickTime);
  Serial.print("] (");
  Serial.print(_nextMillis);
  Serial.print(") ");
}

