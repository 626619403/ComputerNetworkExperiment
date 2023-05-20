import os
import socket
import time

host=''
def send_cmd(sock, cmd):
    sock.sendall(f"{cmd}\r\n".encode())
    time.sleep(0.2)
    response = sock.recv(4096).decode()
    return response

def get_data_socket(sock, use_passive):
    if use_passive:
        send_cmd(sock, "PASV")
        sock.sendall(f"PASV\r\n".encode())
        response = sock.recv(4096).decode()
        ip_and_port = response.split("(")[1].split(")")[0].split(",")
        ip = ".".join(ip_and_port[:4])
        port = int(ip_and_port[4]) * 256 + int(ip_and_port[5])
        if ip.startswith('192'):
            ip=host
        data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_sock.connect((ip, port))
    else:
        data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        data_sock.bind(("0.0.0.0", 0))
        data_sock.listen(1)
        ip = socket.gethostbyname(socket.gethostname())
        ip_and_port = ",".join(ip.split(".") + [str(data_sock.getsockname()[1] // 256), str(data_sock.getsockname()[1] % 256)])
        send_cmd(sock, f"PORT {ip_and_port}")
        data_sock, _ = data_sock.accept()
    return data_sock

def ftp_connect(host, username, password):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, 2121))
    print(sock.recv(4096).decode())
    send_cmd(sock, f"USER {username}")
    repos=send_cmd(sock, f"PASS {password}")
    print(repos)
    return sock


def list_directory(sock, use_passive):
    data_sock = get_data_socket(sock, use_passive)
    send_cmd(sock, "LIST")
    print(data_sock.recv(4096).decode())
    data_sock.close()

def create_directory(ctrl_sock, dir_name):
    response = send_cmd(ctrl_sock, f"MKD {dir_name}")
    print(response)
    
def get_directory(ctrl_sock):
    re=send_cmd(ctrl_sock, "PWD")
    return re.strip().split('"')[1]
    
def change_directory(ctrl_sock, path):
    response = send_cmd(ctrl_sock, f"CWD {path}")
    print(response)

def delete_file(ctrl_sock, filename):
    response = send_cmd(ctrl_sock, f"DELE {filename}")
    print(response)
    
def delete_directory(ctrl_sock, dir_name):
    response = send_cmd(ctrl_sock, f"RMD {dir_name}")
    print(response)
    
def download_file(sock, remote_file, local_file, use_passive):
    send_cmd(sock, "TYPE I")
    tmp_file = local_file + '.tmp'
    bytes_transferred = 0
    local_size = 0
    if os.path.exists(tmp_file):
        bytes_transferred = os.path.getsize(tmp_file)
    if os.path.exists(local_file):
        local_size = os.path.getsize(local_file)

    ft=os.path.exists(tmp_file)
    if local_size==0 and (not ft):
        data_sock = get_data_socket(sock, use_passive)
        re=send_cmd(sock, f"RETR {remote_file}")
        if re.startswith("550"):
            print("No such file or directory in remote files.\n")
            data_sock.close()
            return
    
        with open(tmp_file, "ab") as file:
            while True:
                data = data_sock.recv(4096)
                if not data:
                    break
                file.write(data)
        if os.path.exists(local_file):
           os.remove(local_file) 
        os.rename(tmp_file, local_file)
        print(f"finished\n")
    elif local_size > 0 and (not ft):
        print(f"This file is not blank,do you want to resume? y/n")
        while True:
            user_input = input(f" > ").strip().lower()
            cmd_parts=user_input.split()
            if len(cmd_parts) == 0:
                continue
            cmd=cmd_parts[0]
            if cmd=="n" or cmd== "N":
                break
            elif cmd=="y"or cmd=="Y":
                data_sock = get_data_socket(sock, use_passive)
                re=send_cmd(sock, f"RETR {remote_file}")
                if re.startswith("550"):
                    print("No such file or directory in remote files.\n")
                    data_sock.close()
                    return
    
                with open(tmp_file, "ab") as file:
                    while True:
                        data = data_sock.recv(4096)
                        if not data:
                            break
                        file.write(data)
                os.remove(local_file)
                os.rename(tmp_file, local_file)
                print(f"finished\n")
                break
            else:
                continue
    elif ft:
        print(f"Resuming upload from {bytes_transferred} bytes")   
        send_cmd(sock, f"REST {bytes_transferred}")
        data_sock = get_data_socket(sock, use_passive)
        re=send_cmd(sock, f"RETR {remote_file}")
        if re.startswith("550"):
            print("No such file or directory in remote files.\n")
            data_sock.close()
            return
    
        with open(tmp_file, "ab") as file:
            while True:
                data = data_sock.recv(4096)
                if not data:
                    break
                file.write(data)
        os.rename(tmp_file, local_file)
        print(f"finished\n")
        
    data_sock.close()

def upload_file(sock, local_file, remote_file, use_passive):
    send_cmd(sock, "TYPE I")
    try:
        re=send_cmd(sock, f"SIZE {remote_file}")
    except Exception as re:
        remote_size = 0
    else:
        if re.startswith("550"):
            remote_size=0
        else:    
            remote_size = int(str(re).split()[-1])
    tmp_file = remote_file + '.tmp'
    bytes_transferred = 0
    ft=False
    try:
         ret=send_cmd(sock, f"SIZE {tmp_file}")
    except Exception as re:
        bytes_transferred = 0
    else:
        if ret.startswith("550"):
            bytes_transferred=0
        else:    
            bytes_transferred = int(str(re).split()[-1])
            ft=True
            
    if (not os.path.exists(local_file)):        
        print("No such file or directory.\n")
        data_sock.close()
        return
    
    if remote_size==0 and (not ft):
        data_sock = get_data_socket(sock, use_passive)
        send_cmd(sock, f"STOR {tmp_file}")

        with open(local_file, "rb") as file:
            while True:
                data = file.read(4096)
                if not data:
                    break
                data_sock.sendall(data)
        if not re.startswith("550"):
            send_cmd(sock, f"DELE {remote_file}")
        send_cmd(sock, "RNFR {}".format(tmp_file))
        send_cmd(sock, "RNTO {}".format(remote_file))
        print(f"finished\n")
        
    elif remote_size > 0 and (not ft):
        print(f"This file is not blank,do you want to resume? y/n")
        while True:
            user_input = input(f" > ").strip().lower()
            cmd_parts=user_input.split()
            if len(cmd_parts) == 0:
                continue
            cmd=cmd_parts[0]
            if cmd=="n" or cmd== "N":
                break
            elif cmd=="y"or cmd=="Y":
                data_sock = get_data_socket(sock, use_passive)
                send_cmd(sock, f"STOR {tmp_file}")

                with open(local_file, "rb") as file:
                    while True:
                        data = file.read(4096)
                        if not data:
                            break
                    data_sock.sendall(data)
                send_cmd(sock, f"DELE {remote_file}")
                send_cmd(sock, "RNFR {}".format(tmp_file))
                send_cmd(sock, "RNTO {}".format(remote_file))
                print(f"finished\n")
                break
                
    elif ft:
        print(f"Resuming upload from {bytes_transferred} bytes")
        send_cmd(sock, f"REST {bytes_transferred}")
        data_sock = get_data_socket(sock, use_passive)
        send_cmd(sock, f"STOR {tmp_file}")

        with open(local_file, "rb") as file:
            while True:
                data = file.read(4096)
                if not data:
                    break
                data_sock.sendall(data)
        send_cmd(sock, "RNFR {}".format(tmp_file))
        send_cmd(sock, "RNTO {}".format(remote_file))
        print(f"finished\n")
        
    data_sock.close()

def print_help():
    print("Commands:")
    print("  help          - Show this help")
    print("  passive       - Use passive mode")
    print("  active        - Use active mode")
    print("  upload [path] [name] - Upload a file to the server")
    print("  mkdir [name]  - Create a directory on the server")
    print("  ls            - List the contents of the current directory")
    print("  cd [path]     - Change the current directory")
    print("  rm [file]     - Delete a file")
    print("  rmdir [dir]   - Delete a directory")
    print("  download [remote_file] [local_file] - Download a file")
    print("  quit          - Disconnect and exit")






def main():
    print("----------------welcome to FTP client!---------------\n")
    global host
    host= input("Enter the host: ").strip()
    username = input("Enter your username: ").strip()
    password = input("Enter your password: ").strip()
    
    #host = "127.0.0.1"
    #username = "user"
    #password = "12345"
    use_passive = True # Set to False for active mode
    ctrl_sock = ftp_connect(host, username, password)
    print("-----------------------------------------------------\n")

    while True:
        current_directory = get_directory(ctrl_sock)
        user_input = input(f"{current_directory} > ").strip().lower()
        cmd_parts = user_input.split()
        if len(cmd_parts) == 0:
            continue

        cmd = cmd_parts[0]

        if cmd == "help":
            print_help()
            
        elif cmd == "passive":
            use_passive = True
            print("Switched to passive mode.")
            
        elif cmd == "active":
            use_passive = False
            print("Switched to active mode.")
            
        elif cmd == "upload":
            if len(cmd_parts) != 3:
                print("Usage: upload [local_file] [remote_file]")
            else:
                file_path = cmd_parts[1]
                if not os.path.isfile(file_path):
                    print("File not found.")
                else:
                    remote_file = cmd_parts[2]
                    local_file = cmd_parts[1]
                    upload_file(ctrl_sock, local_file, remote_file, use_passive)
                    
        elif cmd == "mkdir":
            if len(cmd_parts) != 2:
                print("Usage: mkdir [name]")
            else:
                dir_name = cmd_parts[1]
                create_directory(ctrl_sock, dir_name)
                
        elif cmd == "ls":
            list_directory(ctrl_sock, use_passive)
            
        elif cmd == "cd":
            if len(cmd_parts) != 2:
                print("Usage: cd [path]")
            else:
                path = cmd_parts[1]
                change_directory(ctrl_sock, path)
                    
        elif cmd == "rm":
            if len(cmd_parts) != 2:
                print("Usage: rm [file]")
            else:
                filename = cmd_parts[1]
                delete_file(ctrl_sock, filename)
                
        elif cmd == "rmdir":
            if len(cmd_parts) != 2:
                print("Usage: rmdir [dir]")
            else:
                dir_name = cmd_parts[1]
                delete_directory(ctrl_sock, dir_name)
                
        elif cmd == "download":
            if len(cmd_parts) != 3:
                print("Usage: download [remote_file] [local_file]")
            else:
                remote_file = cmd_parts[1]
                local_file = cmd_parts[2]
                download_file(ctrl_sock, remote_file, local_file, use_passive)
        
        elif cmd == "quit":
            print("Disconnecting...")
            send_cmd(ctrl_sock, "QUIT")
            ctrl_sock.close()
            break
        
        else:
            print("Unknown command. Type 'help' for available commands.")
    
if __name__ == "__main__":
    main()


