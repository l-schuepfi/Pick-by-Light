/*

   Pick-by-Light System
   -------------------------------------------------------
   Program used to support the Raspberry Pi 4B at the
   Pick-by-Light with controlling the IR-diodes and
   reading correct values from the load cell.

   This program is based on the calibration file from
   Olav Kallhovd's HX711_ADC library.

   It allows calibration of the load cell via the serial
   interface. At startup, the EEPROM value is read from
   the load cell and used as a calibration factor.

   For this purpose, a pulsed signal with a duty cycle
   of approx. 1.5% and 38 kHz is sent to pin 3. It was
   also set to transmit for 120 ms and then pause for
   380 ms.

   Author: Andreas Katzenberger
   Date: 2026-02-22

*/

#include <HX711_ADC.h>
#if defined(ESP8266)|| defined(ESP32) || defined(AVR)
#include <EEPROM.h>
#endif

// Pins
const int irLedPin = 3; // PWM output (OC2B) -> 38kHz signal
const int HX711_dout = 4; // mcu > HX711 dout pin
const int HX711_sck = 5; // mcu > HX711 sck pin

// Global variables for measurement
volatile int burstCycles = 0; // Counts the cycles for the burst timer

// Calculations for timer 2 overflow (clock rate 16 MHz, OCR2A=210 -> cycle time 26.3 µs)
// const int CYCLES_PER_MS = 1000 / 26.316; // ~38 cycles per millisecond
const int BURST_MS = 120; // Transmission time in milliseconds
const int CYCLE_MS = 500; // Total cycle time in milliseconds (120 ms transmission + 380 ms pause)

const int CYCLES_PER_120MS = 38 * BURST_MS; // 4,560 cycles
const int CYCLES_PER_500MS = 38 * CYCLE_MS; // 19,000 cycles

// HX711 constructor:
HX711_ADC LoadCell(HX711_dout, HX711_sck);

const int calVal_eepromAdress = 0;
float calFactor = 1.0;
unsigned long t = 0;

void setup() {
  Serial.begin(57600);
  delay(1);

  // Pin 3 (OC2B) must be output for the 38kHz signal
  pinMode(irLedPin, OUTPUT); 

  // --- TIMER 2 CONFIGURATION ---
  // Disable interrupts to set registers safely
  noInterrupts();

  // 1. TCCR2A (Timer/Counter Control Register A)
  // WGM20 = 1, WGM21 = 0 (Phase Correct PWM, Top is OCR2A)
  // COM2B1 = 1 (Connects pin 3 to the timer: Clear on Compare Match)
  TCCR2A = _BV(WGM20);

  // 2. TCCR2B (Timer/Counter Control Register B)
  // WGM22 = 1 (Phase Correct PWM Mode 5)
  // CS20 = 1 (No prescaler = use 16 MHz clock directly)
  TCCR2B = _BV(WGM22) | _BV(CS20);

  // 3. OCR2A (Output Compare Register A) - Determines the frequency
  OCR2A = 210; // 16 MHz / (2 * 38 kHz) = 210.5

  // 4. OCR2B (Output Compare Register B) - Determines the duty cycle
  // 1.5% Duty Cycle desired:
  OCR2B = 3; // 210 * 0.015 = 3.15

  // Enable Timer 2 overflow interrupt (TOIE2 = 1)
  TIMSK2 = _BV(TOIE2);

  interrupts(); // Interrupts back on

  LoadCell.begin();
  unsigned long stabilizingtime = 2000; // preciscion right after power-up can be improved by adding a few seconds of stabilizing time
  LoadCell.start(stabilizingtime, true);
  if (LoadCell.getTareTimeoutFlag() || LoadCell.getSignalTimeoutFlag()) {
    Serial.println("Timeout, check MCU>HX711 wiring and pin designations");
    while (1);
  }
  else {
    EEPROM.get(calVal_eepromAdress, calFactor);
    LoadCell.setCalFactor(calFactor); // Set calibration value from EEPROM so that calibration is not mandatory when starting the microcontroller
  }
}

// --- INTERRUPT SERVICE ROUTINEN (ISRs) ---

/**
 * ISR for Timer 2 overflow. Controls the 500 ms transmission cycle (120 ms transmission / 380 ms pause).
 */
ISR(TIMER2_OVF_vect) {
  burstCycles++;

  if (burstCycles == CYCLES_PER_120MS) {
    // 1. At the end of the 120 ms burst: Stop transmission (disconnect OC2B from timer 2)
    TCCR2A &= ~_BV(COM2B1); // Disable pin 3 (OC2B)
    
  } else if (burstCycles >= CYCLES_PER_500MS) {
    // 2. At the end of the 500ms cycle: Reset and start transmission
    burstCycles = 0;
    TCCR2A |= _BV(COM2B1); // Connect pin 3 (OC2B) to timer 2 -> Transmission begins
  }
}

void loop() {
  static boolean newDataReady = false;

  // check for new data/start next conversion:
  if (LoadCell.update()) {
    newDataReady = true;
  }

  // get smoothed value from the dataset:
  if (newDataReady) {
    float i = LoadCell.getData();
    Serial.print("Load_cell output val: ");
    Serial.println(i);
    newDataReady = false;
  }

  // receive command from serial terminal
  if (Serial.available() > 0) {
    char inByte = Serial.read();
    if (inByte == 't') {
      LoadCell.tareNoDelay(); //tare
      Serial.println("Tare complete");
    }
    else if (inByte == 'c') {
      LoadCell.setCalFactor(1.0);
      calibrate(); //calibrate
    }
    else if (inByte == 'r') {
      reset();
    }
  }

  // check if last tare operation is complete
  if (LoadCell.getTareStatus() == true) {
    Serial.println("Tare complete");
  }

}

void reset() {
  EEPROM.get(calVal_eepromAdress, calFactor);
  LoadCell.setCalFactor(calFactor);
  LoadCell.tareNoDelay(); //tare
}

void calibrate() {
  Serial.println("Start calibration (tare)");

  boolean _resume = false;
  while (_resume == false) {
    LoadCell.update();
    if (Serial.available() > 0) {
      char inByte = Serial.read();
      if (inByte == 't') LoadCell.tareNoDelay();
      else if (inByte == 'r') {
        reset();
        return;
      }
    }
    if (LoadCell.getTareStatus() == true) {
      Serial.println("Tare complete");
      _resume = true;
    }
  }

  Serial.println("Calibration (200.0g)");

  float known_mass = 0;
  _resume = false;
  while (_resume == false) {
    LoadCell.update();
    if (Serial.available() > 0) {
      // Check whether an 'r' was sent before parseFloat starts
      if (Serial.peek() == 'r') {
        Serial.read(); // Remove the 'r' from the buffer
        reset();
        return;
      }
      
      known_mass = Serial.parseFloat();
      if (known_mass != 0) {
        Serial.print("Known mass is: ");
        Serial.println(known_mass);
        _resume = true;
      }
    }
  }

  LoadCell.refreshDataSet(); // refresh the dataset to be sure that the known mass is measured correct
  float newCalibrationValue = LoadCell.getNewCalibration(known_mass); // get the new calibration value

  #if defined(ESP8266)|| defined(ESP32)
    EEPROM.begin(512);
  #endif
    EEPROM.put(calVal_eepromAdress, newCalibrationValue);
  #if defined(ESP8266)|| defined(ESP32)
    EEPROM.commit();
  #endif
    EEPROM.get(calVal_eepromAdress, newCalibrationValue);

  Serial.println("End calibration");

  // Have the weights removed again
  _resume = false;
  while (_resume == false) {
    LoadCell.update();
    if (Serial.available() > 0) {
      char inByte = Serial.read();
      if (inByte == 't') LoadCell.tareNoDelay();
      else if (inByte == 'r') {
        reset();
        return;
      }
    }
    if (LoadCell.getTareStatus() == true) {
      Serial.println("Tare complete");
      _resume = true;
    }
  }
}