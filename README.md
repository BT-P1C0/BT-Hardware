# BT-P1C0: Tracker Hardware

The Tracker updates its location on the website [here](<[https://mg-lsj.github.io/Bus-Tracker/](https://bt-p1c0.github.io/BT-Website/)>).

## Image (v6)

![v6a image](/img/v6a.png)
![v6b image](/img/v6b.png)

## Components used:

-   Raspberry Pi Pico (Microcontroller): Controls other two modules
-   NEO-6M (GNSS module): Gets current location
-   SIM800L (GSM/GPRS module): Sends location to the website
-   InvenSense MPU9250 (IMU): Crash detection
-   SSD1306 (OLED Display): Debug codes

## Wiring Diagram v3

![Drawing Diagram](/img/Bt-Pico.png)

## Working

![Working Diagram](/img/working.png)

## How to setup this project?

1. Install this [extension](https://marketplace.visualstudio.com/items?itemName=paulober.pico-w-go).
2. Open the `project's scripts` folder in VS Code
3. Open command pallete by pressing `Ctrl+Shift+P`
4. Run this command. `Pico-W-Go > Configure Project`
5. Done.

A helpful youtube tutorial to setup VS code for Pico can be found [here](https://www.youtube.com/watch?v=O6lkYTfcMEg).

### Hardware Checks

Check LEDs on modules to see if modules are working correctly  
**NOTE:** Startup process can take upto a minute or more.

1. NEO-6M  
   This modules takes 30 - 45 seconds to startup in the best case.
    - No blinking - Searching for satellites
    - Blink every 1 second - Position fix found (Module can "see" enough satelittes).
2. SIM800L  
   For this module startup takes around 30 seconds.
    - Blink every 1s - Module is seaching for a network
    - Blink every 2s - Data connection is active
    - Blink every 3s - Module is connected to a network and can receive/send

Now, run `test_connections.py` to check connections.

## Renders

![](/img/renders/t.png)
![](/img/renders/a1.png)
![](/img/renders/a4.png)
![](/img/renders/b.png)
![](/img/renders/b1.png)
![](/img/renders/b4.png)
