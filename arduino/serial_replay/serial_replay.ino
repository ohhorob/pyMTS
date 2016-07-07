#define LED_DEBUG 0
#include "Led.h"
/*
 * Test receiving bytes from a host.
 * 
 * Bytes are captured from IPS2 protocol, try and find header words with length.
 * 
 * Print back to USB when found. Include packet length to evaluate health of detected packet
 * 
 */

// set this to the hardware serial port you wish to use
#define HWSERIAL Serial1

unsigned long baud = 19200;
const int reset_pin = 4;
const int led_pin = 13;

#define RECBUFF 256
byte buffer[RECBUFF];

void setup() {
    pinMode(led_pin, OUTPUT);
    digitalWrite(led_pin, LOW);
    digitalWrite(reset_pin, HIGH);
    pinMode(reset_pin, OUTPUT);
    Serial.begin(baud);  // USB, communication to PC or Mac
    // Don't need Serial1 for now
//    HWSERIAL.begin(baud); // communication to hardware serial
    showLed();
    while(!Serial) {
      // Wait one second with blinks 2 x (250 + 250)
      blinkLed(2, 250, 250);
    }
    
    Serial.println("Serial Ready");
    
//    if (baud != Serial.baud()) {
//      blinkLed(10, 250, 750);
//    } else {
//      blinkLed(20, 250, 250);
//    }
}

/*
 * Reset pin is triggered by USB Serial DTR
 */
unsigned char prev_dtr = 0;
void maintainReset() {
  unsigned char dtr;
    // check if the USB virtual serial port has raised DTR
  dtr = Serial.dtr();
  if (dtr && !prev_dtr) {
    Serial.println("Reset triggered");
    digitalWrite(reset_pin, LOW);
    delayMicroseconds(250);
    digitalWrite(reset_pin, HIGH);
  }
  prev_dtr = dtr;
}

void maintainUSB() {
    // check if the USB virtual serial wants a new baud rate
  if (Serial.baud() != baud) {
    baud = Serial.baud();
    if (baud == 57600) {
      // This ugly hack is necessary for talking
      // to the arduino bootloader, which actually
      // communicates at 58824 baud (+2.1% error).
      // Teensyduino will configure the UART for
      // the closest baud rate, which is 57143
      // baud (-0.8% error).  Serial communication
      // can tolerate about 2.5% error, so the
      // combined error is too large.  Simply
      // setting the baud rate to the same as
      // arduino's actual baud rate works.
      HWSERIAL.begin(58824);
      showLed();
      delay(2000);
      
    } else {
      HWSERIAL.begin(baud);
    }
    Serial.println("!!! Serial baud mismatch !!!");
  }
}

long led_on_time = 0;

void showLed() {
  // turn on the LED to indicate activity
  digitalWrite(led_pin, HIGH);
  led_on_time = millis();
}

void hideLed() {
  digitalWrite(led_pin, LOW);
  led_on_time = 0;
}

/*
 * LED needs to be turned off after idling for some period
 */
void maintainLed() {
    // if the LED has been left on without more activity, turn it off
  if (led_on_time > 0 && millis() - led_on_time > 3) {
    hideLed();
  }
}

void blinkLed(int count, int onDuty, int offDuty) {
  for (int i = 0; i < count; i++) {
    showLed();
    delay(onDuty);
    hideLed();
    delay(offDuty);
  }
}

/*
 * Consume byte buffer for header word mask
 */
short headerword = 0x0000;
int streamDepth = 0;

void scanForHeaderWord(int dataLen) {
  Serial.print("Stream Depth = ");
  Serial.print(streamDepth);
  Serial.print("; Data length = ");
  Serial.println(dataLen);
  
  for (int i = 0; i < dataLen; i++) {
    byte LSB = buffer[i];
    // Shift along the existing LSB to MSB, and add new LSB
    headerword = ((headerword & 0x00FF) << 8) | LSB;
    Serial.println(headerword, HEX);
    streamDepth++;
  }
  Serial.println();
}

/************
 * Main Loop
 */

void loop() {
  int incoming_available, incoming_read;

  // check if any data has arrived on the USB virtual serial port
  incoming_available = Serial.available();
  if (incoming_available > 0) {
      if (incoming_available > RECBUFF) incoming_available = RECBUFF;
      // read data from the USB port
      incoming_read = Serial.readBytes((char *)buffer, incoming_available);
      scanForHeaderWord(incoming_read);
      showLed();
    }

  maintainReset();
  maintainLed();
//  maintainUSB();
}
