# -*- coding: utf-8 -*-
from socket import *
import sys
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import os
import threading

ip = ''
port = 8888
backlog = 5
hashmap = {}
thread_count = 5
timeout = 10

def stripend(message):
    return message.split("/",1)[0]

def getref(message):
    lines = message.splitlines()
    for line in lines:
        #if line starts with "Referer: "
        if(line.startswith("Referer:")):
            r = line.split(str(port)+"/", 1)[1]
            r = stripend(r)
            print("referer: "+ r)
            return(r)
    return("")

def http_parse(message):
    try:
        referer = getref(message)
        lines = message.splitlines()
        rlist = []
        request = lines[0].split()[1]
        if(len(referer)):
            address = referer
        else:
            rlist = request.split("/", 2);
            address = rlist[1];
            if(len(rlist)==2): #if just a url w/o file
                request = "/index.html"
            else:
                request = "/"+rlist[2];
        if(request.startswith("/"+address)):
            request = request.split("/"+address,1)[1]
        request = add_index(request)
        cachename = address + request #www.example.com/index.html
        #print([request, address, cachename])
        cachename = "./cache/"+cachename
        return [request, address, cachename]
    except Exception as e:
        print(e)
        return None

def web_get(filename, address, cachename, modby):
    requestSock = socket(AF_INET, SOCK_STREAM)
    try:
        requestSock.connect((address.replace("www.",""),80))
        fileobj = requestSock.makefile('r',0)
        getr = "GET "+filename+" HTTP/1.0\n"
        hostr = "Host: "+address+"\n"
        modr=""
        if (modby != 0):
            modr="If-Modified-Since: "+modby+"\n"
        print(getr+hostr+modr)
        fileobj.write(getr+hostr+modr+"\n")
        rpage = ""
        while 1:
            newread = fileobj.read(1024)
            if not newread:
                break
            rpage += newread
        return rpage
    except Exception as e:
        print(e)
        return None

def date_mod(f):
    date = ""
    lines = f.splitlines()
    for line in lines:
        if line is None:
            break
        if(line.startswith("Date: ")):
            date = line[6:]
            date = date.partition("\n")[0]
            break
    if(date == ""):
        date = datetime.now()
    return date

#creates directory for file
#returns a file object
def cache_file(cachename, f):
    #this part is a bit unclear so I will give example
    #if cachename = www.example.com/file/index.html
    #this region of code will end with
    #end = index.html
    #path = www.example.com/file/
    c = cachename[::-1] #reverses string
    split = c.partition("/")
    end = split[0][::-1]
    path = split[2][::-1]+"/"
    #end of confusing region
    print("begin = "+path)
    print("end = "+end)
    #checks if path exists and makes one if not
    if not os.path.exists(os.path.dirname(path)): 
        os.makedirs(os.path.dirname(path))
    try:
        tmpFile = open(cachename,'wb')
        tmpFile.write(f)
        hashmap[cachename] = date_mod(f)
    except Exception as e:
        print(e)

def echeck(page):
    lines = page.splitlines()
    if(len(lines)<2 or len(lines[0].split())<2):
        return -1
    else:
        return int(lines[0].split()[1])

def find_and_send(filename, address, cachename, tcpCliSock):
    f = open(cachename,'r')
    try:
        while 1:
            line = f.read(1024)
            if line is None:
                break
            tcpCliSock.sendall(line)
    except Exception as e:
        print(e)

def update_cache(filename, address, cachename):
    mod = hashmap[cachename]
    page = web_get(filename, address, cachename, mod)
    errno = echeck(page)
    if(errno == 200):
        f = open(cachename, 'wb')
        f.write(page)

#returns described file - either from cache or further
def cache_send(filename, address, cachename, tcpCliSock):
    finished_page = ""
    if(cachename in hashmap):
        #get it from cache
        update_cache(filename, address, cachename) #will update file
        find_and_send(filename, address, cachename, tcpCliSock)
    else:
        page = web_get(filename, address, cachename,0)
        errno = echeck(page)
        print("errno ="+str(errno))
        if(errno == 200):
            cache_file(cachename, page)
            tcpCliSock.sendall(page)
        else:
            tcpCliSock.sendall(page)
            #do other stuff with different errors

def add_index(cachename):
    if (cachename[len(cachename)-1] == "/"):
        cachename += "index.html"
    return cachename

def t_start(tcpCliSock, addr):
    try:
        message = tcpCliSock.recv(4096)
        if(message is None):
            return
        if(len(message.splitlines())<2):
            return
        if(message.splitlines()[0].split()[0] != "GET"):
            return
        print(message)
        r = http_parse(message)
        if r is None:
            return
        filename, address, cachename = r
        print("filename: " + filename)
        print("hostname: " + address)
        print("cachename: " + cachename)
        cache_send(filename, address, cachename,tcpCliSock)
        tcpCliSock.close()
    except Exception as e:
        print(e)
        tcpCliSock.close()
       
def main():
    tcpSerSock = socket(AF_INET, SOCK_STREAM)
    tcpSerSock.bind((ip,port))
    tcpSerSock.listen(backlog)
    while 1:
        print('Ready to serve...')
        tcpCliSock, addr = tcpSerSock.accept()
        tcpCliSock.settimeout(timeout)
	print('Received a connection from:', addr)
        t = threading.Thread(target=t_start, args=(tcpCliSock, addr))
        t.daemon = True
        t.start()
    tcpSerSock.close()

main()
