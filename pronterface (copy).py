#!/usr/bin/env python
try:
    import wx
except:
    print "WX is not installed. This program requires WX to run."
    raise
import printcore, os, sys, glob, time, threading, traceback, StringIO, gviz
thread=threading.Thread
winsize=(800,500)
if os.name=="nt":
    winsize=(800,530)
    try:
        import _winreg
    except:
        pass


import pronsole

def dosify(name):
    return os.path.split(name)[1].split(".")[0][:8]+".g"

class Tee(object):
    def __init__(self, target):
        self.stdout = sys.stdout
        sys.stdout = self
        self.target=target
    def __del__(self):
        sys.stdout = self.stdout
    def write(self, data):
        self.target(data)
        self.stdout.write(data)
    def flush(self):
        self.stdout.flush()


class PronterWindow(wx.Frame,pronsole.pronsole):
    def __init__(self, filename=None,size=winsize):
        pronsole.pronsole.__init__(self)
        self.filename=filename
        os.putenv("UBUNTU_MENUPROXY","0")
        wx.Frame.__init__(self,None,title="Printer Interface",size=size);
        self.panel=wx.Panel(self,-1,size=size)
        self.statuscheck=False
        self.tempreport=""
        self.monitor=0
        self.feedxy=3000
        self.feedz=200
        self.feede=300
        self.paused=False
        self.temps={"off":"0","pla":"200","abs":"265"}
        self.bedtemps={"pla":"90","abs":"140","off":"0"}
        xcol=(245,245,108)
        ycol=(180,180,255)
        zcol=(180,255,180)
        self.cpbuttons=[
        ["HomeX",("home X"),(3,0),(205,205,78),(1,2)],
        ["HomeY",("home Y"),(3,2),(150,150,205),(1,2)],
        ["HomeZ",("home Z"),(3,5),(150,205,150),(1,2)],
        ["Home All",("home"),(3,7),(250,250,250),(1,2)],
        ["Extrude",("extrude"),(0,8),(225,200,200),(1,2)],
        ["Reverse",("reverse"),(2,8),(225,200,200),(1,2)],
        ["FL",("fl"),(0,0),(250,250,250),(1,2)],
        ["FR",("fr"),(0,2),(250,250,250),(1,2)],
        ["BL",("bl"),(2,0),(250,250,250),(1,2)],
        ["BR",("br"),(2,2),(250,250,250),(1,2)],
        ["CENTRE",("ctr"),(1,1),(250,250,250),(1,2)],
        ["Z+",("zpos"),(0,5),(250,250,250),(1,1)],
        ["Z-",("zneg"),(2,5),(250,250,250),(1,1)],
#        ["CURR POS",("M114"),(5,7),(250,250,250),(1,2)],
        ]
#        self.custombuttons=[]
        self.btndict={}
        self.load_rc(".pronsolerc")
#        customdict={}
#        try:
#            execfile("custombtn.txt",customdict)
#            print "here"
#            self.custombuttons=customdict["btns"]
#        except:
#            pass
        self.custombuttons=[
        ["INIT SD","M21",(200,200,200)],
        ["EJECT","M22",(200,200,200)],
        ["LIST","M20",(200,200,200)],
        ["GET TEMP","M105",(200,200,200)],
        ["GET POS","M114",(200,200,200)],
        ["ECHO","loud",(200,200,200)],
        ["QUIET","quiet",(200,200,200)],
        ]
        self.popmenu()
        self.popwindow()
        self.t=Tee(self.catchprint)
        self.stdout=sys.stdout
        self.mini=False
        self.zdist="0.1"        
        self.p.sendcb=self.sentcb
        self.curlayer=0
    
    def online(self):
        print "Printer is now online"
    
    def sentcb(self,line):
        if("G1" in line):
            if("Z" in line):
                try:
                    layer=float(line.split("Z")[1].split()[0])
                    if(layer!=self.curlayer):
                        self.curlayer=layer
                        self.gviz.hilight=[]
                        wx.CallAfter(self.gviz.setlayer,layer)
                except:
                    pass
            self.gviz.addgcode(line,hilight=1)
            #self.gwindow.p.addgcode(line,hilight=1)
    
    def do_extrude(self,l=""):
        try:
            if not (l.__class__=="".__class__ or l.__class__==u"".__class__) or (not len(l)):
                l=str(self.edist.GetValue())
            pronsole.pronsole.do_extrude(self,l)
        except:
            raise
    
    def do_reverse(self,l=""):
        try:
            if not (l.__class__=="".__class__ or l.__class__==u"".__class__) or (not len(l)):
                l=str(float(self.edist.GetValue())*-1.0)
            pronsole.pronsole.do_extrude(self,l)
        except:
            pass
    
    
    def do_settemp(self,l=""):
        try:
            if not (l.__class__=="".__class__ or l.__class__==u"".__class__) or (not len(l)):
                l=str(self.htemp.GetValue().split()[0])
        except:
            print "You must enter a temperature."
        else:
            l=l.lower().replace(",",".")
            for i in self.temps.keys():
                l=l.replace(i,self.temps[i])
            f=float(l)
            if f>=0:
                if self.p.online:
                    self.p.send_now("M104 S"+str(l))
                    print "Setting hotend temperature to ",f," degrees Celsius."
                    self.htemp.SetValue(l)
                else:
                    print "Printer is not online."
            else:
                print "You cannot set negative temperatures. To turn the hotend off entirely, set its temperature to 0."
    
    def do_bedtemp(self,l=""):
        try:
            if not (l.__class__=="".__class__ or l.__class__==u"".__class__) or (not len(l)):
                l=str(self.btemp.GetValue().split()[0])
            l=l.lower().replace(",",".")
            for i in self.bedtemps.keys():
                l=l.replace(i,self.bedtemps[i])
            f=float(l)
            if f>=0:
                if self.p.online:
                    self.p.send_now("M140 S"+str(l))
                    print "Setting bed temperature to ",f," degrees Celsius."
                    self.btemp.SetValue(l)
                else:
                    print "Printer is not online."
            else:
                print "You cannot set negative temperatures. To turn the bed off entirely, set its temperature to 0."
        except:
            print "You must enter a temperature."
            
    
    def catchprint(self,l):
        wx.CallAfter(self.logbox.AppendText,l)
        
    def scanserial(self):
        """scan for available ports. return a list of device names."""
        baselist=[]
        if os.name=="nt":
            try:
                key=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,"HARDWARE\\DEVICEMAP\\SERIALCOMM")
                i=0
                while(1):
                    baselist+=[_winreg.EnumValue(key,i)[1]]
                    i+=1
            except:
                pass
        return baselist+glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') +glob.glob("/dev/tty.*")+glob.glob("/dev/cu.*")+glob.glob("/dev/rfcomm*")
        
    def popmenu(self):
        self.menustrip = wx.MenuBar()
        m = wx.Menu()
        self.Bind(wx.EVT_MENU, lambda x:threading.Thread(target=lambda :self.do_skein("set")).start(), m.Append(-1,"Skeinforge settings"," Adjust skeinforge settings"))
        self.Bind(wx.EVT_MENU, self.OnExit, m.Append(wx.ID_EXIT,"Close"," Closes the Window"))
        self.menustrip.Append(m,"&Print")
        self.SetMenuBar(self.menustrip)
        pass
    
    def OnExit(self, event):
        self.Close()
        
    def popwindow(self):
        #sizer layout: topsizer is a column sizer containing two sections
        #upper section contains the mini view buttons
        #lower section contains the rest of the window - manual controls, console, visualizations
        #TOP ROW:
        uts=self.uppertopsizer=wx.BoxSizer(wx.HORIZONTAL)
        uts.Add(wx.StaticText(self.panel,-1,"Port:",pos=(0,5)),wx.TOP|wx.LEFT,5)
        scan=self.scanserial()
        self.serialport = wx.ComboBox(self.panel, -1,
                choices=scan,
                style=wx.CB_DROPDOWN|wx.CB_SORT, pos=(50,0))
        try:
            self.serialport.SetValue(scan[0])
        except:
            pass
        uts.Add(self.serialport)
        uts.Add(wx.StaticText(self.panel,-1,"@",pos=(250,5)),wx.RIGHT,5)
        self.baud = wx.ComboBox(self.panel, -1,
                choices=["2400", "9600", "19200", "38400", "57600", "115200"],
                style=wx.CB_DROPDOWN|wx.CB_SORT, size=(110,30),pos=(275,0))
        self.baud.SetValue("115200")
        uts.Add(self.baud)
        self.connectbtn=wx.Button(self.panel,-1,"Connect",pos=(380,0))
        uts.Add(self.connectbtn)
        self.connectbtn.SetToolTipString("Connect to the printer")
        self.connectbtn.Bind(wx.EVT_BUTTON,self.connect)
        self.disconnectbtn=wx.Button(self.panel,-1,"Disconnect",pos=(470,0))
        self.disconnectbtn.Bind(wx.EVT_BUTTON,self.disconnect)
        uts.Add(self.disconnectbtn)
        self.resetbtn=wx.Button(self.panel,-1,"Reset",pos=(560,0))
        self.resetbtn.Bind(wx.EVT_BUTTON,self.reset)
        uts.Add(self.resetbtn)
        self.minibtn=wx.Button(self.panel,-1,"Mini mode",pos=(580,0))
        self.minibtn.Bind(wx.EVT_BUTTON,self.toggleview)
#        uts.Add((100,-1),flag=wx.EXPAND)
        uts.Add(self.minibtn)
        self.sleepslider=wx.Slider(self.panel, -1, 50, 1, 10, (620, 5), (80, 45),wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS)
        uts.Add(self.sleepslider)
        
        #SECOND ROW
        ubs=self.upperbottomsizer=wx.BoxSizer(wx.HORIZONTAL)
        
        self.loadbtn=wx.Button(self.panel,-1,"Load file",pos=(10,40))
        self.loadbtn.Bind(wx.EVT_BUTTON,self.loadfile)
        ubs.Add(self.loadbtn)
        self.uploadbtn=wx.Button(self.panel,-1,"SD Upload",pos=(90,40))
        self.uploadbtn.Bind(wx.EVT_BUTTON,self.upload)
        ubs.Add(self.uploadbtn)
        self.sdprintbtn=wx.Button(self.panel,-1,"SD Print",pos=(180,40))
        self.sdprintbtn.Bind(wx.EVT_BUTTON,self.sdprintfile)
        ubs.Add(self.sdprintbtn)
        self.printbtn=wx.Button(self.panel,-1,"Print",pos=(280,40))
        self.printbtn.Bind(wx.EVT_BUTTON,self.printfile)
        ubs.Add(self.printbtn)
        self.pausebtn=wx.Button(self.panel,-1,"Pause",pos=(370,40))
        self.pausebtn.Bind(wx.EVT_BUTTON,self.pause)
        ubs.Add(self.pausebtn)
        try:
            for i in self.custombuttons[:3]:
                if i is None:
                    continue
                b=wx.Button(self.panel,-1,i[0])
                b.properties=i
                b.SetBackgroundColour(i[2])
                b.Bind(wx.EVT_BUTTON,self.procbutton)
                ubs.Add(b)
        except:
            pass
        self.monitorbox=wx.CheckBox(self.panel,-1,"",pos=(450,37))
        ubs.Add((15,-1))
        ubs.Add(self.monitorbox)        
        ubs.Add(wx.StaticText(self.panel,-1,"Monitor",pos=(690,37)))
        self.monitorbox.Bind(wx.EVT_CHECKBOX,self.setmonitor)

        #Right full view
        lrs=self.lowerrsizer=wx.BoxSizer(wx.VERTICAL)
        self.logbox=wx.TextCtrl(self.panel,size=(350,340),pos=(440,75),style = wx.TE_MULTILINE)
        self.logbox.SetEditable(0)
        lrs.Add(self.logbox)
        lbrs=wx.BoxSizer(wx.HORIZONTAL)
        self.commandbox=wx.TextCtrl(self.panel,size=(250,30),pos=(440,420),style = wx.TE_PROCESS_ENTER)
        self.commandbox.Bind(wx.EVT_TEXT_ENTER,self.sendline)
        lbrs.Add(self.commandbox)
        self.sendbtn=wx.Button(self.panel,-1,"Send",pos=(700,420))
        self.sendbtn.Bind(wx.EVT_BUTTON,self.sendline)
        lbrs.Add(self.sendbtn)
        lrs.Add(lbrs)
        
        #left pane
        lls=self.lowerlsizer=wx.BoxSizer(wx.VERTICAL)
        #feed controls
        fs=self.feedsizer=wx.BoxSizer(wx.HORIZONTAL)
        fs.Add(wx.StaticText(self.panel,-1,"XY:",pos=(2,90-2)))#,pos=(2,0),span=(1,2))
        self.xyfeedc=wx.SpinCtrl(self.panel,-1,"3000",min=0,max=50000,size=(60,25),pos=(25,63))
        self.xyfeedc.Bind(wx.EVT_SPINCTRL,self.setfeeds)
        fs.Add(self.xyfeedc)#,pos=(2,2),span=(1,4))
        fs.Add(wx.StaticText(self.panel,-1,"mm/min",pos=(60,69)))#,pos=(2,2),span=(1,4))
        fs.Add((25,25))
        fs.Add(wx.StaticText(self.panel,-1,"Z:",pos=(90,90-2)))#,pos=(2,6),span=(1,2))
        self.zfeedc=wx.SpinCtrl(self.panel,-1,"200",min=0,max=50000,size=(60,25),pos=(25,63))
        self.zfeedc.Bind(wx.EVT_SPINCTRL,self.setfeeds)
        self.zfeedc.SetBackgroundColour((180,255,180))
        self.zfeedc.SetForegroundColour("black")
        fs.Add(self.zfeedc)#,pos=(2,8),span=(2,4))
        fs.Add(wx.StaticText(self.panel,-1,"mm/min",pos=(60,69)))#,pos=(2,2),span=(1,4))
        fs.Add((25,25))
        fs.Add(wx.StaticText(self.panel,-1,"E:",pos=(90,90-2)))#,pos=(2,6),span=(1,2))
        self.efeedc=wx.SpinCtrl(self.panel,-1,"300",min=0,max=50000,size=(60,25),pos=(70,397+28))
        self.efeedc.SetBackgroundColour((225,200,200))
        self.efeedc.SetForegroundColour("black")
        self.efeedc.Bind(wx.EVT_SPINCTRL,self.setfeeds)
        fs.Add(self.efeedc)
        fs.Add(wx.StaticText(self.panel,-1,"mm/min",pos=(130,407+27)))
        lls.Add(fs)
        #bottom of left pane
        ms=self.manualsizer=wx.GridBagSizer()
        for i in self.cpbuttons:
            btn=wx.Button(self.panel,-1,i[0])#,pos=i[2],size=i[4])
            btn.SetBackgroundColour(i[3])
            btn.SetForegroundColour("black")
            btn.properties=i
            btn.Bind(wx.EVT_BUTTON,self.procbutton)
            self.btndict[i[1]]=btn
            ms.Add(btn,pos=i[2],span=i[4])
        
        self.radiox1 = wx.RadioButton(self.panel, -1, "0.1", pos=(230, 110), style=wx.RB_GROUP)
        self.radiox10 = wx.RadioButton(self.panel, -1, "1", pos=(230, 130))
        self.radiox100 = wx.RadioButton(self.panel, -1, "10", pos=(230, 150))
        for eachRadio in [self.radiox1, self.radiox10, self.radiox100]:
            self.Bind(wx.EVT_RADIOBUTTON, self.OnRadio, eachRadio)
        ms.Add(self.radiox1,pos=(0,6),span=(1,2))
        ms.Add(self.radiox10,pos=(1,6),span=(1,2))
        ms.Add(self.radiox100,pos=(2,6),span=(1,2))
        self.edist=wx.SpinCtrl(self.panel,-1,"5",min=0,max=1000,size=(75,25),pos=(410,130))
        self.edist.SetBackgroundColour((225,200,200))
        self.edist.SetForegroundColour("black")
        ms.Add(self.edist,pos=(1,8),span=(1,1))
        ms.Add(wx.StaticText(self.panel,-1,"mm",pos=(130,407)),pos=(1,9),span=(1,2))
        #temp setting
        ms.Add(wx.StaticText(self.panel,-1,"Nozzle:",pos=(10,237)),pos=(4,0),span=(1,1))
        self.htemp=wx.ComboBox(self.panel, -1,
                choices=[self.temps[i]+" ("+i+")" for i in self.temps.keys()],
                style=wx.CB_DROPDOWN, size=(90,25),pos=(55,232))
        self.htemp.SetValue("0")
        ms.Add(self.htemp,pos=(4,1),span=(1,2))
        self.settbtn=wx.Button(self.panel,-1,"Set",size=(40,-1),pos=(145,230))
        self.settbtn.Bind(wx.EVT_BUTTON,self.do_settemp)
        ms.Add(self.settbtn,pos=(4,3),span=(1,3))
        ms.Add(wx.StaticText(self.panel,-1,"Bed:",pos=(210,237)),pos=(4,6),span=(1,1))
        self.btemp=wx.ComboBox(self.panel, -1,
                choices=[self.bedtemps[i]+" ("+i+")" for i in self.bedtemps.keys()],
                style=wx.CB_DROPDOWN, size=(90,25),pos=(255,232))
        self.btemp.SetValue("0")
        ms.Add(self.btemp,pos=(4,7),span=(1,2))
        self.setbbtn=wx.Button(self.panel,-1,"Set",size=(40,-1),pos=(135,365))
        self.setbbtn.Bind(wx.EVT_BUTTON,self.do_bedtemp)
        ms.Add(self.setbbtn,pos=(4,9),span=(1,2))
#        ms.Add((10,0),pos=(0,11),span=(1,1))

        self.gviz=gviz.gviz(self.panel,(200,200),(200,200))
        self.gwindow=gviz.window([])
        self.gviz.Bind(wx.EVT_LEFT_DOWN,self.showwin)
        self.gwindow.Bind(wx.EVT_CLOSE,lambda x:self.gwindow.Hide())

#        ms.Add(self.gviz,pos=(6,0),span=(1,8))
        
        lls.Add(ms)
        cs=wx.GridBagSizer()
        cs.Add(self.gviz,pos=(0,0),span=(3,1))
        posindex=0
        try:
            for i in self.custombuttons[3:]:
                if i is None:
                    continue
                b=wx.Button(self.panel,-1,i[0])
                b.properties=i
                b.SetBackgroundColour(i[2])
                b.Bind(wx.EVT_BUTTON,self.procbutton)
                cs.Add(b,pos=(1+posindex/3,1+posindex%3),span=(1,1))
                posindex+=1
        except:
            pass
        lls.Add(cs)#,pos=(0,10),span=(15,1))
        
        
        
        self.uppersizer=wx.BoxSizer(wx.VERTICAL)
        self.uppersizer.Add(self.uppertopsizer)
        self.uppersizer.Add(self.upperbottomsizer)
        
        self.lowersizer=wx.BoxSizer(wx.HORIZONTAL)
        self.lowersizer.Add(lls)
        self.lowersizer.Add(lrs)
        self.topsizer=wx.BoxSizer(wx.VERTICAL)
        self.topsizer.Add(self.uppersizer)
        self.topsizer.Add(self.lowersizer)
        self.panel.SetSizer(self.topsizer)
        self.status=self.CreateStatusBar()
        self.status.SetStatusText("Not connected to printer.")
        self.Bind(wx.EVT_CLOSE, self.kill)
        self.topsizer.Layout()
        self.topsizer.Fit(self)
        
        #self.panel.Fit()
        #uts.Layout()
        
    def showwin(self,event):
        self.gwindow.Show()
        
    def do_pos(self,e):
        self.p.send_now("M114")

#    def onButton(self,event):
#        button = event.GetEventObject()
#        #self.p.send_now(self.jogdict[button.GetLabel()]+" F"+str(self.xyfeedc.GetValue()))         
#        self.onecmd("move_abs "+self.jogdict[button.GetLabel()]+" F"+str(self.xyfeedc.GetValue()))
         
        
    def do_fl(self,e):
        self.onecmd("move_abs X5 Y5 F"+str(self.xyfeedc.GetValue()))
    def do_fr(self,e):
        self.onecmd("move_abs X135 Y5 F"+str(self.xyfeedc.GetValue()))
    def do_bl(self,e):
        self.onecmd("move_abs X5 Y135 F"+str(self.xyfeedc.GetValue()))
    def do_br(self,e):
        self.onecmd("move_abs X135 Y135 F"+str(self.xyfeedc.GetValue()))
    def do_ctr(self,e):
        self.onecmd("move_abs X70 Y70 F"+str(self.xyfeedc.GetValue()))
    def OnRadio(self, event):
       radioSelected = event.GetEventObject()
       self.zdist=radioSelected.GetLabel()

    def do_zneg(self,e):
        self.onecmd("move Z -" + self.zdist)

    def do_zpos(self,e):
        self.onecmd("move Z " + self.zdist)
        
    def setfeeds(self,e):
        try:
            self.feede=int(self.efeedc.GetValue())
        except:
            pass
        try:
            self.feedz=int(self.zfeedc.GetValue())
        except:
            pass
        try:
            self.feedxy=int(self.xyfeedc.GetValue())
        except:
            pass
        
        
    def toggleview(self,e):
        if(self.mini):
            self.mini=False
            self.topsizer.Fit(self)
        
            #self.SetSize(winsize)
            self.minibtn.SetLabel("Mini mode")
            
        else:
            self.mini=True
            self.uppersizer.Fit(self)
        
            #self.SetSize(winssize)
            self.minibtn.SetLabel("Full mode")
                
        
    def procbutton(self,e):
        try:
            self.onecmd(e.GetEventObject().properties[1])
        except:
            print "event object missing"
            raise
        
    def kill(self,e):
        self.statuscheck=0
        self.p.recvcb=None
        self.p.disconnect()
        try:
            self.gwindow.Destroy()
        except:
            pass
        self.Destroy()
        
        
    def setmonitor(self,e):
        self.monitor=self.monitorbox.GetValue()
        
    def sendline(self,e):
        command=self.commandbox.GetValue()
        if not len(command):
            return
        wx.CallAfter(self.logbox.AppendText,">>>"+command+"\n")
        self.onecmd(str(command))
        self.commandbox.SetSelection(0,len(command))
        
    def statuschecker(self):
        try:
            while(self.statuscheck):
                string=""
                if(self.p.online):
                    string+="Printer is online. "
                try:
                    string+="Loaded "+os.path.split(self.filename)[1]+" "
                except:
                    pass
                string+=(self.tempreport.replace("\r","").replace("T","Hotend").replace("B","Bed").replace("\n","").replace("ok ",""))+" "
                if self.sdprinting:
                    string+= " SD printing:%04.2f %%"%(self.percentdone,)
                if self.p.printing:
                    string+= " Printing:%04.2f %%"%(100*float(self.p.queueindex)/len(self.p.mainqueue),)
                wx.CallAfter(self.status.SetStatusText,string)
                wx.CallAfter(self.gviz.Refresh)
                if(self.monitor and self.p.online):
                    if self.sdprinting:
                        self.p.send_now("M27")
                    self.p.send_now("M105")
                time.sleep(self.sleepslider.GetValue())
            wx.CallAfter(self.status.SetStatusText,"Not connected to printer.")
        except:
            pass #if window has been closed
    def capture(self, func, *args, **kwargs):
        stdout=sys.stdout
        cout=None
        try:
            cout=self.cout
        except:
            pass
        if cout is None:
            cout=cStringIO.StringIO()
        
        sys.stdout=cout
        retval=None
        try:
            retval=func(*args,**kwargs)
        except:
            traceback.print_exc()
        sys.stdout=stdout
        return retval

    def recvcb(self,l):
        if "T:" in l:
            self.tempreport=l
        tstring=l.rstrip()
        #print tstring
        if(tstring!="ok"):
            print tstring
            #wx.CallAfter(self.logbox.AppendText,tstring+"\n")
        for i in self.recvlisteners:
            i(l)
    
    def listfiles(self,line):
        if "Begin file list" in line:
            self.listing=1
        elif "End file list" in line:
            self.listing=0
            self.recvlisteners.remove(self.listfiles)
            wx.CallAfter(self.filesloaded)
        elif self.listing:
            self.sdfiles+=[line.replace("\n","").replace("\r","").lower()]
        
    def waitforsdresponse(self,l):
        if "file.open failed" in l:
            wx.CallAfter(self.status.SetStatusText,"Opening file failed.")
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "File opened" in l:
            wx.CallAfter(self.status.SetStatusText,l)
        if "File selected" in l:
            wx.CallAfter(self.status.SetStatusText,"Starting print")
            self.sdprinting=1
            self.p.send_now("M24")
            return
        if "Done printing file" in l:
            wx.CallAfter(self.status.SetStatusText,l)
            self.sdprinting=0
            self.recvlisteners.remove(self.waitforsdresponse)
            return
        if "SD printing byte" in l:
            #M27 handler
            try:
                resp=l.split()
                vals=resp[-1].split("/")
                self.percentdone=100.0*int(vals[0])/int(vals[1])
            except:
                pass
    
        
        
    def filesloaded(self):
        dlg=wx.SingleChoiceDialog(self, "Select the file to print", "Pick SD file", self.sdfiles)
        if(dlg.ShowModal()==wx.ID_OK):
            target=dlg.GetStringSelection()
            if len(target):
                self.recvlisteners+=[self.waitforsdresponse]
                self.p.send_now("M23 "+str(target.lower()))
        
        #print self.sdfiles
        pass

    def getfiles(self):
        if not self.p.online:
            self.sdfiles=[]
            return
        self.listing=0
        self.sdfiles=[]
        self.recvlisteners+=[self.listfiles]
        self.p.send_now("M20")
        
    def skein_func(self):
        try:
            from skeinforge.skeinforge_application.skeinforge_utilities import skeinforge_craft
            from skeinforge.skeinforge_application import skeinforge
            from skeinforge.fabmetheus_utilities import settings
            skeinforge_craft.writeOutput(self.filename,False)
            #print len(self.cout.getvalue().split())
            self.stopsf=1
        except:
            print "Skeinforge execution failed."
            self.stopsf=1
            raise
        
    def skein_monitor(self):
        while(not self.stopsf):
            try:
                wx.CallAfter(self.status.SetStatusText,"Skeining...")#+self.cout.getvalue().split("\n")[-1])
            except:
                pass
            time.sleep(0.1)
        fn=self.filename
        try:
            self.filename=self.filename.replace(".stl","_export.gcode")
            self.f=[i.replace("\n","").replace("\r","") for i in open(self.filename)]
            wx.CallAfter(self.status.SetStatusText,"Loaded "+self.filename+", %d lines"%(len(self.f),))
            threading.Thread(target=self.loadviz).start()
        except:
            self.filename=fn
        
    def skein(self,filename):
        print "Skeining "+filename
        if not os.path.exists("skeinforge"):
            print "Skeinforge not found. \nPlease copy Skeinforge into a directory named \"skeinforge\" in the same directory as this file."
            return
        if not os.path.exists("skeinforge/__init__.py"):
            f=open("skeinforge/__init__.py","w")
            f.close()
        self.cout=StringIO.StringIO()
        self.filename=filename
        self.stopsf=0
        thread(target=self.skein_func).start()
        thread(target=self.skein_monitor).start()
        
    def loadfile(self,event):
        basedir="."
        try:
            basedir=os.path.split(self.filename)[0]
        except:
            pass
        dlg=wx.FileDialog(self,"Open file to print",basedir,style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
        dlg.SetWildcard("STL and GCODE files (;*.gcode;*.g;*.stl;*.pla;*.abs")
        if(dlg.ShowModal() == wx.ID_OK):
            name=dlg.GetPath()
            if not(os.path.exists(name)):
                self.status.SetStatusText("File not found!")
                return
            if name.endswith(".stl"):
                self.skein(name)
            else:
                self.f=[i.replace("\n","").replace("\r","") for i in open(name)]
                self.filename=name
                self.status.SetStatusText("Loaded "+name+", %d lines"%(len(self.f),))
                threading.Thread(target=self.loadviz).start()
                
    def loadviz(self):
        self.gviz.clear()
        for i in self.f:
            self.gviz.addgcode(i)
            self.gwindow.p.addgcode(i)
        self.gviz.showall=1
        wx.CallAfter(self.gviz.Refresh)
                
    def printfile(self,event):
        if self.paused:
            self.p.paused=0
            self.pausebtn.SetLabel("Pause")
            self.printbtn.SetLabel("Print")
            self.paused=0
            if self.sdprinting:
                self.p.send_now("M26 S0")
                self.p.send_now("M24")
                return
        
        if self.f is None or not len(self.f):
            wx.CallAfter(self.status.SetStatusText,"No file loaded. Please use load first.")
            return
        if not self.p.online:
            wx.CallAfter(self.status.SetStatusText,"Not connected to printer.")
            return
        self.pausebtn.Enable()
        self.printbtn.SetLabel("Restart")
        self.p.startprint(self.f)
        
    def endupload(self):
        self.p.send_now("M29 ")
        wx.CallAfter(self.status.SetStatusText,"File upload complete")
        time.sleep(0.5)
        self.p.clear=True
        self.uploading=False
        
    def uploadtrigger(self,l):
        if "Writing to file" in l:
            self.uploading=True
            self.p.startprint(self.f)
            self.p.endcb=self.endupload
            self.recvlisteners.remove(self.uploadtrigger)
        elif "open failed, File" in l:
            self.recvlisteners.remove(self.uploadtrigger)
        
    def upload(self,event):
        if not len(self.f):
            return
        if not self.p.online:
            return
        dlg=wx.TextEntryDialog(self,"Enter a target filename in 8.3 format:","Pick SD filename",dosify(self.filename))
        if dlg.ShowModal()==wx.ID_OK:
            self.p.send_now("M28 "+str(dlg.GetValue()))
            self.recvlisteners+=[self.uploadtrigger]
        pass
        
    def pause(self,event):
        if not self.paused:
            if self.sdprinting:
                self.p.send_now("M25")
            else:
                if(not self.p.printing):
                    #print "Not printing, cannot pause."
                    return
                self.p.pause()
            self.paused=True
            self.pausebtn.SetLabel("Resume")
        else:
            self.paused=False
            if self.sdprinting:
                self.p.send_now("M24")
            else:
                self.p.resume()
            self.pausebtn.SetLabel("Pause")
    
        
    def sdprintfile(self,event):
        threading.Thread(target=self.getfiles).start()
        pass
        
    def connect(self,event):
        port=None
        try:
            port=self.scanserial()[0]
        except:
            pass
        if self.serialport.GetValue()!="":
            port=str(self.serialport.GetValue())
        baud=115200
        try:
            baud=int(self.baud.GetValue())
        except:
            pass
        if self.paused:
            self.p.paused=0
            self.p.printing=0
            self.pausebtn.SetLabel("Pause")
            self.printbtn.SetLabel("Print")
            self.paused=0
            if self.sdprinting:
                self.p.send_now("M26 S0")
        self.p.connect(port,baud)
        self.statuscheck=True
        threading.Thread(target=self.statuschecker).start()
        
        
    def disconnect(self,event):
        self.p.disconnect()
        self.statuscheck=False
        if self.paused:
            self.p.paused=0
            self.p.printing=0
            self.pausebtn.SetLabel("Pause")
            self.printbtn.SetLabel("Print")
            self.paused=0
            if self.sdprinting:
                self.p.send_now("M26 S0")
                
    
    def reset(self,event):
        dlg=wx.MessageDialog(self,"Are you sure you want to reset the printer?","Reset?",wx.YES|wx.NO)
        if dlg.ShowModal()==wx.ID_YES:
            self.p.reset()
            if self.paused:
                self.p.paused=0
                self.p.printing=0
                self.pausebtn.SetLabel("Pause")
                self.printbtn.SetLabel("Print")
                self.paused=0
            
        
        
if __name__ == '__main__':
    app = wx.App(False)
    main = PronterWindow()
    main.Show()
    try:
        app.MainLoop()
    except:
        pass

