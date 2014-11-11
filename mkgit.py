#!/usr/bin/python

import os
import sys
import shutil
import smtplib
import email.utils, email.mime.multipart, email.mime.application, email.mime.text
import SimpleHTTPServer
import SocketServer
from SimplePostHandler import SimplePostHandler
import urlparse
import simplejson
import posixpath
import BaseHTTPServer
import urllib
import cgi
import shutil
import mimetypes
from StringIO import StringIO
import mkgit_conf

hostname = mkgit_conf.hostname
port = mkgit_conf.port
path = mkgit_conf.path
mailfrom = mkgit_conf.mailfrom
mailto = mkgit_conf.mailto
mailtos = mailto.split(';')
mailserver = mkgit_conf.mailserver
mailport = mkgit_conf.mailport
mailuser = mkgit_conf.mailuser
mailpasswd = mkgit_conf.mailpasswd

__version__ = '0.1'

class SimplePostHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    server_version = "SimplePostServer/" + __version__

    def do_GET(self):
        self.send_head()
        self.wfile.write('Nothing happened.')

    def do_POST(self):
        self.send_head()
        ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
        print(ctype)
        if ctype == 'multipart/form-data':
            postvars = cgi.parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers.getheader('content-length'))
            postvars = cgi.parse_qs(self.rfile.read(length))
        elif ctype == 'application/json':
            length = int(self.headers.getheader('content-length'))
            postvars = simplejson.loads(self.rfile.read(length))            
        else:
            postvars = {}
        text = post(postvars)
        self.wfile.write(text)

    def send_head(self):
        self.send_response(200)
        self.send_header("Content-type", 'text/plain')
        self.end_headers()

def basename(remote):
    return remote[remote.rfind('/')+1:-4]

def make(remote):
    os.system('git clone %s %s' % (remote,path))
    os.chdir(path)
    os.system('make')

def cleanup():
    shutil.rmtree(path)

def send(remote, message):
    outer = email.mime.multipart.MIMEMultipart()
    outer['Subject'] = basename(remote)
    outer['From'] = mailfrom
    outer['To'] = mailto
    outer.preamble = 'Your mail reader does not support MIME.\n'
    msg = email.mime.text.MIMEText(message)
    outer.attach(msg)
    pdf = open('%s/%s.pdf' % (path, basename(remote)), 'rb')
    msg = email.mime.application.MIMEApplication(pdf.read(), _subtype = 'pdf')
    pdf.close()
    outer.attach(msg)
    mailtext = outer.as_string()
    print('Sending mail...')
    server = smtplib.SMTP(host = mailserver, port = mailport)
    server.starttls()
    server.login(mailuser, mailpasswd)
    failed = server.sendmail(mailfrom, mailtos, mailtext)
    server.quit()
    if failed:
        print('Sending failed for:', failed)
    else:
        print('Sent mail.')

def post(form):
    if os.fork() != 0:
        return 'Done.'
    message = ''
    repository = form['repository']
    remote = repository['url']
    commits = form['commits']
    message = 'The repository\n\n%s\n\nreceived the following commits:\n' % remote
    for commit in commits:
        message += '\nid: %s\nmessage:\n%s\n\ntimestamp: %s\nauthor: %s (%s)\n' %\
            (commit['id'],
             commit['message'],
             commit['timestamp'],
             commit['author']['name'],
             commit['author']['email'])
    message += '\nThe current pdf file is attached.'
    make(remote)
    send(remote, message)
    cleanup()
    sys.exit(0)

httpd = SocketServer.TCPServer((hostname, port), SimplePostHandler)
httpd.serve_forever()
