# Project based on the [Haptic input knob](https://m.youtube.com/watch?v=Q76dMggUH1M&pp=ygUKc21hcnQga25vYg%3D%3D)

Its intended as means to learn and have some fun while coding. 

This project has a strong dependance on the I2C protocol. All of the devices used, communicate to a Raspberry pi 4 through it. 

It is composed by an SSD1315 Oled display. I decided to write a library from scratch (I know about Luma.oled. and decided to just reinvent the wheel: again, just for fun.)
It uses a few sensors: temperature+humidity, a barometric pressure sensor, and a magnetic encoder. 

The information reported by the sensors is fed into the display, as well as the current time. 

This was not thought of as just a clock, but a controlable interface. The magnetic encoder is here for this purpose: you can control stuff with it. 
With that in mind, some 3d printing was required. .STL files attached with the correct knob's measurements that fit a AS5600 encoder.

Currently, you can only see the time+sensors information. But it may well be used for more than that: plans on changing from a raspberry pi 4 to a raspberry pi pico, using it as an HID device to control volume, skip track, scrolling, etc...

