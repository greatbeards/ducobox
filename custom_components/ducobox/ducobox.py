import asyncio
from asynciominimalmodbus import AsyncioInstrument
from minimalmodbus import MODE_RTU, ModbusException
import logging
import random

_LOGGER = logging.getLogger(__name__)

# import time
# import os
# import requests
# import sys
# import numpy as np
# import datetime
# import configparser
# import _LOGGER
# import _LOGGER.handlers

## file:///C:/Users/gebruiker/Downloads/informatieblad-ModBus-RTU-(nl).pdf
# https://www.duco.eu/Wes/CDN/1/Attachments/informatieblad-ModBus-RTU-(nl)_638085224731148696.pdf


status_descr = {
    0: "Auto",
    1: "10 min high",
    2: "20 min high",
    3: "30 min high",
    4: "Manual low",
    5: "Manual middle",
    6: "Manual high",
    7: "Away / Not home",
    8: "Permanent low",
    9: "Permanent middle",
    10: "Permanente high",
    99: "Error",
}

SIMULATION_MODE = False


class DucoBoxException(Exception):
    pass


class GenericSensor:
    """Generic class to read a setting from the instrument."""

    def __init__(self, modbus_client, module, name, holding_reg=None, input_reg=None):
        self.name = name
        self.mb_client = modbus_client
        self.module = module
        self.value = None
        self.retry_attempts = 5
        self.retry = self.retry_attempts
        self.holding_reg = holding_reg
        self.input_reg = input_reg

        self.alias = (
            str(self.module.name)
            + " @adr "
            + str(self.module.base_adr)
            + " "
            + self.name
            + " "
            + str(input_reg)
            + " "
            + str(holding_reg)
        )

    async def update(self):
        if SIMULATION_MODE:
            self.value = random.randint(0, 100)
            await asyncio.sleep(0.01)
            return

        if self.holding_reg:
            self.value = await self.read_holding_reg(self.holding_reg)
        else:
            self.value = await self.read_input_reg(self.input_reg)

    async def read_input_reg(self, adress):
        while self.retry > 1:
            try:
                ret = await self.mb_client.read_register(
                    adress - 1, functioncode=4, signed=True
                )
                self.retry = self.retry_attempts
                return ret
            except ModbusException:
                self.retry -= 1

        _LOGGER.warning("Disabled %s - unresponsive" % self.alias)

    async def read_holding_reg(self, adress):
        while self.retry > 1:
            try:
                ret = await self.mb_client.read_register(
                    adress - 1, functioncode=3, signed=True
                )
                self.retry = self.retry_attempts
                return ret
            except ModbusException:
                self.retry -= 1

        print("Disabled sensor %s - unresponsive" % self.alias)

    def __str__(self):
        return "%s: %s" % (self.alias, str(self.value))


class GenericActuator(GenericSensor):
    """Generic class to write a setting to the instrument."""

    def __init__(self, modbus_client, module, name, holding_reg):
        super().__init__(modbus_client, module, name, holding_reg=holding_reg)

    def write(self, value):
        if not SIMULATION_MODE:
            self._write_holding_reg(self.holding_reg, value)
        else:
            self.value = value

    def _write_holding_reg(self, adress, value):
        while self.retry > 1:
            try:
                ret = self.mb_client.write_register(
                    adress - 1, value, functioncode=16, signed=True
                )
                self.retry = self.retry_attempts
                return ret
            except ModbusException:
                self.retry -= 1
        _LOGGER.warning("Disabled actuator %s - unresponsive" % self.alias)


class DucoBoxBase:
    """
    DucoBoxBase initializes all connected valves/devices
    Creates a list of all sensors [GenericSensor] and actuators [GenericActuator]
    """

    def __init__(self, serial_port, baudrate=9600, slave_adr=1, simulate=False):
        self.simulate = simulate
        self.retry_attempts = 5
        self.retry = self.retry_attempts
        self.sensors = []
        self.actuators = []
        self.modules = []
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.slave_adr = slave_adr
        self.mb_client = None

        if simulate:
            global SIMULATION_MODE
            SIMULATION_MODE = True

            _LOGGER.info("Running in simulation mode")

    async def create_serial_connection(self):
        if self.simulate:
            await asyncio.sleep(0.01)
            return

        try:
            mb_client = await AsyncioInstrument(
                self.serial_port, self.slave_adr, mode=MODE_RTU
            )  # port name, slave address (in decimal)
            mb_client.serial.timeout = 0.1  # sec
            mb_client.serial.baudrate = self.baudrate
            self.mb_client = mb_client
        except Exception:
            _LOGGER.exception(f"Failed to open serial port {self.serial_port}")

    def add_sensor(self, sensor: GenericSensor):
        self.sensors.append(sensor)

    def detected(self):
        return len(self.modules) > 0

    async def _simulate_modules(self):
        """In simulation mode, load a module of each type"""

        adr = 10
        for code, duco_mod in ducobox_modules.items():
            mod = duco_mod[0](mb_client=self.mb_client, base_adr=adr)
            self.modules.append(mod)
            adr += 10
            await asyncio.sleep(0.01)

    async def scan_modules(self):
        """Scan all connected modules"""
        if self.simulate:
            await self._simulate_modules()
            return

        for adr in range(10, 90, 10):
            resp = None
            while self.retry > 1:
                try:
                    resp = await self.mb_client.read_register(
                        adr - 1, functioncode=4, signed=True
                    )
                    break
                except ModbusException:
                    self.retry -= 1

            if resp is None:
                _LOGGER.warning("No response from %d - stop scanning for modules" % adr)
                break

            self.modules = []
            if resp in ducobox_modules:
                _LOGGER.info(
                    "Detected %s on adress %d" % (ducobox_modules[resp][1], adr)
                )
                mod = ducobox_modules[resp][0](self.mb_client, adr)
                # self.sensors += mod.sensors
                # self.actuators += mod.actuators
                self.modules.append(mod)

        if len(self.modules) == 0:
            raise DucoBoxException("No modules detected!")

    async def update_sensors(self):
        """Fetch all data from all sensors"""

        for id, module in enumerate(self.modules):
            remove_ids = []
            for id, sensor in enumerate(module.sensors):
                await sensor.update()

                if sensor.value is None:
                    remove_ids.append(id)
                else:
                    print(sensor)

            for id in remove_ids[::-1]:
                del self.sensors[id]


class DucoBox:
    name = "Master module"

    def __init__(self, mb_client: AsyncioInstrument | None, base_adr: int) -> None:
        self.mb_client = mb_client
        self.base_adr = base_adr

        self.sensors = [
            GenericSensor(
                mb_client,
                module=self,
                name="ventilation setpoint",
                holding_reg=base_adr + 0,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="auto min",
                holding_reg=base_adr + 5,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="auto max",
                holding_reg=base_adr + 6,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="action",
                holding_reg=base_adr + 9,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="status",
                input_reg=base_adr + 1,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="ventilation level",
                input_reg=base_adr + 2,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="power",
                input_reg=base_adr + 3,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="average power",
                input_reg=base_adr + 4,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="maximal power",
                input_reg=base_adr + 5,
            ),
        ]

        self.actuators = []


class DucoValve(DucoBox):
    name = "Generic valve"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        super().__init__(mb_client, base_adr)
        self.mb_client = mb_client

        self.sensors = [
            GenericSensor(
                mb_client,
                module=self,
                name="auto min",
                holding_reg=base_adr + 5,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="auto max",
                holding_reg=base_adr + 6,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="localisation ID",
                holding_reg=base_adr + 9,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="status",
                input_reg=base_adr + 1,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="ventilation level",
                input_reg=base_adr + 2,
            ),
            # GenericSensor(
            #    mb_client,
            #    module=self,
            #    name="temperature",
            #    input_reg=base_adr + 3,
            # ),
        ]

        self.actuators = [
            GenericActuator(
                mb_client,
                module=self,
                name="ventilation setpoint",
                holding_reg=base_adr + 0,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="maximal flow",
                holding_reg=base_adr + 4,
            ),
        ]


class DucoCO2Valve(DucoValve):
    name = "CO2 valve"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        super().__init__(mb_client, base_adr)

        self.sensors += [
            GenericSensor(
                mb_client,
                module=self,
                name="temperature",
                input_reg=base_adr + 4,
            ),
        ]

        self.actuators += [
            GenericActuator(
                mb_client,
                module=self,
                name="CO2 setpoint",
                holding_reg=base_adr + 1,
            ),
        ]


class DucoHumValve(DucoValve):
    name = "Humidity valve"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        super().__init__(mb_client, base_adr)

        self.sensors += [
            GenericSensor(
                mb_client,
                module=self,
                name="humidity",
                input_reg=base_adr + 5,
            ),
        ]

        self.actuators += [
            GenericActuator(
                mb_client,
                module=self,
                name="humidity setpoint",
                holding_reg=base_adr + 2,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="humidity delta",
                holding_reg=base_adr + 3,
            ),
        ]


class DucoCO2HumValve(DucoValve):
    name = "Humidity and CO2 valve"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        super().__init__(mb_client, base_adr)

        self.sensors += [
            GenericSensor(
                mb_client,
                module=self,
                name="temperature",
                input_reg=base_adr + 4,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="humidity",
                input_reg=base_adr + 5,
            ),
        ]

        self.actuators += [
            GenericActuator(
                mb_client,
                module=self,
                name="CO2 setpoint",
                holding_reg=base_adr + 1,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="humidity setpoint",
                holding_reg=base_adr + 2,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="humidity delta",
                holding_reg=base_adr + 3,
            ),
        ]


class DucoSensorlessValve(DucoValve):
    name = "Sensorless valve"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        super().__init__(mb_client, base_adr)

        self.sensors += [
            GenericSensor(
                mb_client,
                module=self,
                name="temperature",
                input_reg=base_adr + 3,
            )
        ]


class DucoSensor:
    name = "Generic sensor"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        self.base_adr = base_adr

        self.sensors = [
            GenericSensor(
                mb_client,
                module=self,
                name="status",
                input_reg=base_adr + 1,
            ),
            # not supported on my ducoboxFocus
            GenericSensor(
                mb_client,
                module=self,
                name="localisation ID",
                input_reg=base_adr + 9,
            ),
        ]

        self.actuators = []


class DucoCO2Sensor(DucoSensor):
    name = "CO2 sensor"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        super().__init__(mb_client, base_adr)

        self.sensors += [
            GenericSensor(
                mb_client,
                module=self,
                name="temperature",
                input_reg=base_adr + 3,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="CO2 value",
                input_reg=base_adr + 4,
            ),
        ]

        self.actuators += [
            GenericActuator(
                mb_client,
                module=self,
                name="CO2 setpoint",
                holding_reg=base_adr + 1,
            ),
        ]


class DucoHumSensor(DucoSensor):
    name = "Humidity sensor"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        super().__init__(mb_client, base_adr)

        self.sensors += [
            GenericSensor(
                mb_client,
                module=self,
                name="temperature",
                input_reg=base_adr + 3,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="humidity",
                input_reg=base_adr + 5,
            ),
        ]

        self.actuators += [
            GenericActuator(
                mb_client,
                module=self,
                name="humidity setpoint",
                holding_reg=base_adr + 2,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="humidity delta",
                holding_reg=base_adr + 3,
            ),
        ]


class DucoVentValve(DucoValve):
    name = "Tronic vent valve"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        super().__init__(mb_client, base_adr)

        self.sensors += [
            GenericSensor(
                mb_client,
                module=self,
                name="temperature",
                input_reg=base_adr + 3,
            ),
        ]


class DucoControlSwitch(DucoValve):
    name = "Switching contact"


ducobox_modules = {
    10: (DucoBox, "master"),
    11: (DucoSensorlessValve, "Sensorless valve"),
    12: (DucoCO2Valve, "CO2 valve"),
    13: (DucoHumValve, "humidity valve"),
    14: (DucoSensor, "control switch"),
    15: (DucoCO2Sensor, "CO2 sensor"),
    16: (DucoHumSensor, "humidity sensor"),
    17: (DucoVentValve, "tronic vent valve"),
    18: (DucoControlSwitch, "switching contact"),
    24: (DucoCO2HumValve, "humidity and CO2 valve"),
}

###########################################################
###########################################################
###########################################################
if __name__ == "__main__":
    dbb = DucoBoxBase("/dev/ttyUSB0", simulate=True)
    asyncio.run(dbb.create_serial_connection())
    asyncio.run(dbb.scan_modules())
    asyncio.run(dbb.update_sensors())
