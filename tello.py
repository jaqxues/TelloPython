import queue
import datetime
import logging
import socket
import threading
import time


def _try_to_int(value):
    try:
        value = int(value)
    except:
        pass
    return value


class Drone:
    TELLO_COMMAND_PORT = 8889
    TELLO_VIDEO_PORT = 11111
    TELLO_STATE_PORT = 8890

    def __init__(self, local_ip='', local_port=8889, state_interval=0.2, command_timeout=5.0, tello_ip='192.168.10.1'):

        self.state_interval = state_interval
        self.command_timeout = command_timeout

        self.abort_flag = False

        self.response_queue = queue.Queue(1)
        self.state_last_update = None
        self.states = {}

        self.tello_address = (tello_ip, self.TELLO_COMMAND_PORT)
        self.local_state_port = self.TELLO_STATE_PORT
        self.local_video_port = self.TELLO_VIDEO_PORT

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket_state = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.socket.bind((local_ip, local_port))
        self.socket_state.bind((local_ip, self.local_state_port))

        self.receive_ack_thread = threading.Thread(target=self._receive_ack)
        self.receive_ack_thread.daemon = True
        self.receive_ack_thread.start()
        self.receive_state_thread = threading.Thread(target=self._receive_state)
        self.receive_state_thread.daemon = True
        self.receive_state_thread.start()

    def __del__(self):
        self.socket.close()
        self.socket_state.close()

    def _receive_ack(self):
        while True:
            try:
                data, _ = self.socket.recvfrom(1518)
                print(data)
                if data:
                    self.response_queue.put(data.decode(encoding='utf-8'))
            except socket.error:
                logging.error('Ack Socket Failed')

    def _receive_state(self):
        while True:
            try:
                data, ip = self.socket_state.recvfrom(1024)
                if data:
                    data = data.decode(encoding='utf-8')
                    if ';' in data:
                        states = data.replace(';\r\n', '').split(';')
                        self.states = {s[0]: s[1] for s in map(lambda item: item.split(';'), states)}

                self.state_last_update = datetime.datetime.now()

                time.sleep(self.state_interval)
            except socket.error:
                logging.error('State Socket Failed')

    def send_command(self, command, command_timeout=None):
        if command_timeout is None:
            command_timeout = self.command_timeout
        print('>> Send Command:', command)

        self.abort_flag = False

        self.socket.sendto(command.encode(encoding='utf-8'), self.tello_address)

        try:
            command_response = self.response_queue.get(timeout=command_timeout)
        except queue.Empty:
            logging.error("Empty Response Queue")
            command_response = "none_response"

        return command_response

    def enter_sdk_mode(self):
        return self.send_command('command')

    def start_stream(self):
        return self.send_command('streamon')

    def stop_stream(self):
        return self.send_command('streamoff')

    def take_off(self):
        return self.send_command('takeoff', 10)  # Takeoff Command takes longer than other Commands

    def land(self):
        return self.send_command('land')

    def emergency(self):
        return self.send_command('emergency')

    def _move(self, direction, distance):
        distance = min(distance, 500)
        distance = max(distance, 20)
        return self.send_command(f'{direction} {distance}')

    def move_backward(self, distance):
        return self._move('back', distance)

    def move_forward(self, distance):
        return self._move('forward', distance)

    def move_left(self, distance):
        return self._move('left', distance)

    def move_right(self, distance):
        return self._move('right', distance)

    def move_up(self, distance):
        return self._move('up', distance)

    def go_location(self, x, y, z, speed):
        return self.send_command(f'go {x} {y} {z} {speed}')

    def curve(self, x1, y1, z1, x2, y2, z2, speed):
        return self.send_command(f'curve {x1} {y1} {z1} {x2} {y2} {z2} {speed}')

    def get_wifi(self):
        return self.send_command('wifi?')

    def get_sdk(self):
        return self.send_command('sdk?')

    def get_serial_number(self):
        return self.send_command('sn?')

    def get_flight_time(self):
        flight_time = self.send_command('time?')
        return _try_to_int(flight_time)

    def get_battery(self):
        battery = self.send_command('battery?')
        return _try_to_int(battery)

    def get_speed(self):
        speed = self.send_command('speed?')
        try:
            speed = round((float(speed) / 27.7778), 1)
        except:
            pass
        return speed

    def get_last_states(self):
        return self.states
