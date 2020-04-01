#!/usr/bin/python3

import socket
import os.path
import sys

def main(argv):

	# open the target file; get file size
	try:
		fsize = os.path.getsize(argv[3])
	except os.error as emsg:
		print("File error: ", emsg)
		sys.exit(1)

	fd = open(argv[3], 'rb')

	# create socket and connect to server
	try:
		sockfd = socket.socket()
		sockfd.connect((argv[1], int(argv[2])))
	except socket.error as emsg:
		print("Socket error: ", emsg)
		sys.exit(1)

	# once the connection is set up; print out 
	# the socket address of your local socket
	print("Connection established. My socket address is", sockfd.getsockname())

	# send file name and file size as one string separate by ':'
	# e.g., socketprogramming.pdf:32341
	msg = argv[3]+':'+str(fsize)
	sockfd.send(msg.encode('ascii'))

	# receive acknowledge - e.g., "OK"
	rmsg = sockfd.recv(50)

	if rmsg != b"OK":
		print("Received a negative acknowledgment")
		sys.exit(1)

	# send the file contents
	print("Start sending ...")
	remaining = fsize
	while remaining > 0:
		smsg = fd.read(1000)
		mlen = len(smsg) 
		if mlen == 0:
			print("EOF is reached, but I still have %d to read !!!" % remaining)
			sys.exit(1)
		try:
			sockfd.send(smsg)
		except socket.error as emsg:
			print("Socket sendall error: ", emsg)
			sys.exit(1)
		remaining -= mlen
		#print("Send one block of length %d bytes" % mlen)

	# close connection
	print("[Completed]")
	fd.close()
	sockfd.close()

if __name__ == '__main__':
	if len(sys.argv) != 4:
		print("Usage: python3 FTClient.py <Server_addr> <Server_port> <filename>")
		sys.exit(1)
	main(sys.argv)