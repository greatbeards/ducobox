import asyncio
from asynciominimalmodbus import AsyncioInstrument
from minimalmodbus import MODE_RTU, ModbusException
import logging
import random

_LOGGER = logging.getLogger(__name__)

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

    def __init__(
        self,
        modbus_client,
        module,
        name,
        holding_reg=None,
        input_reg=None,
        number_of_decimals=0,
    ):
        self.name = name
        self.mb_client = modbus_client
        self.module = module
        self.value = None
        self.retry_attempts = 5
        self.retry = self.retry_attempts
        self.holding_reg = holding_reg
        self.input_reg = input_reg
        self.number_of_decimals = number_of_decimals

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
            new_val = random.randint(0, 100)
            if new_val < 50:
                new_val = None
            await asyncio.sleep(0.01)
        else:
            if self.holding_reg:
                new_val = await self._read_holding_reg(
                    self.holding_reg, self.number_of_decimals
                )
            else:
                new_val = await self._read_input_reg(
                    self.input_reg, self.number_of_decimals
                )

    async def _read_input_reg(self, adress, number_of_decimals=0):
        while self.retry > 1:
            try:
                ret = await self.mb_client.read_register(
                    adress - 1,
                    functioncode=4,
                    signed=True,
                    number_of_decimals=number_of_decimals,
                )
                self.retry = self.retry_attempts
                return ret
            except ModbusException:
                self.retry -= 1

        _LOGGER.warning("Disabled %s - unresponsive" % self.alias)

    async def _read_holding_reg(self, adress, number_of_decimals=0):
        while self.retry > 1:
            try:
                ret = await self.mb_client.read_register(
                    adress - 1,
                    functioncode=3,
                    signed=True,
                    number_of_decimals=number_of_decimals,
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

    def __init__(self, modbus_client, module, name, holding_reg, number_of_decimals=0):
        super().__init__(
            modbus_client,
            module,
            name,
            holding_reg=holding_reg,
            number_of_decimals=number_of_decimals,
        )

    def write(self, value):
        if not SIMULATION_MODE:
            self._write_holding_reg(
                self.holding_reg, value, number_of_decimals=self.number_of_decimals
            )
        else:
            self.value = value

    def _write_holding_reg(self, adress, value, number_of_decimals=0):
        while self.retry > 1:
            try:
                ret = self.mb_client.write_register(
                    adress - 1,
                    value,
                    functioncode=16,
                    signed=True,
                    number_of_decimals=number_of_decimals,
                )
                self.retry = self.retry_attempts
                return ret
            except ModbusException:
                self.retry -= 1
        _LOGGER.warning("Disabled actuator %s - unresponsive" % self.alias)


class DucoBoxBase:
    """
    DucoBoxBase initializes all connected valves/devices
    Creates a list of all sensors [GenericSensor|GenericActuator]
    """

    def __init__(self, serial_port, baudrate=9600, slave_adr=1, simulate=False):
        self.simulate = simulate
        self.retry_attempts = 5
        self.retry = self.retry_attempts
        self.sensors = []
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
            mb_client = AsyncioInstrument(
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

            print(adr, str(duco_mod[0]), mod, mod.name)
            print("\r\n".join([str(sens) for sens in mod.sensors]))

            self.modules.append(mod)
            self.sensors += mod.sensors
            adr += 10

        # sort sensors based on alias
        # self.sensor_alias =
        # self.sensor_alias.sort()

        # print("\r\n".join(self.sensor_alias))
        await asyncio.sleep(0.01)

    async def scan_modules(self):
        """Scan all connected modules"""
        if self.simulate:
            await self._simulate_modules()
            return

        self.modules = []
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
            if resp in ducobox_modules:
                _LOGGER.info(
                    "Detected %s on adress %d" % (ducobox_modules[resp][1], adr)
                )
                mod = ducobox_modules[resp][0](self.mb_client, adr)
                self.modules.append(mod)

        if len(self.modules) == 0:
            raise DucoBoxException("No modules detected!")

    async def update_sensors(self):
        """Fetch all data from all sensors"""

        for id, module in enumerate(self.modules):
            for sensor in module.sensors:
                await sensor.update()


class DucoDevice:
    """Base class for all devices holds the sensors list."""

    def __init__(self, required_argument="sdf") -> None:
        print("__init__ DucoDevice: " + str(required_argument))
        self.sensors = []

    def register_sensors(self, sensor_list):
        sens_names = [sens.name for sens in self.sensors]

        for new_sens in sensor_list:
            if not new_sens.name in sens_names:
                self.sensors.append(new_sens)
            else:
                print("%s already present" % new_sens.name)


class DucoBox(DucoDevice):
    name = "Master module"

    def __init__(self, mb_client: AsyncioInstrument | None, base_adr: int) -> None:
        DucoDevice.__init__(self)
        self.base_adr = base_adr

        sensors = [
            GenericSensor(
                mb_client,
                module=self,
                name="ventilation setpoint",
                holding_reg=base_adr + 0,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="auto min",
                holding_reg=base_adr + 5,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="auto max",
                holding_reg=base_adr + 6,
            ),
            GenericActuator(
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
            GenericSensor(
                mb_client,
                module=self,
                name="localisation ID",
                input_reg=base_adr + 9,
            ),
        ]

        self.register_sensors(sensors)


class DucoGenericSensor:
    name = "Generic sensor"

    def __init__(
        self, mb_client: AsyncioInstrument, base_adr: int, register_sensors=None
    ) -> None:
        self.base_adr = base_adr

        sensors = [
            GenericSensor(
                mb_client,
                module=self,
                name="status",
                input_reg=base_adr + 1,
            ),
            # Not for batter powered sensor
            GenericSensor(
                mb_client,
                module=self,
                name="temperature",
                input_reg=base_adr + 3,
                number_of_decimals=1,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="localisation ID",
                input_reg=base_adr + 9,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="button 1",
                holding_reg=base_adr + 4,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="button 2",
                holding_reg=base_adr + 5,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="button 3",
                holding_reg=base_adr + 6,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="Manual Time",
                holding_reg=base_adr + 7,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="action",
                holding_reg=base_adr + 9,
            ),
        ]

        if register_sensors:
            register_sensors(sensors)


class DucoCO2Sensor(DucoGenericSensor, DucoDevice):
    name = "CO2 sensor"

    def __init__(
        self, mb_client: AsyncioInstrument, base_adr: int, register_sensors=None
    ) -> None:
        if register_sensors is None:
            self.base_adr = base_adr
            DucoDevice.__init__(self)
            DucoGenericSensor.__init__(self, mb_client, base_adr, self.register_sensors)

        sensors = [
            GenericSensor(
                mb_client,
                module=self,
                name="CO2 value",
                input_reg=base_adr + 4,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="CO2 setpoint",
                holding_reg=base_adr + 1,
            ),
        ]

        self.register_sensors(sensors)


class DucoHumSensor(DucoGenericSensor, DucoDevice):
    name = "Humidity sensor"

    def __init__(
        self, mb_client: AsyncioInstrument, base_adr: int, register_sensors=None
    ) -> None:
        if register_sensors is None:
            self.base_adr = base_adr
            DucoDevice.__init__(self)
            DucoGenericSensor.__init__(self, mb_client, base_adr, self.register_sensors)

        sensors = [
            GenericSensor(
                mb_client,
                module=self,
                name="humidity",
                input_reg=base_adr + 5,
                number_of_decimals=1,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="humidity setpoint",
                holding_reg=base_adr + 2,
                number_of_decimals=1,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="humidity delta",
                holding_reg=base_adr + 3,
            ),
        ]

        self.register_sensors(sensors)


class DucoValve:
    """Holding the generic parameters for a valve"""

    name = "Generic valve"

    def __init__(
        self, mb_client: AsyncioInstrument, base_adr: int, register_sensors=None
    ) -> None:
        print("DucoValve")
        self.base_adr = base_adr
        self.mb_client = mb_client

        sensors = [
            GenericActuator(
                mb_client,
                module=self,
                name="auto min",
                holding_reg=base_adr + 5,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="auto max",
                holding_reg=base_adr + 6,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="localisation ID",
                input_reg=base_adr + 9,
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
                name="temperature",
                input_reg=base_adr + 3,
                number_of_decimals=1,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="ventilation setpoint",
                holding_reg=base_adr + 0,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="flow",
                holding_reg=base_adr + 4,
            ),
            GenericActuator(
                mb_client,
                module=self,
                name="action",
                holding_reg=base_adr + 9,
            ),
        ]

        print(register_sensors)

        if register_sensors:
            print("registering sensors from DucoValve")
            register_sensors(sensors)


class DucoSwitch(DucoGenericSensor, DucoDevice):
    name = "control switch"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        self.base_adr = base_adr
        DucoDevice.__init__(self)
        super().__init__(mb_client, base_adr, self.register_sensors)


class DucoSensorlessValve(DucoValve, DucoDevice):
    name = "Sensorless valve"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        DucoDevice.__init__(self)
        DucoValve.__init__(self, mb_client, base_adr, self.register_sensors)


class DucoCO2Valve(DucoValve, DucoCO2Sensor, DucoDevice):
    name = "CO2 valve"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        self.base_adr = base_adr
        DucoDevice.__init__(self)
        DucoValve.__init__(self, mb_client, base_adr, self.register_sensors)
        DucoCO2Sensor.__init__(self, mb_client, base_adr, self.register_sensors)


class DucoHumValve(DucoValve, DucoHumSensor, DucoDevice):
    name = "Humidity valve"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        self.base_adr = base_adr
        DucoDevice.__init__(self)
        DucoValve.__init__(self, mb_client, base_adr, self.register_sensors)
        DucoHumSensor.__init__(self, mb_client, base_adr, self.register_sensors)


class DucoCO2HumValve(DucoValve, DucoCO2Sensor, DucoHumSensor, DucoDevice):
    name = "Humidity and CO2 valve"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        self.base_adr = base_adr
        DucoDevice.__init__(self)
        DucoValve.__init__(self, mb_client, base_adr, self.register_sensors)
        DucoCO2Sensor.__init__(self, mb_client, base_adr, self.register_sensors)
        DucoHumSensor.__init__(self, mb_client, base_adr, self.register_sensors)


class DucoVentValve(DucoValve, DucoDevice):
    name = "Tronic vent valve"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        self.base_adr = base_adr
        DucoDevice.__init__(self)
        DucoValve.__init__(self, mb_client, base_adr, self.register_sensors)

        sensors = [
            GenericSensor(
                mb_client,
                module=self,
                name="grille position",
                input_reg=base_adr + 2,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="temperature",
                input_reg=base_adr + 3,
                number_of_decimals=1,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="inlet",
                holding_reg=base_adr + 4,
            ),
        ]

        self.register_sensors(sensors)


class DucoRelay(DucoDevice):
    name = "relay contact"

    def __init__(self, mb_client: AsyncioInstrument, base_adr: int) -> None:
        self.base_adr = base_adr
        DucoDevice.__init__(self)

        sensors = [
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
                name="ventilation setpoint",
                holding_reg=base_adr + 0,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="switch mode",
                holding_reg=base_adr + 1,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="switch value",
                holding_reg=base_adr + 2,
            ),
            GenericSensor(
                mb_client,
                module=self,
                name="action",
                holding_reg=base_adr + 9,
            ),
        ]

        self.register_sensors(sensors)


ducobox_modules = {
    10: (DucoBox, "master"),
    11: (DucoSensorlessValve, "Sensorless valve"),
    12: (DucoCO2Valve, "CO2 valve"),
    13: (DucoHumValve, "humidity valve"),
    14: (DucoSwitch, "control switch"),
    15: (DucoCO2Sensor, "CO2 sensor"),
    16: (DucoHumSensor, "humidity sensor"),
    17: (DucoVentValve, "tronic vent valve"),
    18: (DucoRelay, "relay contact"),
    24: (DucoCO2HumValve, "humidity and CO2 valve"),
}

###########################################################
###########################################################
###########################################################
if __name__ == "__main__":
    import time

    loop = asyncio.get_event_loop()

    dbb = DucoBoxBase("/dev/ttyUSB0", simulate=True)
    loop.run_until_complete(dbb.create_serial_connection())
    loop.run_until_complete(dbb.scan_modules())
    loop.run_until_complete(dbb.update_sensors())

    while True:
        time.sleep(1)
        loop.run_until_complete(dbb.update_sensors())

    loop.run_forever()

    print("\r\n".join(dbb.sensor_alias))
