#!/usr/bin/python

import socket
import sys
import io
import threading
import time
import struct

# glotbal variables
HOST, PORT = "140.113.27.40", 60007
DATA_PORT = 60005
CRLF = "\r\n"
GG = 0


def RTSP_cmd_gen (req, args) :
    """
    generate rtsp protocol request command string
    Ref. http://en.wikipedia.org/wiki/Real_Time_Streaming_Protocol
    """
    # the reqest command should be upper caseed
    req = req.upper()

    if req == 'SETUP':
        return ('SETUP ' + args['file'] + ' RTSP/1.0' + CRLF +
                'CSeq: ' + args['CSeq'] + CRLF +
                'Transport: RTP/AVP;unicast;client_port=' + str(DATA_PORT) + CRLF)
    elif req == 'PLAY':
        return ('PLAY '     + args['file']    + ' RTSP/1.0' + CRLF +
                'CSeq: '    + args['CSeq']    + CRLF +
                'Session: ' + args['Session'] + CRLF)
    elif req == 'PAUSE':
        return ('PAUSE '    + args['file']    + ' RTSP/1.0' + CRLF +
                'CSeq: '    + args['CSeq']    + CRLF +
                'Session: ' + args['Session'] + CRLF)
    elif req == 'TEARDOWN':
        return ('TEARDOWN ' + args['file']    + ' RTSP/1.0' + CRLF +
                'CSeq: '    + args['CSeq']    + CRLF +
                'Session: ' + args['Session'] + CRLF)

    if not req in ["SETUP", "PLAY", "PAUSE", "TEARDOWN"]:
        print "unimplemented"
        return ""

    return req


def decode(buf):
    """
    decode RTSP header
    """
    
    # split with CRLF
    s = buf.split(CRLF)

    if 'RTSP/1.0' in buf:
        if 'Session' in buf:
            return {'type' : 'SETUP', 'status' : s[0][9:],
                    'CSeq' : s[1][6:], 'Session' : s[2][9:]}
        else:
            return {'type' : 'OTHER', 'status' : s[0][9:],
                    'CSeq' : s[1][6:]}

    return None


class frame_reciever(threading.Thread):
    """
    recieve jpeg frames
    """

    def __init__(self):
        threading.Thread.__init__(self)
        self.stop_event = threading.Event()
        self.playing, self.teardown = 0, 0
        self.jpeg_n = 0
        self.data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM);
        self.setDaemon(True)

    # thread run
    def run(self):
        global HOST, DATA_PORT
        print "start thread!!"

        self.data_socket.sendto('UTP!', (HOST, DATA_PORT))

        while 1:
            self.on_play()
            time.sleep(0.001)
            if self.teardown == 1:
                break
        print "end thread!!"

    # on [PLAY, PAUSE], decode UDP packets
    def on_play(self):
        if self.playing == 1:
            try:
                # unpack raw data
                hdr1, hdr2, jpeg_n, ts, l = struct.unpack("BBHII", self.data_socket.recv(12))
                hdr1 &= 0xFF
                hdr2 &= 0xFF
                _V, _P, _X, _CC = hdr1 << 6 >> 6, hdr1 << 5 >> 7, hdr1 << 4 >> 7, hdr1 >> 4
                _M, _PT = hdr2 & 0x01, hdr2 >> 1

                # show info in the raw packet
                print "<V:{}, P:{}, X:{}, CC:{}, M:{}, PT:{}".format(_V, _P, _X, _CC, _M, _PT)
                print "<seq> => {}".format(jpeg_n)
                print "<timestamp> {} ({})".format(ts, time.ctime(ts))
                print "<frame len> => {}".format(l)

                # recv the jpeg frame
                frame = self.data_socket.recv(l)
                self.jpeg_n = jpeg_n
                self.picname = 'frame.jpg'
                bosi = io.open(self.picname, 'wb')
                bos = io.BufferedWriter(bosi)
                bos.write(frame)
                bos.close()
                bosi.close()
            except:
                pass

    
    def stop(self):
        self.data_socket.close()
        self.stop_event.set()

    def __del__(self):
        print "bye!", self.teardown


class client:
    """
    the socket client object
    """
    def __init__(self):
        # RTSP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.sock.connect((HOST, PORT))
        self.filename = ''


    def setup(self, filename):
        """
        RTSP SETUP request
        """
        # SETUP connection
        self.filename = filename
        s = RTSP_cmd_gen('SETUP', {'file' : self.filename, 'CSeq' : "123"})
        self.sock.sendall(s)

        print "[C] setup:\n", s

        received = self.sock.recv(128)
        print len(received), "Received [S] setup:\n{}".format(received)
        self.d = decode(received)
        
        if not self.d is None:
            print "[S] setup:\n", self.d['Session'], self.d['status'], self.d['CSeq']
            self.client_session = self.d['Session']
        else:
            print "[SETUP] None"

        # mjpeg frame reciever
        self.fr = frame_reciever()
        self.fr.start()

    def play(self):
        """
        RTSP PLAY request
        """
        self.fr.playing = 1

        s = RTSP_cmd_gen('PLAY', {'file' : self.filename,
                                  'CSeq' : str(int(self.d['CSeq']) + 1),
                                  'Session' : self.client_session})

        self.sock.sendall(s)
        print "[C] play:\n", s

        received = self.sock.recv(128)
        print len(received), "Received [S] play:\n{}".format(received)
        self.d = decode(received)

        if not self.d is None:
            print "[S] play: ", self.d['status'], self.d['CSeq']
        else:
            print "[PLAY] None"


        

    def pause(self):
        """
        RTSP PAUSE request
        """
        self.fr.playing = 0

        s = RTSP_cmd_gen('PAUSE', {'file' : self.filename,
                                   'CSeq' : str(int(self.d['CSeq']) + 1),
                                   'Session' : self.client_session})
        self.sock.sendall(s)
        print "[C] pause:\n", s

        received = self.sock.recv(128)
        print len(received), "Received [S] pause:\n{}".format(received)
        self.d = decode(received)

        if not self.d is None:
            print "[S] pause:", self.d['status'], self.d['CSeq']
        else:
            print "[PAUSE] None"


    def teardown(self):
        """
        RTSP TEARDOWN request
        """
        s = RTSP_cmd_gen('TEARDOWN', {'file' : self.filename,
                                      'CSeq' : str(int(self.d['CSeq']) + 1),
                                      'Session' : self.client_session})
        self.sock.sendall(s)
        print "[C] teardown:\n", s

        received = self.sock.recv(128)
        print len(received), "Received [S] teardown:\n{}".format(received)
        self.d = decode(received)

        if not self.d is None:
            print "[S] teardown: ", self.d['status'], self.d['CSeq']
        else:
            print "[TEARDOWN] None"

        self.fr.teardown = 1
        print "Hey!", self.fr.is_alive(), self.fr.teardown
        self.fr.stop()
        print "after calling stop"
        del self.fr


    def __del__(self):
        self.sock.close()

if __name__ == '__main__':
    c = client()
    for i in range(2):
        c.setup("movie.mjpeg")
        c.play()
        time.sleep(2)
        c.pause()
        time.sleep(2)
        c.play()
        time.sleep(2)
        c.pause()
        c.play()
        time.sleep(3)
        c.teardown()
        print "============="
        print "end test: ", i
    print "test end!"
