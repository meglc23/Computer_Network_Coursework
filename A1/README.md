### Assignment 1: A Simple Game House Application

* This project is based on Python socket programming, where the client establishes TCP connections with the server programme. It includes the functions of a user querying game room information, entering a game room, and playing with other users.
* The programme should be run on Python 3.6+, and is only tested on MacOS environment.
* The game is implemented by OOP so that the methods are clear, though the programme may seem long. I guess it is better to separate the public and private members, but I just don't want to do that now.
* The two players in the same game room, as well as the room itself, can access each other in _O(1)_ time.
* The game house has default 10 total rooms, and allows 100 users to connect simultaneously. The variables _TOTAL_ROOM_ and _MAX_PLAYER_NUM_ can be altered in the server programme. 