#!/usr/bin/python

import SocketServer
import socket
import io
import sys
import os
import threading
import struct
import random
import time

# server ip & port
HOST = "140.113.27.40"
PORT = 60007
DATA_PORT = 60005
CRLF = "\r\n"

# bytestream
bs = None

# the value is between [0 - PLAY - 1 - PAUSE - 0]
playing = 0
# the value is between [1 - SETUP - 0 - TEARDOWN - 1]
teardown = 1
# jpeg fram counter
jpeg_n = 0
client_ip = ''



def rtsp_cmd_gen (req, args) :
    """
    generate rtsp protocol request command string
    Ref. http://en.wikipedia.org/wiki/Real_Time_Streaming_Protocol
    """

    # the reqest command should be upper caseed
    req = req.upper()

    if req == 'SETUP':
        return ('RTSP/1.0 200 OK' + CRLF +
                'CSeq: ' + args['CSeq'] + CRLF +
                'Session: ' + args['Session'] + CRLF)
    elif req == 'PLAY':
        return ('RTSP/1.0 200 OK' + CRLF +
                'CSeq: ' + args['CSeq'] + CRLF)
    elif req == 'PAUSE':
        return ('RTSP/1.0 200 OK' + CRLF +
                'CSeq: ' + args['CSeq'] + CRLF)
    elif req == 'TEARDOWN':
        return ('RTSP/1.0 200 OK' + CRLF +
                'CSeq: ' + args['CSeq'] + CRLF)
    if not req in ["SETUP", "PLAY", "PAUSE", "TEARDOWN"]:
        print "unimplemented"
        return ""

    return req


def decode(buf):
    """
    decode my RTSP header
    """
    s = buf.split(CRLF)
    if 'SETUP' in buf[0:5]:
        return {'type' : 'SETUP',
                'file' : s[0][6:-9],
                'CSeq' : s[1][6:]}

    elif 'PLAY' in buf[0:4]:
        return {'type' : 'PLAY',
                'file' : s[0][5:-9],
                'CSeq' : s[1][6:],
                'Session' : s[2][9:]}

    elif 'PAUSE' in buf[0:5]:
        return {'type' : 'PAUSE',
                'file' : s[0][6:-9],
                'CSeq' : s[1][6:],
                'Session' : s[2][9:]}
    elif 'TEARDOWN' in buf[0:8]:
        return {'type' : 'TEARDOWN',
                'file' : s[0][9:-9],
                'CSeq' : s[1][6:],
                'Session' : s[2][9:]}
    else:
        return None



def linesplit(sock):
    """
    split line from receiving data
    """
    BUFSIZ = 32
    buf = ""
    done = False

    try:
        buf = sock.recv(BUFSIZ)
    except:
        pass

    while not done:
        if CRLF in buf:
            (line, buf) = buf.split(CRLF, 1)
            yield line+CRLF
        else:
            try:
                more = sock.recv(BUFSIZ)
                if not more:
                    done = True
                else:
                    buf = buf+more
            except:
                pass
    if buf:
        yield buf



def is_protocol(s):
    """
    is the string a valid protocol type
    """
    if 'SETUP' in s[0:5] or 'PLAY' in s[0:4] or \
       'PAUSE' in s[0:5] or 'TEARDOWN' in s[0:8] or \
       'CSeq'  in s[0:4] or 'Session' in s[0:7] or \
       'Transport' in s[0:9]:
        return True
    return False



class thread_player(threading.Thread):
    """
    the mjpeg decoder and player, run on another thread from the TCP server
    """
    def __init__(self):
        threading.Thread.__init__(self)
        self.stop_event = threading.Event()

    def set_sock(self):
        global HOST, DATA_PORT

        # set frame stream socket (UDP)
        self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.data_socket.bind((HOST, DATA_PORT))

        # this need to recv "UDP!"
        self.client_udp = self.data_socket.recvfrom(128)
        print self.client_udp
        self.client_udp = self.client_udp[1]


    def run(self):
        global teardown, jpeg_n

        jpeg_n = 0
        print "start thread!"
        while not teardown:
            self.on_play()
        print "end thread!"

        # release resources
        self.bos.close()
        self.bosi.close()
   

    def on_play(self):
        global bs, playing, teardown, jpeg_n
        global client_ip, DATA_PORT

        # 30 FPS?
        time.sleep(0.033)

        if playing and not teardown:
            l = ''
            try:
                # according to the mjpeg format
                # read 5 bit as a string for the next frame length
                for i in struct.unpack('5c', bs.read(5)):
                    l += i
                l = int(l)
                if l <= 0:
                    return

                # next jpeg frame
                jpeg_n += 1
                # write it in to a jpeg file
                self.bosi = io.open('frame{}.jpg'.format(jpeg_n), 'wb')
                self.bos = io.BufferedWriter(self.bosi)

                # RTP packet data
                _V, _P, _X, _CC, _M, _PT = 2, 0, 0, 0, 0, 26
                _ts = int(time.time())
                hdr = _V | _P << 2 | _X << 3 | _CC << 4
                hdr2 = _M | _PT << 1

                print "decode {} frame : len {}".format(jpeg_n, l)
                frame = bs.read(l)
                self.bos.write(frame)
                self.data_socket.sendto(struct.pack("BBHII", hdr, hdr2, jpeg_n, _ts, l), self.client_udp)
                self.data_socket.sendto(frame, self.client_udp)

            # blahblahblah
            except ValueError:
                print "on exp valerr"
                print hdr, type(hdr)
            except IOError:
                print "IO"
                # ignore QQ
                pass
            except:
                playing = 0
                print "Hmm", sys.exc_info()[0]

    def stop(self):
        # shutdown the socket
        self.data_socket.close()
        self.stop_event.set()


class MyHandler (SocketServer.BaseRequestHandler):
    """
    the RTSP server
    """
    def handle (self):
        global bs 
        global playing, teardown
        global client_ip

        client_ip, client_port = self.client_address

        print "ip, port => {} : {}".format(client_ip, client_port)

        self.pro_buf = ""
        line_count = 0
        # recieving line by line
        for line in linesplit(self.request):
            self.data = line.strip()
            if not teardown:
                # is the thread player alive()
                #print "is alive? ", p.is_alive()
                pass

            if is_protocol(self.data):
                self.pro_buf += self.data + CRLF
                if line_count < 2:
                    line_count += 1
                else:
                    # what protocol?
                    protocol = decode(self.pro_buf)
                    if protocol['type'] == 'SETUP':
                        print "setup"

                        # open the file
                        f = io.open('movie.mjpeg', 'rb')
                        bs = io.BufferedReader(f)
                        print bs

                        self.request.sendall(rtsp_cmd_gen('SETUP', 
                            {'CSeq' : protocol['CSeq'],
                             'Session' : str(random.randint(100000, 999999))}))

                        playing, teardown = 0, 0

                        # launch the player on another thread
                        p = thread_player()
                        p.set_sock()
                        print p.client_udp
                        p.start()


                    elif protocol['type'] == 'PLAY':
                        print "play"
                        playing = 1

                        self.request.sendall(rtsp_cmd_gen('PLAY', 
                            {'CSeq' : protocol['CSeq']}))

                    elif protocol['type'] == 'PAUSE':
                        print "pause"
                        playing = 0

                        self.request.sendall(rtsp_cmd_gen('PAUSE', 
                            {'CSeq' : protocol['CSeq']}))

                    elif protocol['type'] == 'TEARDOWN':
                        print "teardown"
                        print "close file:", bs

                        # close file handles
                        bs.close()
                        f.close()
                        teardown = 1

                        self.request.sendall(rtsp_cmd_gen('TEARDOWN', 
                            {'CSeq' : protocol['CSeq']}))

                        # stop the player
                        p.stop()

                    else:
                        print "you don't say  @_@?"

                    self.pro_buf = ""
                    line_count = 0

            else:
                print "What!!!!", line


        # yooooooooooooooooo!
        print "yo!"



if __name__ == "__main__":
    print "server Runs on", HOST, ":", PORT

    server = SocketServer.TCPServer((HOST, PORT), MyHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()

