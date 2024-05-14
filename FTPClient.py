import socket as s
import os
#N.B. SI SONO TRALASCIATE NELLA DESCRIZIONE DELLE FUNZIONI LA GESTIONE DELLE ECCEZIONI E I METODI DI CHECK DEI VARI COMANDI


#Script FTP Client
def FTPClientScript():

    #INDIRIZZO SERVER
    HOST = '127.0.0.1'
    # PORTA PI SERVER PER I COMANDI
    CONTROL_SERVER_PORT = 2121


    try:
        #CREAZIONE SOCKET PER PI E CONNESSIONE
        control_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        tryToConnect(control_socket, HOST, CONTROL_SERVER_PORT)
        print(control_socket.recv(1024).decode())

        #INSERIMENTO CREDENZIALI
        print(control_socket.recv(1024).decode())
        username = input("Username: ")
        control_socket.send(f"{username}".encode())

        if username != "anonymous":
            print(control_socket.recv(1024).decode())
            password = input("Password: ")
            control_socket.send(f"{password}".encode())

        print(control_socket.recv(1024).decode())


        while True:
            #INVIO COMANDO AL SERVER
            command = input("Enter FTP command (e.g., LIST, RETR filename, QUIT): ").strip().upper()
            control_socket.send(command.encode())
            if command.startswith("LIST"):
                #SE COMANDO LIST, CREAZIONE DI UN SOCKET PER DTP CON LA PORTA INVIATA DAL SERVER
                data_port = int(control_socket.recv(1024).decode('utf-8'))
                data_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
                data_socket.connect((HOST, data_port))
                response = data_socket.recv(4096).decode()
                print(response)
                data_socket.close()
            elif command == "QUIT":
                break
            elif command.startswith('RETR'):
                #SE COMANDO RETR, CREAZIONE DI UN SOCKET PER DTP CON LA PORTA INVIATA DAL SERVER
                # E SCRITTURA DEI DATI RICEVUTI DAL FILE RICHIESTO SU UN NUOVO FILE
                data_port = int(control_socket.recv(1024).decode('utf-8'))
                data_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
                data_socket.connect((HOST, data_port))
                with open(os.path.abspath(command.split(" ")[1].lower()), 'wb') as file:
                    data = data_socket.recv(1024)
                    while data:
                        file.write(data)
                        data = data_socket.recv(1024)
                data_socket.close()
                response = control_socket.recv(4096).decode()
                print(response)
                print(f"File '{command.split(" ")[1]}' downloaded correctly.")
            elif command.startswith('STOR'):
                #SE COMANDO STOR, CREAZIONE DI UN SOCKET PER DTP CON LA PORTA INVIATA DAL SERVER
                # E INVIO DEI DATI DEL FILE SELEZIONATO AL SERVER
                data_port = int(control_socket.recv(1024).decode('utf-8'))
                data_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
                data_socket.connect((HOST, data_port))
                with open(command.split(" ")[1].lower(), 'rb') as file:
                    f = file.read()
                    data_socket.sendall(f)
                data_socket.close()
                response = control_socket.recv(4096).decode()
                print(response)
            else:
                response = control_socket.recv(4096).decode()
                print(response)



    except Exception as e:
        print("Error", e)
    finally:
        # Chiudi la socket di controllo
        control_socket.close()




def tryToConnect(socket: s.socket, address: str, port: int):
    try:
        socket.connect((address, port))
        print("Connection estabilished")
    except:
        print("Connection not estabilished. Impossible to find Server on port: ", port)

FTPClientScript()