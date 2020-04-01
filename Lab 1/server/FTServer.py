#!/usr/bin/python3

import socket
import sys

def main(argv):
    # get port number from argv
    serverPort = int(argv[1])
   
    # create socket and bind
    sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        sockfd.bind( ("", serverPort) )
    except socket.error as err:
        print("Binding error: ", err)
        sys.exit(1)
    
    sockfd.listen(5)
    
    print("The server is ready to receive")
    
    while True:
        
        # accept new connection
        try:
            conn, addr = sockfd.accept()     
        except socket.error as err:
            print("Accept error: ", err)
            conn.send(b"ERROR")
            continue
        
        # receive file name/size message from client 
        try:
            fname_fsize = conn.recv(1024)
        except socket.error as err:
            print("Recv error: ", err)
            conn.send(b"ERROR")
            continue
        
        #use Python string split function to retrieve file name and file size from the received message
        fpair = fname_fsize.decode().split(":")
        fname, filesize = fpair[0], fpair[1]
        
        print("Open a file with name \'%s\' with size %s bytes" % (fname, filesize))
        
        #create a new file with fname
        try:
            fd = open(fname, 'wb')
        except OSError:
            print ("Could not write file: ", fname)
            conn.send(b"ERROR")
            continue
        
        remaining = int(filesize)

        conn.send(b"OK")

        print("Start receiving . . .")
        while remaining > 0:
            # receive the file content into rmsg and write into the file
                        
            try:
                rmsg = conn.recv(1024)
            except socket.error as err:
    	        print("Recv error: ", err)

            if rmsg:
                fd.write(rmsg)
                remaining -= len(rmsg)
            else:
                print("Connection is broken")
                break

        print("[Completed]")
        fd.close()
        conn.close()
        
    sockfd.close()
    

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 FTServer.py <Server_port>")
        sys.exit(1)
    main(sys.argv)