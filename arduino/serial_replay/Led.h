#ifndef LED_H
#define LED_H

#include "Arduino.h"

#ifndef LED_DEBUG
#define LED_DEBUG 0
#endif // LED_DEBUG

#define LED_ONDUTY  500
#define LED_OFFDUTY 500

class Led
{
  public:
    static Led *forPins(int *pins);
    Led(int pin);
    void on();
    void off();
    void flash(int count = 0);
    void tick();
  private:
    int _pin;
    unsigned long _nextMillis;
    int _nextState;
    int _flashCount;
    void _tickDebug(long tickTime);
};

#endif // LED_H
