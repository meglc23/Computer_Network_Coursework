#!/usr/bin/python3

import os.path
import socket
import sys


def send_msg(conn_socket, msg):
    try:
        conn_socket.send(msg.encode())
    except socket.error as err:
        print("Socket sending error: ", err)
        sys.exit(1)


def get_msg(conn_socket):
    try:
        msg = conn_socket.recv(1024).decode()
    except socket.error as err:
        print("Socket recv error: ", err)
        sys.exit(1)
    print(msg)
    return msg.split()


def main(argv):
    # create socket and connect to server
    try:
        conn_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn_socket.connect((argv[1], int(argv[2])))
    except socket.error as err:
        print("Socket error: ", err)
        sys.exit(1)

    # user authentication
    success_login = False
    msg = None
    while not success_login:
        user_name = input("Please input your user name: ")
        password = input("Please input your password: ")
        send_msg(conn_socket, f"/login {user_name} {password}")
        msg = get_msg(conn_socket)
        if msg[0] == "1001":
            success_login = True

    while True:
        user_input = input()
        send_msg(conn_socket, user_input)
        msg = get_msg(conn_socket)
        if msg[0] == "4001":
            break
        elif msg[0] == "3011":
            msg = get_msg(conn_socket)

    print("Client ends")
    conn_socket.close()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 GameClient.py <server_addr> <server_port>")
        sys.exit(1)
    main(sys.argv)
