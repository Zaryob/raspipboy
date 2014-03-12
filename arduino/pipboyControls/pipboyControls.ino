// Teensy 2++ USB-Serial Controller
//  for RasPipBoy, the Raspberry Pi Pip-Boy 3000
// By Neal D Corbett, 2013

#include <Encoder.h>
#include <Bounce.h>
#include <AccelStepper.h>

// Set up 4-pin stepper-motor - this'll be the radiation-gauge:
AccelStepper stepper(4, 42, 43, 44, 45);
int gaugeMode = 0;
long int gaugeVal = 0;

// Change these pin numbers to the pins connected to your encoder.
//   Best Performance: both pins have interrupt capability1Q
//   Good Performance: only the first pin has interrupt capability
//   Low Performance:  neither pin has interrupt capability
Encoder knobEnc(0, 1);
Encoder scrollEnc(2, 3);
int encoderPins[] = {2,3,4,5,};
//   (avoid using pins with LEDs attached)

const int mouseSpeed = 10;

int tabNum = 0;
int modeNum = 0;
boolean torchActive = false;

// Pin used to turn sound/screen on/off:
int powerPin = 45;

// Battery-voltage analog-read pin
//  (connected to 20Kohm/10Kohm voltage-divider)
int battVoltsActivePin = 44; // Turn voltage-divider on/off
int battVoltsAPin = A0;  // Analog pin (F0)
int battVoltsDPin = 38;  // Digital address for same pin
float maxVolts = 7.68; // Maximum voltage-divider input-value (corresponds to 2.56V reference-voltage)

// Analog-read info for temperature sensor:
//  (I'm using a TMP36 sensor component)
int tempAPin = A1;  // Analog pin (F1)
int tempDPin = 39;  // Digital address for same pin

unsigned long keyPressDelay = 500;

unsigned long buttonHoldTime = 700;
unsigned long buttonToHoldTime = 0;
boolean buttonIsHeld = false;
boolean buttonWasHeld = false;

// Last pin is the screen-torch:
int ledPins[] = {17, 16, 15, 14,};
const int ledCount = 4;

char tabKeys[] = "123";
char modeKeys[] = "qwerty";
//int tabKeys[] = {KEY_1,KEY_2,KEY_3};
//int modeKeys[] = {KEY_Q,KEY_W,KEY_E,KEY_R,KEY_T};

// The three lit tab-buttons, the rotary switch pins, knob-press, selector-button: 
int buttonPins[] = {13, 12, 11,  21, 22, 23, 24, 25, 26,   27, 7, };
unsigned long debounceDur = 30;
Bounce bounces[] = 
{
  Bounce(buttonPins[0],debounceDur), 
  Bounce(buttonPins[1],debounceDur),
  Bounce(buttonPins[2],debounceDur), 
  Bounce(buttonPins[3],debounceDur),
  Bounce(buttonPins[4],debounceDur), 
  Bounce(buttonPins[5],debounceDur),
  Bounce(buttonPins[6],debounceDur), 
  Bounce(buttonPins[7],debounceDur),
  Bounce(buttonPins[8],debounceDur),
  Bounce(buttonPins[9],debounceDur),
  Bounce(buttonPins[10],debounceDur),
};
const int buttonCount = 11;

String inputString = "";

void setup() 
{
  // POWER-SAVING: Set all pins to output by default:
  for (int n = 0; n < 46; n++)
  {
    pinMode(n, OUTPUT);
  }
  
  // Set up serial bits:
  Serial.begin(38400);
  inputString.reserve(200);
  
  // Set up analog-read pins:
  analogReference(INTERNAL2V56);
  pinMode(battVoltsDPin, INPUT);
  pinMode(tempDPin, INPUT);
  maxVolts /= 100.0;
  
  // Set up input-pins, with pullup resistors enabled:
  for (int n = 0; n < 4; n++)
  {
    pinMode(encoderPins[n], INPUT_PULLUP);
  }
  for (int n = 0; n < buttonCount; n++)
  {
    pinMode(buttonPins[n], INPUT_PULLUP);
  }

  // Set up leds:
  for (int n = 0; n < ledCount; n++)
  {
    pinMode(ledPins[n], OUTPUT);
    digitalWrite(ledPins[n], HIGH);
  }
  // Turn on default-mode LED:
  digitalWrite(ledPins[0], LOW);
  digitalWrite(ledPins[3], torchActive);
  
  // Initialise stepper-motor:
  stepper.setMaxSpeed(200);
  stepper.setAcceleration(5000);
  // Move to limit, then forward a step, then reset zero-step:
  stepper.setCurrentPosition(0);
  stepper.runToNewPosition(-10);
  stepper.runToNewPosition(-9);
  stepper.setCurrentPosition(0.0);
  
  // Turn on amplifier/screen:
  digitalWrite(powerPin, HIGH);

  delayMicroseconds(10);
}

boolean standby = false;
boolean knobPressed = false;
boolean firstLoop = true;

long newVal;
int randVal;
unsigned long nextRand;

void setStandby (boolean sleep)
{
  // Mode 5 is always standby...
  sleep = (sleep || (modeNum == 5));
  
  if (sleep != standby)
  {
    standby = sleep;
    
    if (standby)
    {
//      Serial.println("STANDING BY");
      
      digitalWrite(powerPin, LOW);
      digitalWrite(ledPins[tabNum], HIGH);
    }
    else 
    {
//      Serial.println("WAKING UP");
      digitalWrite(powerPin, HIGH);
      digitalWrite(ledPins[tabNum], LOW);
    }
  }
}

void loop() 
{
  int tabWas = tabNum;
  int modeWas = modeNum;
  
  boolean tabPress = false;
  boolean modePress = false;
  
  // Parse serial-buffer
  while (Serial.available()) 
  {
    // get the new byte:
    char inChar = (char)Serial.read(); 
  
    // if the incoming character is a newline, deal with the recieved line:
    if (inChar == '\n') 
    {
      // Set stepper's move-target:
      if (inputString.startsWith("gaugeMove="))
      {
        String valStr = inputString.substring(10);
        gaugeVal = valStr.toInt();
        stepper.moveTo(gaugeVal);
      }
      // Set stepper acceleration:
      else if (inputString.startsWith("gaugeAcc=")) 
      {
        String valStr = inputString.substring(9);
        long int accVal = valStr.toInt();
        stepper.setAcceleration(accVal);
      }
      // Send a particular gauge-mode:
      if (inputString.startsWith("gaugeMode="))
      {
        String valStr = inputString.substring(10);
        gaugeMode = valStr.toInt();
      }

      // Read battery voltage:
      else if (inputString.startsWith("volts"))
      {
        // Activate the voltage-divider:
        digitalWrite(battVoltsActivePin, HIGH);
        
        // Initial read to clear bad volts...
        analogRead(battVoltsAPin); delay(20);
        
        // Take average of lots of readings:
        int16_t battVal = 0;
        for (int n = 0; n < 32; n += 1)
        {
          battVal += (analogRead(battVoltsAPin));    // Read analog value
          delay(20);
        }
        battVal /= 32;
        
        digitalWrite(battVoltsActivePin, LOW);
        
        battVal = map (battVal,0,1023,0,100);
        float battVolts = (maxVolts * battVal);
        
        Serial.print("volts ");
        Serial.println(battVolts);
      }

      // Read temperature:
      else if (inputString.startsWith("temp"))
      {
        // Initial read to clear bad volts...
        analogRead(tempAPin); delay(20);
        
        // Take average of lots of readings:
        int16_t tempVal = 0;
        for (int n = 0; n < 32; n += 1)
        {
          tempVal += (analogRead(tempAPin));    // Read analog value
          delay(10);
        }
        tempVal /= 32;

//        Serial.print("\nVal: ");Serial.println(tempVal);
        tempVal = map (tempVal,0,1023,0,2560); // Convert to millivolts
//        Serial.print("mv: ");Serial.println(tempVal);
        
        float tempDegrees = 0.1 * (tempVal - 500);
        Serial.print("temp ");
        Serial.println(tempDegrees);
      }
      // Go into low-power standby-mode:
      else if (inputString.startsWith("sleep"))
      {
        setStandby(true);
      }
      // Wake up from standby-mode:
      else if (inputString.startsWith("wake"))
      {
        setStandby(false);
      }
      // Send id-string on request:
      else if (inputString == "identify")
      {
        Serial.println("PIPBOY");
      }
      
      // clear string, ready for further commands:
      inputString = "";
    }
    else 
    {
      // add it to the inputString:
      inputString += inChar;
    }
  } 
  
  for (int n = 0; n < buttonCount; n++)
  {
    bounces[n].update();
    
    if (n < 3)
    {
      if (bounces[n].fallingEdge())
      {
        tabNum = n;
        tabPress = true;
        
        // Turn on corresponding LED:
        if ((tabNum != tabWas) && (!firstLoop))
        {
          for (int m = 0; m < 3; m++) 
          {
            if (m == n)
            {
              digitalWrite(ledPins[m], LOW);
            }
            else 
            {
              digitalWrite(ledPins[m], HIGH);
            }
          }
        }
        
        // Wake up from standby-mode:
        setStandby(false);
      }
    }
    // Rotary-switch turned:
    else if (n < 9)
    {
      if (bounces[n].read() == LOW)
      {
        modeNum = (n - 3);
        modePress = (modeNum != modeWas);
      }
    }
    // Knob-press:
    else if (n == 9)
    {
      knobPressed = (bounces[n].read());
    }
    // Front-button press:
    else if (n == 10) 
    {
      if (bounces[n].fallingEdge())
      {
        // Wake up from standby-mode:
        setStandby(false);
        
        Serial.println("select");
        
        // Reset holding-count when starting press:
        buttonToHoldTime = (millis() + buttonHoldTime);
        buttonIsHeld = true;
        buttonWasHeld = false;
      }
      else if (bounces[n].risingEdge())
      {
        buttonIsHeld = false;
      }
    }
  }
  
  if ((buttonIsHeld) && (!buttonWasHeld) && ((millis()) > buttonToHoldTime))
  {
    // Toggle torch:
    buttonWasHeld = true;
    torchActive = !torchActive;
    
    // Let Pi know if torch is toggling on or off:
    if (torchActive)
    {
      Serial.println("lighton");
    }
    else 
    {
      Serial.println("lightoff");
    }

    // Wait for Pi to finish redrawing bright screen before changing LEDs...
    if (torchActive)
    {
      delay(400);
    }
    digitalWrite(ledPins[3], torchActive);
  }
  
  if (tabPress && (!firstLoop))
  {
    Serial.println(tabKeys[tabNum]);
  }
        
  if (modePress && (!firstLoop))
  {
    // Wake up from standby-mode:
    setStandby(false);

    Serial.println(modeKeys[modeNum]);
    modeWas = modeNum;
  }
  
  long newKnob, newScroll;
  
  // Scroll-dial, presses Up/Down keys:
  newScroll = scrollEnc.read();  
  if ((newScroll > 3) || (newScroll < -3))
  {
    // Wake up from standby-mode:
    setStandby(false);
    
    if (newScroll < 0)
    {
      Serial.println("cursorup");
    }
    else 
    {
      Serial.println("cursordown");
    }
    
    // Reset encoder:
    scrollEnc.write(0);
  }

  // Hand-mounted knob, controls mouse:
  newKnob = knobEnc.read();  
  if ((newKnob > 3) || (newKnob < -3))
  {
    // Wake up from standby-mode:
    setStandby(false);
    
    // Moves mouse left/right if knob-button is not pressed:
    if (knobPressed) 
    {
      if (newKnob < 0)
      {
//        Mouse.move(mouseSpeed, 0);
        Serial.println("right");
      }
      else 
      {
//        Mouse.move(-mouseSpeed, 0);
        Serial.println("left");
      }
    }
    // Moves mouse up/down if button is pressed:
    else 
    {
      if (newKnob < 0)
      {
//        Mouse.move(0, mouseSpeed);
        Serial.println("up");
      }
      else 
      {
//        Mouse.move(0, -mouseSpeed);
        Serial.println("down");
      }
    }

    // Reset encoder:    
    knobEnc.write(0);
  }
  
  // Update stepper-position:
  if (!standby)
  {
    if (stepper.distanceToGo() == 0)
    {
      if (gaugeMode!=0)
      {
        if (stepper.currentPosition() == gaugeVal)
        {
          if (nextRand < millis())
          {
            stepper.setAcceleration(5000);
            randVal = random(0,100);
            
            if ((gaugeMode==2)&&(randVal > 90))
            {
              newVal = random(5,8);
            }
            else 
            {
              newVal = (gaugeVal + 1);
            }
    
            nextRand = millis() + random(50,2000);
            stepper.moveTo(newVal);
            stepper.run();
          }
        }
        else 
        {
          stepper.setAcceleration(10);
          stepper.moveTo(gaugeVal);
        }
      }
    }
    else 
    {
      stepper.run();
    }
  }
  
  firstLoop = false;
}

