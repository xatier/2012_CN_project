#!/usr/bin/python

import os
import wx
import client

sed = 0
ped = 0

class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=wx.Size(500,500))
        self.CreateStatusBar()
        self.Centre()

        # Setting up the menu
        filemenu= wx.Menu()

        menuAbout = filemenu.Append(wx.ID_ABOUT, '&About', 'about this program')
        menuExit  = filemenu.Append(wx.ID_EXIT, 'E&xit', 'ByeBye')

        # Creating the menubar
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File")
        self.SetMenuBar(menuBar)

        # Buttons
        self.sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        self.buttons = []
        self.buttons.append(wx.Button(self, -1, "SETUP"))
        self.sizer2.Add(self.buttons[0], 1, wx.EXPAND)
        self.buttons.append(wx.Button(self, -1, "PLAY"))
        self.sizer2.Add(self.buttons[1], 1, wx.EXPAND)
        self.buttons.append(wx.Button(self, -1, "PAUSE"))
        self.sizer2.Add(self.buttons[2], 1, wx.EXPAND)
        self.buttons.append(wx.Button(self, -1, "TEARDOWN"))
        self.sizer2.Add(self.buttons[3], 1, wx.EXPAND)

        # timer
        self.timex = wx.Timer(self, wx.ID_OK)
        self.timex.Start(80)


        # Set events.
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        self.Bind(wx.EVT_BUTTON, self.OnSetup, self.buttons[0])
        self.Bind(wx.EVT_BUTTON, self.OnPlay, self.buttons[1])
        self.Bind(wx.EVT_BUTTON, self.OnPause, self.buttons[2])
        self.Bind(wx.EVT_BUTTON, self.OnTeardown, self.buttons[3])
        self.Bind(wx.EVT_CLOSE, self.OnExit)
        self.Bind(wx.EVT_TIMER, self.OnPaint, self.timex)

        # add sizer2 to sizer
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.sizer2, 0, wx.EXPAND)

        # Layout the sizer
        self.SetSizer(self.sizer)
        self.SetAutoLayout(1)

        self.Show(True)

        # i don't want to see the anonyed error message dialog :(
        wx.Log_SetActiveTarget(wx.LogStderr()) 



    def OnPaint(self, e):
        global sed, ped
        if sed and ped == 1:
            try :
                dc = wx.PaintDC(self)
                self.pic = wx.Bitmap(c.fr.picname)
                dc.DrawBitmap(self.pic, 20, 50)
            except:
                pass

    def OnAbout(self, e):
        dlg = wx.MessageDialog( self, "my CN project", "About", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def OnExit(self, e):
        dlg = wx.MessageDialog(self,
                    "Do you really want make a contract with me?",
                    "Confirm Exit!", wx.OK|wx.ICON_QUESTION)
        dlg.ShowModal()
        dlg.Destroy()
        self.Destroy()

    def OnSetup(self, e):
        global sed
        sed = 1
        c.setup('movie.mjpeg')

    def OnPlay(self, e):
        global ped
        ped = 1
        c.play()

    def OnPause(self, e):
        global ped
        ped = 0
        c.pause()
        # force to refresh
        self.OnPaint("")

    def OnTeardown(self, e):
        global sed
        sed = 0
        c.teardown()



app = wx.App(False)
c = client.client()
frame = MainWindow(None, "Video Player")
app.MainLoop()

