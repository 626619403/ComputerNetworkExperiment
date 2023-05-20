import os
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
def main():
    authorizer = DummyAuthorizer()
    authorizer.add_user('user', '12345', 'd:\\file', perm='elradfmwMT')
    authorizer.add_anonymous('d:\\file')
    handler = FTPHandler
    handler.authorizer = authorizer
    handler.permit_foreign_addresses=True
    handler.banner = "pyftpdlib based ftpd ready."
    address = ('', 2121)
    handler
    server = FTPServer(address, handler)
    server.max_cons = 256
    server.max_cons_per_ip = 5
    server.serve_forever()
if __name__ == '__main__':
    main()