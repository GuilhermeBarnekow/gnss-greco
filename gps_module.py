import serial
import threading
import time
import random
import logging

class GNSSModule:
    def __init__(self, port=None, baudrate=115200, simulation=False, max_retries=5, retry_delay=2):
        self.simulation = simulation
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.ser = None
        self.logger = logging.getLogger('GNSSModule')
        if not self.simulation:
            # Use default port if not specified
            if port is None:
                # Common serial ports for Raspberry Pi
                possible_ports = ['/dev/serial0', '/dev/ttyAMA0', '/dev/ttyS0']
                for p in possible_ports:
                    if self._try_open_port(p, baudrate):
                        break
                else:
                    self.logger.error("Could not open any serial port for GNSS module.")
                    self.logger.info("Falling back to simulation mode due to serial port error.")
                    self.simulation = True
                    self._start_simulation()
            else:
                if not self._try_open_port(port, baudrate):
                    self.logger.error(f"Could not open specified port {port} for GNSS module.")
                    self.logger.info("Falling back to simulation mode due to serial port error.")
                    self.simulation = True
                    self._start_simulation()
                    return
        else:
            self.sim_data_index = 0
            self.sim_data = self._generate_sim_data()
            self.lock = threading.Lock()
            self.running = True
            self.thread = threading.Thread(target=self._simulate_data_thread, daemon=True)
            self.thread.start()

    def _try_open_port(self, port, baudrate):
        for attempt in range(1, self.max_retries + 1):
            try:
                self.ser = serial.Serial(port, baudrate, timeout=1)
                self.logger.info(f"Connected to GNSS module on port {port} (attempt {attempt})")
                return True
            except serial.SerialException as e:
                self.logger.warning(f"Attempt {attempt} failed to open port {port}: {e}")
                time.sleep(self.retry_delay)
        return False

    def _generate_sim_data(self):
        # Generate simulated GPS data points (latitude, longitude)
        base_lat = -23.5505  # Example base location (São Paulo)
        base_lon = -46.6333
        data = []
        for i in range(1000):
            lat = base_lat + (random.random() - 0.5) * 0.01
            lon = base_lon + (random.random() - 0.5) * 0.01
            data.append((lat, lon))
        return data

    def _simulate_data_thread(self):
        while self.running:
            time.sleep(1)
            with self.lock:
                self.sim_data_index = (self.sim_data_index + 1) % len(self.sim_data)

    def read_data(self):
        if self.simulation:
            try:
                with self.lock:
                    lat, lon = self.sim_data[self.sim_data_index]
                # Return simulated NMEA-like string or tuple
                return f"$GPGGA,{lat},{lon}"
            except Exception as e:
                self.logger.error(f"Error reading simulated data: {e}")
                return None
        else:
            if self.ser is None:
                self.logger.error("Serial port not initialized.")
                return None
            try:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('ascii', errors='replace').strip()
                    # Validate NMEA sentence or GPS data integrity here
                    if self._validate_data(line):
                        return line
                    else:
                        self.logger.warning(f"Invalid GPS data received: {line}")
                        return None
                return None
            except serial.SerialException as e:
                self.logger.error(f"Serial read error: {e}")
                # Attempt to reconnect
                self._attempt_reconnect()
                return None
            except Exception as e:
                self.logger.error(f"Unexpected error reading serial data: {e}")
                return None

    def _validate_data(self, data):
        # Basic validation: check if data starts with $ and has commas
        if not data.startswith('$'):
            return False
        if ',' not in data:
            return False
        # Further validation can be added here (e.g., checksum)
        return True

    def _attempt_reconnect(self):
        self.logger.info("Attempting to reconnect to serial port...")
        if self.ser:
            try:
                self.ser.close()
            except Exception as e:
                self.logger.warning(f"Error closing serial port: {e}")
            self.ser = None
        # Try to reopen the port with retries
        possible_ports = ['/dev/serial0', '/dev/ttyAMA0', '/dev/ttyS0']
        for p in possible_ports:
            if self._try_open_port(p, 115200):
                self.logger.info(f"Reconnected to serial port {p}")
                return
        self.logger.error("Failed to reconnect to any serial port.")

    def stop(self):
        if self.simulation:
            self.running = False
            self.thread.join()

    def _start_simulation(self):
        self.sim_data_index = 0
        self.sim_data = self._generate_sim_data()
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self._simulate_data_thread, daemon=True)
        self.thread.start()
