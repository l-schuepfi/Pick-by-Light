/*

   Pick-by-Light System
   -------------------------------------------------------
   Program used to check if the IR-modules are working
   before attaching them to the system.

   For this purpose, a pulsed signal with a duty cycle
   of approx. 1.5% and 38 kHz is sent to pin 3. It was
   also set to transmit for 120 ms and then pause for
   380 ms.

   On pin 8, the output of the module is catched and
   analyzed by determining the LOW-times and printing
   them to the Serial Monitor.

   They function correctly if values near 120.0 are
   received when holding your hand next to the module.
   With increasing the distance to the module, the
   values should decrease linearly.

   Author: Andreas Katzenberger
   Date: 2026-02-22

*/

// Pins
const int irLedPin = 3; // PWM output (OC2B) -> 38kHz signal
const int receiverPin = 8; // Receiver on pin 8

// Global variables for measurement
volatile int burstCycles = 0; // Counts the cycles for the burst timer

// Calculations for timer 2 overflow (clock rate 16 MHz, OCR2A=210 -> cycle time 26.3 µs)
// const int CYCLES_PER_MS = 1000 / 26.316; // ~38 cycles per millisecond
const int BURST_MS = 120; // Transmission time in milliseconds
const int CYCLE_MS = 500; // Total cycle time in milliseconds (120 ms transmission + 380 ms pause)

const int CYCLES_PER_120MS = 38 * BURST_MS; // 4,560 cycles
const int CYCLES_PER_500MS = 38 * CYCLE_MS; // 19,000 cycles

bool detectFallingSlope = true;
int lowInARow = 0;
unsigned long startLow = 0;

int highInARow = 0;
unsigned long startHigh = 0;

float lowTimeMs = 0.0;

void setup() {
  Serial.begin(115200);

  // Configure pins
  pinMode(receiverPin, INPUT);
  
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
  
  Serial.println("System ready. 38kHz high-power carrier active on pin 3.");
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
  lowTimeMs = getLowTimeMs();
  Serial.println(lowTimeMs);
}


float getLowTimeMs() {
  // The TSSP4P38 pulls the output LOW when it detects 38 kHz.
  // In case of interruption, it goes to HIGH.

  float diff_ms = 0.0;
  while(true) {
    if (digitalRead(receiverPin) == HIGH) {
      lowInARow = 0;
      if (detectFallingSlope == false) {
        highInARow += 1;
        if(highInARow == 1)
        {
          startHigh = micros();
        }
        else if (highInARow >= 5) {
          detectFallingSlope = true;
          highInARow = 0;
          diff_ms = (startHigh - startLow) / 1000.0;
          return diff_ms;
        }
      }
    }
    else {
      highInARow = 0;
      if (detectFallingSlope == true) {
        lowInARow += 1;
        if(lowInARow == 1)
        {
          startLow = micros();
        }
        else if (lowInARow >= 5) {
          detectFallingSlope = false;
          lowInARow = 0;
        }
      }
    }
  }
}


// Sorts a float array of length n in order
void sortArray(float *values, int n) {
  // Bubble Sort
  for (int i = 0; i < n - 1; i++) {
    for (int j = 0; j < n - i - 1; j++) {
      if (values[j] > values[j + 1]) {
        int tmp = values[j];
        values[j] = values[j + 1];
        values[j + 1] = tmp;
      }
    }
  }
}


/**
 * Calculates the mean value of a float array.
 * Ignores values before the start index or after the end index.
 */
float mean(const float *values, int start, int end) {
  float sum = 0;
  for (int i = start; i <= end; i++) {
    sum += values[i];
  }
  return (float)sum / float(end - start + 1);
}


/**
 * Calculates the standard deviation of a float array.
 * Ignores values before the start index or after the end index.
 */
float stddev(const float *values, int start, int end, float meanValue) {
  float varSum = 0;
  int count = end - start + 1;

  for (int i = start; i <= end; i++) {
    float diff = values[i] - meanValue;
    varSum += diff * diff;
  }
  return sqrt(varSum / count);
}