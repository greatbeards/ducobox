Ducobox Focus
==============
Homeassistant Custom component for the DocuBox focus via serial modbus connection.
Autmatic detection of connected valves / sensors / switches.


All modules described in the ducobox focus manual are supported.
`https://www.duco.eu/Wes/CDN/1/Attachments/informatieblad-ModBus-RTU-(nl)_638085224731148696.pdf`


Under development!


Connection
----------

The connection to the Ducobox is made using a RS485 to USB dongle.
The dongle is directly connected to the Homeassistant PC.


configuration
-------------

The Ducobox Focus did not require any configuration to get modbus working.


Homeassistant
=============

installation
------------
1. Install HACS in Homeassistant.
2. In the HACS tab, use the 3 dots on the right upper side to add a `custom repository`
3. Enter the repository url: `https://github.com/greatbeards/ducobox`, category: `integration`
4. Reboot


Add `Ducobox Focus` using `add integration`.

Fill in the serial port. This was `/dev/ttyUSB0` in my case, this will depent on you setup.
Baudrate and Slave ID are set to the default values.

Leave simulation mode to `0` for normal operation.
Simulation mode will create a virtual device for every supported type of valve/sensor.


Status
======



2023-03:
* Under development!
* Automatic detection of modules
* Implemented config flow
* No error handling during setup
* No services are registered => No settings can be written to the ducobox
* Status values are only displayed by number
* Docstrings missing / incorrect
