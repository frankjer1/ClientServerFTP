import os
import socket as s

#N.B. SI SONO TRALASCIATE NELLA DESCRIZIONE DELLE FUNZIONI LA GESTIONE DELLE ECCEZIONI E I METODI DI CHECK DEI VARI COMANDI



#Script FTP Server
def FTPServerScript():

    PUBLIC_DIRECTORY = "public"
    USERS_DIRECTORY = "documents"
    HOST: str = "127.0.0.1"
    CONTROL_PORT: int =  2121
    DATA_PORT: int =  2122

    #CREAZIONE SOCKET PER PI
    control_socket = create_server_socket(HOST, CONTROL_PORT, 5)
    print("FTP server listening on port ", CONTROL_PORT)

    while True:
        #ACCETTAZIONE DI UNA CONNESSIONE DAL CLIENT
        control_conn, control_client_addr = control_socket.accept()
        print("Connected to ", control_client_addr)
        control_conn.send(b"220 Welcome to FTP server\r\n")
        
        #AUTENTICAZIONE
        authenticated, user_directory = handle_user_login(control_conn, PUBLIC_DIRECTORY, USERS_DIRECTORY)
        if not authenticated:
            control_conn.close()
            continue
        else:

            while True:
                #RICEZIONE COMANDO DAL CLIENT: AD OGNI COMANDO C'E' UN CHECK DEI PERMESSI DELL'UTENZA E IN CASO DI
                #ESITO POSITIVO SI PROCEDE CON L'OPERAZIONE SELEZIONATA
                command = control_conn.recv(4096).decode().strip()
                print(command)
                if command == "QUIT":
                    control_conn.send(b"221 Goodbye.\r\n")
                    control_conn.close()
                    break
                elif command.startswith("LIST"):
                    if not checkDirectoryPermission(user_directory, command):
                        control_conn.send(b"550 Permission denied.\r\n")
                        continue
                    else:
                        control_conn.send(b"330 Proceeding with the request...\r\n")
                    listFiles(HOST, DATA_PORT, control_conn, user_directory)
                elif command.startswith("RNFR"):
                    if not checkDirectoryPermission(user_directory, command) or user_directory == "public":
                        control_conn.send(b"550 Permission denied.\r\n")
                        continue
                    else:
                        control_conn.send(b"330 Proceeding with the request...\r\n")
                    renameFile(command.split(" ")[1].lower(), control_conn)
                elif command.startswith("DELE"):
                    if not checkDirectoryPermission(user_directory, command) or user_directory == "public":
                        control_conn.send(b"550 Permission denied.\r\n")
                        continue
                    else:
                        control_conn.send(b"330 Proceeding with the request...\r\n")
                    removeFile(command.split(" ")[1].lower(), control_conn)
                elif command.startswith("RETR"):
                    if not checkDirectoryPermission(user_directory, command):
                        control_conn.send(b"550 Permission denied.\r\n")
                        continue
                    else:
                        control_conn.send(b"330 Proceeding with the request...\r\n")
                    download(command.split(" ")[1].lower(), HOST, DATA_PORT, control_conn, user_directory)
                elif command.startswith("STOR"):
                    if user_directory == "public":
                        control_conn.send(b"550 Permission denied.\r\n")
                        continue
                    else:
                        control_conn.send(b"330 Proceeding with the request...\r\n")
                    upload(user_directory, HOST, control_conn, DATA_PORT, os.path.basename(command.split(" ")[1].lower()))
                else:
                    control_conn.send(b"500 Unknown command.\r\n")

    
#Questa funzione crea una nuova socket TCP e le associa indirizzo e porta,
#per poi metterla in ascolto con maxQueue possibili connessioni in coda.
def create_server_socket(address: str, port: int, maxQueue: int):
    new_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
    new_socket.bind((address, port))
    new_socket.listen(maxQueue)
    return new_socket

#QUESTA FUNZIONE CREA UN SOCKET PER DTP E MANDA IL VALORE DELLA PORTA DATI AL CLIENT. SUCCESSIVAMENTE
#ESTRAE LA LISTA DEI FILE DALLA USER DIRECTORY E LA INVIA AL CLIENT
def listFiles(host: str, data_port: int, control_conn: s.socket, user_directory: str):
    data_socket = create_server_socket(host, data_port, 1)
    control_conn.send(str(data_port).encode('utf-8'))
    try:
        data_conn, data_address = data_socket.accept()
        files = os.listdir(os.path.abspath(user_directory))
        data_conn.sendall('\r\n'.join(files).encode() + b'\r\n')
        control_conn.send(b"250 Files retrieved with success.\r\n")
    except Exception as e:
        print("error: ", e)
        control_conn.send(b"Error: Impossible to retrieve files list.\r\n")
    finally:
        data_conn.close()
        data_socket.close()


#AUTENTICAZIONE CON ASSOCIAZIONE DELLE DIRECTORY ASSEGNATE AI RISPETTIVI UTENTI
def handle_user_login(control_client_conn: s.socket, publicDirectory: str, UsersDirectory: str):
    control_client_conn.send(b"331 Please specify the username.\r\n")
    username = control_client_conn.recv(1024).decode().strip()
    if username != "anonymous":
        control_client_conn.send(b"331 Please specify the password.\r\n")
        password = control_client_conn.recv(1024).decode().strip()
    if username == "anonymous":
        control_client_conn.send(b"230 Welcome, anonymous user. Your root directory is \"public\"\r\n")
        return True, publicDirectory 
    elif check_credentials(username, password):
        control_client_conn.send(b"230 User logged in, proceed. your root directory is \"documents\"\r\n")
        return True, UsersDirectory
    else:
        control_client_conn.send(b"530 Login incorrect.\r\n")
        return False, None


def check_credentials(username, password):
    if username == "admin" and password == "pass":
        return True  
    else:
        return False

#FUNZIONE DI CONTROLO DEI PERMESSI SULLA VISIBILITA' DELLE DIRECTORIES
def checkDirectoryPermission(directoryPath: str, command: str):
    if command.split(" ")[1].lower() == directoryPath:
        return True
    else:
        relative_path = os.path.join(directoryPath, command.split(" ")[1].lower())
        if os.path.abspath(directoryPath) in os.path.abspath(relative_path) and os.path.exists(os.path.abspath(relative_path)):
            return True
        else:
            return False
    
#FUNZIONE DI RENAME: E' DIVISA IN DUE PARTI, OVVERO LA PRIMA IN CUI VIENE RICEVUTA RICHIESTA DI RIDENOMINAZIONE DI UN CERTO FILE
# E LA SECONDA IN CUI VIENE FORNITO DAL CLIENT IL NUOVO NOME E VIENE ULTIMATA L'OPERAZIONE   
def renameFile(oldFilename: str, conn_socket: s.socket):
    relative_old_path = os.path.join("documents", oldFilename)
    if os.path.exists(os.path.abspath(relative_old_path)):
        conn_socket.send(b"350 Requested file action pending further information.")
        command = conn_socket.recv(1024).decode().strip()
        relative_new_path = os.path.join("documents", command.split(" ")[1].lower())
        try:
            os.rename(os.path.abspath(relative_old_path), os.path.abspath(relative_new_path))
            conn_socket.send(b"250 File has been renamed.\r\n")           
        except Exception as e:
            print("error: ", e)
            conn_socket.send(b"500 Error: Impossible to rename file.\r\n")
    else:
        conn_socket.send(b"404 File does not exist.\r\n")

#FUNZIONE DI RIMOZIONE DI UN CERTO FILE
def removeFile(filename: str, conn_socket: s.socket):
    relative_path = os.path.join("documents", filename)
    if os.path.exists(os.path.abspath(relative_path)):
        try:
            os.remove(os.path.abspath(relative_path))
            conn_socket.send(b"250 File has been removed.\r\n")           
        except Exception as e:
            print("error: ", e)
            conn_socket.send(b"500 Error: Impossible to remove file.\r\n")
    else:
        conn_socket.send(b"404 File does not exist.\r\n")

#QUESTA FUNZIONE CREA UN SOCKET PER DTP E MANDA IL VALORE DELLA PORTA DATI AL CLIENT. SUCCESSIVAMENTE
#LEGGE I DATI DAL FILE RICHIESTOE E INVIA IL TUTTO AL CLIENT.
def download(filename: str, host: str, data_port: int, control_conn: s.socket, user_directory: str):
    relative_path = os.path.join(user_directory, filename)
    if os.path.exists(os.path.abspath(relative_path)):
        data_socket = create_server_socket(host, data_port, 1)
        control_conn.send(str(data_port).encode('utf-8')) 
        try:
            data_conn, data_address = data_socket.accept()
            with open(os.path.abspath(relative_path), 'rb') as f:
                file = f.read()
                data_conn.sendall(file)
                data_conn.close()
            data_socket.close() 
            control_conn.send(b"250 File downloaded with success.\r\n")         
        except Exception as e:
            print("error: ", e)
            control_conn.send(b"500 Error: Impossible to download file.\r\n")
    else:
        control_conn.send(b"404 File does not exist.\r\n")
#QUESTA FUNZIONE CREA UN SOCKET PER DTP E MANDA IL VALORE DELLA PORTA DATI AL CLIENT. SUCCESSIVAMENTE
#LEGGE I DATI INVIATI DAL CLIENT E LI SCRIVE SU UN NUOVO FILE
def upload(user_directory: str, host: str, control_conn: s.socket, data_port: int, filename: str):
    path = os.path.abspath(user_directory)
    filepath = os.path.join(path, filename)
    data_socket = create_server_socket(host, data_port, 1)
    control_conn.send(str(data_port).encode('utf-8'))
    try:
        data_conn, data_address = data_socket.accept()
        with open(filepath, 'wb') as file:
                data = data_conn.recv(1024)
                while data:
                    file.write(data)
                    data = data_conn.recv(1024)
                data_conn.close()
        data_socket.close()
        control_conn.send(b"250 File uploaded correctly.\r\n")
    except Exception as e:
            print("error: ", e)
            control_conn.send(b"500 Error: Impossible to upload file.\r\n")
    


FTPServerScript()



