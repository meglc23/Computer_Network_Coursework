#!/usr/bin/python3

import random
import socket
import sys
import threading

TOTAL_ROOM = 10
MAX_PLAYER_NUM = 100
USER_INFO = {}
MSG = {1001: "Authentication successful",
       1002: "Authentication failed",
       3001: "",
       3011: "Wait",
       3012: "Game started. Please guess true or false",
       3013: "The room is full",
       3021: "You are the winner",
       3022: "You lost this game",
       3023: "The result is a tie",
       4001: "Buy bye",
       4002: "Unrecognized message"
       }


class GameHouse(object):
    def __init__(self, id):
        self.id = id
        self.player_val_pair = {}
        self.rand_bool_val = -1     # 0: false, 1: true

    def add_player(self, cur_player):
        self.player_val_pair[cur_player] = -1

    def find_partner(self, cur_player):
        for player in self.player_val_pair:
            if player != cur_player:
                return player
        return None

    def set_player_val(self, cur_player, val):
        self.player_val_pair[cur_player] = val

    def generate_rand_bool(self):
        if self.rand_bool_val == -1:
            self.rand_bool_val = random.randint(0, 1)

    def calc_game_res(self, cur_player):
        # return result:
        # -1 -> wait for partner,   0 -> current player loses,
        # 1 -> current player wins, 2 -> tie
        partner_val = self.player_val_pair[self.find_partner(cur_player)]
        if partner_val == -1:
            return -1
        cur_val = self.player_val_pair[cur_player]
        if cur_val == partner_val:
            return 2
        self.generate_rand_bool()
        return self.rand_bool_val == cur_val

    def reset(self):
        self.player_val_pair = {}
        self.rand_bool_val = -1


class Player(object):
    def __init__(self, name):
        self.name = name
        self.room = -1
        self.status = 0
        self.conn_socket = None
        # status:
        # 0 -> out of house,    1 -> in the game hall,
        # 2 -> waiting in room, 3 -> playing a game

    def __eq__(self, other):
        if not isinstance(other, Player):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def login(self, conn_socket):
        self.set_status(1)
        self.conn_socket = conn_socket

    def join_room(self, room):
        self.room = room
        self.set_status(2)

    def end_game(self):
        self.room = -1
        self.set_status(1)

    def log_off(self):
        self.room = -1
        self.set_status(0)
        self.conn_socket = None

    def set_status(self, new_status):
        self.status = new_status


class Game(object):
    def __init__(self, server_socket):
        self.lock = threading.Lock()
        self.server_socket = server_socket
        self.game_houses = [GameHouse(id) for id in range(TOTAL_ROOM+1)]
        self.players = [Player(pair[0]) for pair in USER_INFO]

    def start_game(self):
        while True:
            client = self.server_socket.accept()
            new_client = threading.Thread(
                target=self.handle_each_client, args=(client,))
            new_client.start()

    def check_connection(self, connect, cur_player, conn_socket, msg):
        if connect and len(msg) > 0:
            return True
        if not cur_player:
            conn_socket.close()
            return False
        if cur_player.status == 3:
            with self.lock:
                partner = self.game_houses[cur_player.room].find_partner(
                    cur_player)
            if partner.status:
                self.send_msg(partner.conn_socket, 3021)
        cur_player.log_off()
        return False

    def handle_each_client(self, client):
        conn_socket, addr = client

        # login authentication
        auth_info = []
        connect = self.get_msg(conn_socket, auth_info)
        if not self.check_connection(connect, None, conn_socket, auth_info):
            return

        while USER_INFO[auth_info[1]] != auth_info[2]:
            connect = self.send_msg(conn_socket, 1002)
            connect &= self.get_msg(conn_socket, auth_info)
            if not self.check_connection(connect, None, conn_socket, auth_info):
                return

        for player in self.players:
            if player.name == auth_info[1]:
                cur_player = player
        cur_player.login(conn_socket)
        connect = self.send_msg(conn_socket, 1001)

        # login successful
        while(cur_player.status != 0):
            msg = []
            connect &= self.get_msg(conn_socket, msg)
            if not self.check_connection(connect, cur_player, conn_socket, msg):
                return
            action = self.parse_msg(msg, cur_player)
            if action:
                connect = self.send_msg(conn_socket, action)

        conn_socket.close()

    def get_msg(self, conn_socket, msg):
        try:
            str_msg = conn_socket.recv(1024).decode()
        except socket.error as err:
            print("Socket recv error: ", err)
            return False
        msg[:] = list(str_msg.split())
        return True

    def send_msg(self, conn_socket, action):
        msg = str(action) + " " + MSG[action]
        if action == 3001:
            with self.lock:
                msg += str(TOTAL_ROOM) + ' '.join(
                    [str(len(house.player_val_pair)) for house in self.game_houses])
        try:
            conn_socket.send(msg.encode())
        except socket.error as err:
            print("Socket sending error: ", err)
            return False
        return True

    def parse_msg(self, msg, cur_player):
        status = cur_player.status
        cur_player_room = cur_player.room
        connect_partner = True
        action = 4002
        print("in parse: ", msg)
        if (msg[0] == "/list" and len(msg) == 1):
            action = 3001

        elif (msg[0] == "/enter" and len(msg) == 2 and status == 1):
            room_no = int(msg[1])
            if not room_no or room_no <= 0 or room_no > TOTAL_ROOM:
                return action

            # calculate players ALREADY in the room
            self.lock.acquire()
            room_to_join = self.game_houses[room_no]
            players_in_room = len(room_to_join.player_val_pair)

            if players_in_room < 2:
                cur_player.join_room(room_no)
                room_to_join.add_player(cur_player)
            if players_in_room == 1:
                partner = room_to_join.find_partner(cur_player)
                cur_player.set_status(3)
                partner.set_status(3)
                connect_partner = self.send_msg(partner.conn_socket, 3012)
                if not self.check_connection(connect_partner, partner, partner.conn_socket, ["dummy"]):
                    room_to_join.reset()
                    self.lock.release()
                    return None

            self.lock.release()
            action = players_in_room + 3011

        elif (msg[0] == "/guess" and status == 3):
            if (msg[1] not in ["true", "false"]):
                return action

            self.lock.acquire()
            cur_house = self.game_houses[cur_player_room]
            cur_house.set_player_val(cur_player, int(msg[1] == "true"))
            partner = cur_house.find_partner(cur_player)
            result = cur_house.calc_game_res(cur_player)
            action = 0
            if result == -1:
                self.lock.release()
                return None
            elif result == 0:
                connect_partner = self.send_msg(partner.conn_socket, 3021)
                action = 3022
            elif result == 1:
                connect_partner = self.send_msg(partner.conn_socket, 3022)
                action = 3021
            else:
                connect_partner = self.send_msg(partner.conn_socket, 3023)
                action = 3023

            cur_house.reset()
            self.lock.release()
            cur_player.end_game()
            if not self.check_connection(connect_partner, partner, partner.conn_socket, ["dummy"]):
                return None
            else:
                partner.end_game()

        elif msg[0] == "/exit" and len(msg) == 1 and status == 1:
            cur_player.log_off()
            action = 4001

        return action


def main(argv):
    _, port, filepath = argv
    global USER_INFO

    # read user info from txt, create players
    with open(filepath) as f:
        for line in f:
            pair = line.rstrip('\n').split(':')
            USER_INFO[pair[0]] = pair[1]

    print(USER_INFO)
    # create socket and bind
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server_socket.bind(("", int(port)))
    except socket.error as err:
        print("Binding error: ", err)
        sys.exit(1)

    server_socket.listen(MAX_PLAYER_NUM)

    # start a new game from the server
    new_game = Game(server_socket)
    new_game.start_game()

    server_socket.close()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 GameServer.py <server_port> <path_to_user_file>")
        sys.exit(1)
    main(sys.argv)
