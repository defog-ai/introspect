import http.server
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver

PORT = 80

Handler = http.server.SimpleHTTPRequestHandler

Handler.extensions_map={
    '.html': 'text/html',
    '': 'text/html', # Default is 'application/octet-stream'
    }

httpd = socketserver.TCPServer(("", PORT), Handler)

print("serving at port", PORT)
httpd.serve_forever()
