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
       4001: "Bye bye",
       4002: "Unrecognized message"
       }


class GameRoom(object):
    def __init__(self, id):
        self.id = id
        self.player_val_pair = {}   # Player obj, guessing value (default -1)
        self.rand_bool_val = -1     # -1: not set, 0: false, 1: true

    def add_player(self, cur_player):
        self.player_val_pair[cur_player] = -1

    def find_partner(self, cur_player):
        for player in self.player_val_pair:
            if player != cur_player:
                return player
        return None

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
        self.__init__(self.id)


class Player(object):
    def __init__(self, name):
        self.name = name
        self.get_initial_set()

    def get_initial_set(self):
        self.room_no = -1

        self.status = 0
        # 0 -> out of house,    1 -> in the game hall,
        # 2 -> waiting in room, 3 -> playing a game

        self.conn_socket = None
        self.partner_offline = False
        # If the player has not made a guess, and his partner leave -> partner offline = True
        # And his next sending message will be ignored, cause the return message is always 3021

    def __eq__(self, other):
        if not isinstance(other, Player):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def login(self, conn_socket):
        self.status = 1
        self.conn_socket = conn_socket

    def join_room(self, room_no):
        self.room_no = room_no
        self.status = 2

    def end_game(self):
        self.room_no = -1
        self.status = 1


class Game(object):
    def __init__(self, server_socket):
        self.lock = threading.Lock()
        self.server_socket = server_socket
        self.game_rooms = [GameRoom(id) for id in range(TOTAL_ROOM)]
        self.players = [Player(name) for name in USER_INFO]

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
                cur_room = self.game_rooms[cur_player.room_no]
                partner = cur_room.find_partner(cur_player)
            if partner:
                self.send_msg(partner.conn_socket, 3021)
                if cur_room.player_val_pair[partner] == -1:
                    partner.partner_offline = True
                partner.end_game()
        if cur_player.status >= 2:
            with self.lock:
                self.game_rooms[cur_player.room_no].reset()
        cur_player.get_initial_set()
        return False

    def handle_each_client(self, client):
        conn_socket, _ = client

        # login authentication
        auth_info = []
        connect = self.get_msg(conn_socket, auth_info)
        if not self.check_connection(connect, None, conn_socket, auth_info):
            return

        while auth_info[1] not in USER_INFO or USER_INFO[auth_info[1]] != auth_info[2]:
            connect = self.send_msg(conn_socket, 1002)
            connect &= self.get_msg(conn_socket, auth_info)
            if not self.check_connection(connect, None, conn_socket, auth_info):
                return

        for player in self.players:
            if player.name == auth_info[1]:
                cur_player = player
        cur_player.login(conn_socket)
        connect = self.send_msg(conn_socket, 1001)

        # login successful, start playing game
        while(cur_player.status != 0):
            msg = []
            connect &= self.get_msg(conn_socket, msg)
            if not self.check_connection(connect, cur_player, conn_socket, msg):
                return
            action = self.parse_msg(msg, cur_player)
            if action:
                connect = self.send_msg(conn_socket, action)

        # logout
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
                msg += str(TOTAL_ROOM) + ' ' + ' '.join(
                    [str(len(room.player_val_pair)) for room in self.game_rooms])
        try:
            conn_socket.send(msg.encode())
        except socket.error as err:
            print("Socket sending error: ", err)
            return False
        return True

    def parse_msg(self, msg, cur_player):
        status = cur_player.status
        cur_player_room_no = cur_player.room_no
        connect_partner = True
        action = 4002

        if cur_player.partner_offline:
            cur_player.partner_offline = False
            return None

        if (msg[0] == "/list" and len(msg) == 1):
            action = 3001

        elif (msg[0] == "/enter" and len(msg) == 2 and status == 1):
            try:
                room_no = int(msg[1]) - 1
            except:
                return action
            if room_no < 0 or room_no >= TOTAL_ROOM:
                return action

            # calculate players ALREADY in the room
            self.lock.acquire()
            room_to_join = self.game_rooms[room_no]
            players_in_room = len(room_to_join.player_val_pair)

            if players_in_room < 2:
                cur_player.join_room(room_no)
                room_to_join.add_player(cur_player)
            if players_in_room == 1:
                partner = room_to_join.find_partner(cur_player)
                cur_player.status = 3
                partner.status = 3
                if not self.send_msg(partner.conn_socket, 3012):
                    self.lock.release()
                    return None

            self.lock.release()
            action = players_in_room + 3011

        elif (msg[0] == "/guess" and status == 3):
            if (msg[1] not in ["true", "false"]):
                return action

            self.lock.acquire()
            cur_player_room = self.game_rooms[cur_player_room_no]
            cur_player_room.player_val_pair[cur_player] = int(msg[1] == "true")
            partner = cur_player_room.find_partner(cur_player)
            if not partner:
                self.lock.release()
                return None
            result = cur_player_room.calc_game_res(cur_player)
            # wait for partner
            if result == -1 or not self.send_msg(partner.conn_socket, 3021+result):
                self.lock.release()             # no partner
                return None
            if result == 2:                     # set action value for the current player
                action = 3023                   # tie -> 3023
            else:
                action = 3022 - result          # win or lose -> 3021 or 3022

            cur_player_room.reset()
            self.lock.release()
            cur_player.end_game()
            partner.end_game()

        elif msg[0] == "/exit" and len(msg) == 1 and status == 1:
            cur_player.get_initial_set()
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
