#!/usr/bin/env python
try:
    import wx
except:
    print "WX is not installed. This program requires WX to run."
    raise
import printcore, os, sys, glob, time, threading, traceback, StringIO, gviz
try:
    os.chdir(os.path.split(__file__)[0])
except:
    pass
    
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
        self.settings.last_file_path = ""
        self.settings.last_temperature = 0.0
        self.settings.last_bed_temperature = 0.0
        self.filename=filename
        os.putenv("UBUNTU_MENUPROXY","0")
        wx.Frame.__init__(self,None,title="eMAKER Printer Interface",size=size);
        self.panel=wx.Panel(self,-1,size=size)
        self.statuscheck=False
        self.tempreport=""
        self.monitor=0
        self.paused=False
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
        ]
        self.custombuttons=[]
        self.btndict={}
        self.parse_cmdline(sys.argv[1:])
        customdict={}
        try:
            execfile("custombtn.txt",customdict)
            self.custombuttons+=customdict["btns"]
        except:
            pass
        self.popmenu()
        self.popwindow()
        self.t=Tee(self.catchprint)
        self.stdout=sys.stdout
        self.mini=False
        self.zdist="0.1"        
        self.p.sendcb=self.sentcb
#        self.p.startcb=self.startcb
#        self.starttime=0
        self.curlayer=0
    
#    def startcb(self):
#        self.starttime=time.time()
        
#    def endcb(self):
#        print "Print took "+str(int(time.time()-self.starttime))+" seconds."
#        wx.CallAfter(self.pausebtn.Hide)
#        wx.CallAfter(self.printbtn.SetLabel,"Print")

    
    def online(self):
        print "Printer is now online"
        self.connectbtn.Disable();
        self.disconnectbtn.Enable();
#        for i in self.printerControls:
#            i.Enable()
#        if self.filename:
#            self.printbtn.Enable()
        
    
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
#                    self.set("last_temperature",str(f))
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
#                    self.set("last_bed_temperature",str(f))
                else:
                    print "Printer is not online."
            else:
                print "You cannot set negative temperatures. To turn the bed off entirely, set its temperature to 0."
        except:
            print "You must enter a temperature."
            
#    def start_macro(self,macro_name,old_macro_definition=""):
#        if not self.processing_rc:
#            def cb(definition):
#                if "\n" not in definition and len(definition.strip())>0:
#                    macro_def = definition.strip()
#                    self.cur_macro_def = macro_def
#                    self.cur_macro_name = macro_name
#                    if macro_def.startswith("!"):
#                        self.cur_macro = "def macro(self,*arg):\n  "+macro_def[1:]+"\n"
#                    else:
#                        self.cur_macro = "def macro(self,*arg):\n  self.onecmd('"+macro_def+"'.format(*arg))\n"
#                    self.end_macro()
#                    return
#                pronsole.pronsole.start_macro(self,macro_name,True)
#                for line in definition.split("\n"):
#                    if hasattr(self,"cur_macro_def"):
#                        self.hook_macro(line)
#                if hasattr(self,"cur_macro_def"):
#                    self.end_macro()
#            macroed(macro_name,old_macro_definition,cb)
#        else:
#            pronsole.pronsole.start_macro(self,macro_name,old_macro_definition)
    
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
#        if sys.platform != 'darwin':
        self.Bind(wx.EVT_MENU, lambda x:threading.Thread(target=lambda :self.do_skein("set")).start(), m.Append(-1,"Skeinforge settings"," Adjust skeinforge settings"))
        self.Bind(wx.EVT_MENU, self.OnExit, m.Append(wx.ID_EXIT,"Close"," Closes the Window"))
        self.menustrip.Append(m,"&Print")
        self.SetMenuBar(self.menustrip)
        pass
    
    def OnExit(self, event):
        self.Close()

    def rescanserial(self,e):
        scan=self.scanserial()
        self.serialport.Clear()
        for port in scan:
            self.serialport.Append(port)
        
    def popwindow(self):
        # this list will contain all controls that should be only enabled
        # when we're connected to a printer
        self.printerControls = []
        
        #sizer layout: topsizer is a column sizer containing two sections
        #upper section contains the mini view buttons
        #lower section contains the rest of the window - manual controls, console, visualizations
        #TOP ROW:
        uts=self.uppertopsizer=wx.BoxSizer(wx.HORIZONTAL)
        #uts.Add(wx.StaticText(self.panel,-1,"Port:",pos=(0,5)),wx.TOP|wx.LEFT,5)
        self.portbtn=wx.Button(self.panel,-1,"Port",pos=(0,5),style=wx.BU_EXACTFIT)
        self.portbtn.Bind(wx.EVT_BUTTON,self.rescanserial)
        uts.Add(self.portbtn)
        scan=self.scanserial()
        self.serialport = wx.ComboBox(self.panel, -1,
                choices=scan,
                style=wx.CB_DROPDOWN|wx.CB_SORT, pos=(50,0))
        try:
            if self.settings.port:
                self.serialport.SetValue(self.settings.port)
        except:
            pass
        uts.Add(self.serialport)
        uts.Add(wx.StaticText(self.panel,-1,"@",pos=(250,5)),wx.RIGHT,5)
        self.baud = wx.ComboBox(self.panel, -1,
                choices=["2400", "9600", "19200", "38400", "57600", "115200"],
                style=wx.CB_DROPDOWN|wx.CB_SORT, size=(110,30),pos=(275,0))
        try:
            self.baud.SetValue("115200")
            self.baud.SetValue(str(self.settings.baudrate))
        except:
            pass
        uts.Add(self.baud)
        self.connectbtn=wx.Button(self.panel,-1,"Connect",pos=(380,0))
        uts.Add(self.connectbtn)
        self.connectbtn.SetToolTipString("Connect to the printer")
        self.connectbtn.Bind(wx.EVT_BUTTON,self.connect)
        self.disconnectbtn=wx.Button(self.panel,-1,"Disconnect",pos=(470,0))
        self.disconnectbtn.Bind(wx.EVT_BUTTON,self.disconnect)
        self.printerControls.append(self.disconnectbtn)
        uts.Add(self.disconnectbtn)
        self.disconnectbtn.Disable();
        self.resetbtn=wx.Button(self.panel,-1,"Reset",pos=(560,0))
        self.resetbtn.Bind(wx.EVT_BUTTON,self.reset)
        uts.Add(self.resetbtn)
        self.minibtn=wx.Button(self.panel,-1,"Mini mode",pos=(690,0))
        self.minibtn.Bind(wx.EVT_BUTTON,self.toggleview)
        uts.Add(self.minibtn)
        self.sleepslider=wx.Slider(self.panel, -1, 50, 1, 10, (620, 1), (80, 45),wx.SL_HORIZONTAL | wx.SL_AUTOTICKS | wx.SL_LABELS)
        uts.Add(self.sleepslider)
        uts.Add((10,-1))
        
        #SECOND ROW
        ubs=self.upperbottomsizer=wx.BoxSizer(wx.HORIZONTAL)
        
        self.loadbtn=wx.Button(self.panel,-1,"Load file",pos=(10,40))
        self.loadbtn.Bind(wx.EVT_BUTTON,self.loadfile)
        ubs.Add(self.loadbtn)
        self.uploadbtn=wx.Button(self.panel,-1,"SD Upload",pos=(90,40))
        self.uploadbtn.Bind(wx.EVT_BUTTON,self.upload)
        self.printerControls.append(self.uploadbtn)
        ubs.Add(self.uploadbtn)
        self.sdprintbtn=wx.Button(self.panel,-1,"SD Print",pos=(180,40))
        self.sdprintbtn.Bind(wx.EVT_BUTTON,self.sdprintfile)
        self.printerControls.append(self.sdprintbtn)
        ubs.Add(self.sdprintbtn)
        self.printbtn=wx.Button(self.panel,-1,"Print",pos=(280,40))
        self.printbtn.Bind(wx.EVT_BUTTON,self.printfile)
#        self.printbtn.Disable()
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
        self.xyfeedc=wx.SpinCtrl(self.panel,-1,str(self.settings.xy_feedrate),min=0,max=12000,size=(60,25),pos=(25,63))
        self.xyfeedc.Bind(wx.EVT_SPINCTRL,self.setfeeds)
        fs.Add(self.xyfeedc)#,pos=(2,2),span=(1,4))
        fs.Add(wx.StaticText(self.panel,-1,"mm/min",pos=(60,69)))#,pos=(2,2),span=(1,4))
        fs.Add((25,25))
        fs.Add(wx.StaticText(self.panel,-1,"Z:",pos=(90,90-2)))#,pos=(2,6),span=(1,2))
        self.zfeedc=wx.SpinCtrl(self.panel,-1,str(self.settings.z_feedrate),min=0,max=200,size=(60,25),pos=(25,63))
        self.zfeedc.Bind(wx.EVT_SPINCTRL,self.setfeeds)
        self.zfeedc.SetBackgroundColour((180,255,180))
        self.zfeedc.SetForegroundColour("black")
        fs.Add(self.zfeedc)#,pos=(2,8),span=(2,4))
        fs.Add(wx.StaticText(self.panel,-1,"mm/min",pos=(60,69)))#,pos=(2,2),span=(1,4))
        fs.Add((25,25))
        fs.Add(wx.StaticText(self.panel,-1,"E:",pos=(90,90-2)))#,pos=(2,6),span=(1,2))
        self.efeedc=wx.SpinCtrl(self.panel,-1,str(self.settings.e_feedrate),min=0,max=1500,size=(60,25),pos=(70,397+28))
        self.efeedc.SetBackgroundColour((225,200,200))
        self.efeedc.SetForegroundColour("black")
        self.efeedc.Bind(wx.EVT_SPINCTRL,self.setfeeds)
        fs.Add(self.efeedc)
        fs.Add(wx.StaticText(self.panel,-1,"mm/min",pos=(130,407+27)))
        lls.Add(fs)
        #bottom of left pane
        ms=self.manualsizer=wx.GridBagSizer(hgap=5, vgap=5)
        for i in self.cpbuttons:
            btn=wx.Button(self.panel,-1,i[0])#,pos=i[2],size=i[4])
            btn.SetBackgroundColour(i[3])
            btn.SetForegroundColour("black")
            btn.properties=i
            btn.Bind(wx.EVT_BUTTON,self.procbutton)
            self.btndict[i[1]]=btn
            self.printerControls.append(btn)
            ms.Add(btn,pos=i[2],span=i[4])
        self.radiox1 = wx.RadioButton(self.panel, -1, "0.1", pos=(230, 110), style=wx.RB_GROUP)
        self.radiox10 = wx.RadioButton(self.panel, -1, "1", pos=(230, 130))
        self.radiox100 = wx.RadioButton(self.panel, -1, "10", pos=(230, 150))
        for eachRadio in [self.radiox1, self.radiox10, self.radiox100]:
            self.Bind(wx.EVT_RADIOBUTTON, self.OnRadio, eachRadio)
        if self.settings.z_dist == 0.1:
            self.radiox1.SetValue(True)
        elif self.settings.z_dist == 1:
            self.radiox10.SetValue(True)
        else:
            self.radiox100.SetValue(True)
        ms.Add(self.radiox1,pos=(0,6),span=(1,2))
        ms.Add(self.radiox10,pos=(1,6),span=(1,2))
        ms.Add(self.radiox100,pos=(2,6),span=(1,2))
        self.edist=wx.SpinCtrl(self.panel,-1,"5",min=0,max=1000,size=(75,25),pos=(410,130))
        self.edist.SetBackgroundColour((225,200,200))
        self.edist.SetForegroundColour("black")
        ms.Add(self.edist,pos=(1,8),span=(1,1))
        ms.Add(wx.StaticText(self.panel,-1,"mm",pos=(130,407)),pos=(1,9),span=(1,2))
        #nozzle temp setting
        ms.Add(wx.StaticText(self.panel,-1,"Nozzle:",pos=(10,237)),pos=(4,0),span=(1,1))
        htemp_choices=[self.temps[i]+" ("+i+")" for i in sorted(self.temps.keys(),key=lambda x:self.temps[x])]
        if self.settings.last_temperature not in map(float,self.temps.values()):
            htemp_choices = [str(self.settings.last_temperature)] + htemp_choices
        self.htemp=wx.ComboBox(self.panel, -1,
                choices=htemp_choices,style=wx.CB_DROPDOWN, size=(90,25),pos=(55,232))
        self.htemp.SetValue("0")
        ms.Add(self.htemp,pos=(4,1),span=(1,2))
        self.settbtn=wx.Button(self.panel,-1,"Set",size=(40,-1),pos=(135,230))
        self.settbtn.Bind(wx.EVT_BUTTON,self.do_settemp)
        self.printerControls.append(self.settbtn)
        ms.Add(self.settbtn,pos=(4,3),span=(1,3))
        #bed temp setting
        ms.Add(wx.StaticText(self.panel,-1,"Bed:",pos=(210,237)),pos=(4,6),span=(1,1))
        btemp_choices=[self.bedtemps[i]+" ("+i+")" for i in sorted(self.bedtemps.keys(),key=lambda x:self.bedtemps[x])]
        if self.settings.last_bed_temperature not in map(float,self.bedtemps.values()):
            btemp_choices = [str(self.settings.last_bed_temperature)] + btemp_choices
        self.btemp=wx.ComboBox(self.panel, -1,
                choices=btemp_choices,style=wx.CB_DROPDOWN, size=(90,25),pos=(255,232))
        self.btemp.SetValue("0")
        ms.Add(self.btemp,pos=(4,7),span=(1,2))
        self.setbbtn=wx.Button(self.panel,-1,"Set",size=(40,-1),pos=(135,365))
        self.setbbtn.Bind(wx.EVT_BUTTON,self.do_bedtemp)
        self.printerControls.append(self.setbbtn)
        ms.Add(self.setbbtn,pos=(4,9),span=(1,2))

        lls.Add(ms)

        cs=wx.GridBagSizer(hgap=5,vgap=5)
        #toolpath window
        self.gviz=gviz.gviz(self.panel,(200,200),(200,200))
#        self.gviz.showall=1
        self.gwindow=gviz.window([])
        self.gviz.Bind(wx.EVT_LEFT_DOWN,self.showwin)
        self.gwindow.Bind(wx.EVT_CLOSE,lambda x:self.gwindow.Hide())
        cs.Add(self.gviz,pos=(0,0),span=(5,1))
        #custom buttons
        posindex=0
        try:
            for i in self.custombuttons[3:]:
                if i is None:
                    continue
                b=wx.Button(self.panel,-1,i[0])
                b.properties=i
                b.SetBackgroundColour(i[2])
                b.Bind(wx.EVT_BUTTON,self.procbutton)
                cs.Add(b,pos=(posindex%5,1+posindex/5),span=(1,1))
                posindex+=1
        except:
            pass
        
        lls.Add(cs)
        
        
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
        
        # disable all printer controls until we connect to a printer
#        self.pausebtn.Hide()
#        for i in self.printerControls:
#            i.Disable()
        
        #self.panel.Fit()
        #uts.Layout()
        
    def showwin(self,event):
#        if(self.f is not None):
        self.gwindow.Show()
        
    def do_pos(self,e):
        self.p.send_now("M114")

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
       self.zdist_changed = True
       self.settings._set("z_dist",radioSelected.GetLabel())

    def do_zneg(self,e):
        self.onecmd("move Z -" + self.zdist)

    def do_zpos(self,e):
        self.onecmd("move Z " + self.zdist)
        
    def setfeeds(self,e):
        self.feedrates_changed = True
        try:
           self.settings._set("e_feedrate",self.efeedc.GetValue())
        except:
            pass
        try:
            self.settings._set("z_feedrate",self.zfeedc.GetValue())
        except:
            pass
        try:
            self.settings._set("xy_feedrate",self.xyfeedc.GetValue())
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
        if hasattr(self,"feedrates_changed"):
            self.save_in_rc("set xy_feedrate","set xy_feedrate %d" % self.settings.xy_feedrate)
            self.save_in_rc("set z_feedrate","set z_feedrate %d" % self.settings.z_feedrate)
            self.save_in_rc("set e_feedrate","set e_feedrate %d" % self.settings.e_feedrate)
        if hasattr(self,"zdist_changed"):
            self.save_in_rc("set z_dist","set z_dist %f" % self.settings.z_dist)
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
#                wx.CallAfter(self.tempdisp.SetLabel,self.tempreport.strip().replace("ok ",""))
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
                if(self.monitor):
                    time.sleep(self.sleepslider.GetValue())
                else:
                    time.sleep(1)
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
#            wx.CallAfter(self.tempdisp.SetLabel,self.tempreport.strip().replace("ok ",""))
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
#            self.startcb()
            return
        if "Done printing file" in l:
            wx.CallAfter(self.status.SetStatusText,l)
            self.sdprinting=0
            self.recvlisteners.remove(self.waitforsdresponse)
#            self.endcb()
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
#            if self.p.online:
#                    wx.CallAfter(self.printbtn.Enable)
                    
            wx.CallAfter(self.status.SetStatusText,"Loaded "+self.filename+", %d lines"%(len(self.f),))
#            wx.CallAfter(self.pausebtn.Hide)
#            wx.CallAfter(self.printbtn.SetLabel,"Print")

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
        basedir=self.settings.last_file_path
        if not os.path.exists(basedir):
            basedir = "."
            try:
                basedir=os.path.split(self.filename)[0]
            except:
                pass
        dlg=wx.FileDialog(self,"Open file to print",basedir,style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
        dlg.SetWildcard("STL and GCODE files (;*.gcode;*.g;*.stl;*.STL;*.pla;*.abs")
        if(dlg.ShowModal() == wx.ID_OK):
            name=dlg.GetPath()
            if not(os.path.exists(name)):
                self.status.SetStatusText("File not found!")
                return
            path = os.path.split(name)[0]
            if path != self.settings.last_file_path:
                self.set("last_file_path",path)
            if name.lower().endswith(".stl"):
                self.skein(name)
            else:
                self.f=[i.replace("\n","").replace("\r","") for i in open(name)]
                self.filename=name
                self.status.SetStatusText("Loaded "+name+", %d lines"%(len(self.f),))
#                self.printbtn.SetLabel("Print")
#                self.pausebtn.SetLabel("Pause")
#                self.pausebtn.Hide()
#                if self.p.online:
#                    self.printbtn.Enable()
                threading.Thread(target=self.loadviz).start()
                
    def loadviz(self):
        self.gviz.clear()
#        self.gwindow.p.clear()
        for i in self.f:
            self.gviz.addgcode(i)
            self.gwindow.p.addgcode(i)
        self.gviz.showall=1
        wx.CallAfter(self.gviz.Refresh)
                
    def printfile(self,event):
        if self.paused:
            self.p.paused=0
            self.paused=0
            self.on_startprint()
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
        self.on_startprint()
        self.p.startprint(self.f)
    
    def on_startprint(self):
        self.pausebtn.SetLabel("Pause")
        self.pausebtn.Show()
        self.printbtn.SetLabel("Restart")
    
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
        self.on_startprint()
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
        if port != self.settings.port:
            self.set("port",port)
        if baud != self.settings.baudrate:
            self.set("baudrate",str(baud))
        threading.Thread(target=self.statuschecker).start()
        
        
    def disconnect(self,event):
        self.p.disconnect()
        self.statuscheck=False
        
        self.disconnectbtn.Disable();
        self.connectbtn.Enable()
#        self.printbtn.Disable();
#        self.pausebtn.Hide();
#        for i in self.printerControls:
#            i.Disable()
        
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
            
class macroed(wx.Frame):
    """Really simple editor to edit macro definitions"""
    def __init__(self,macro_name,definition,callback):
        self.indent_chars = "  "
        wx.Frame.__init__(self,None,title="macro %s" % macro_name)
        self.callback = callback
        self.panel=wx.Panel(self,-1)
        titlesizer=wx.BoxSizer(wx.HORIZONTAL)
        title = wx.StaticText(self.panel,-1,"  macro %s: "%macro_name)
        title.SetFont(wx.Font(11,wx.NORMAL,wx.NORMAL,wx.BOLD))
        titlesizer.Add(title,1)
        self.okb = wx.Button(self.panel,-1,"Save")
        self.okb.Bind(wx.EVT_BUTTON,self.save)
        titlesizer.Add(self.okb)
        self.cancelb = wx.Button(self.panel,-1,"Cancel")
        self.cancelb.Bind(wx.EVT_BUTTON,self.close)
        titlesizer.Add(self.cancelb)
        topsizer=wx.BoxSizer(wx.VERTICAL)
        topsizer.Add(titlesizer,0,wx.EXPAND)
        self.e=wx.TextCtrl(self.panel,style=wx.TE_MULTILINE+wx.HSCROLL,size=(200,200))
        self.e.SetValue(self.unindent(definition))
        topsizer.Add(self.e,1,wx.ALL+wx.EXPAND)
        self.panel.SetSizer(topsizer)
        topsizer.Layout()
        topsizer.Fit(self)
        self.Show()
    def save(self,ev):
        self.Close()
        self.callback(self.reindent(self.e.GetValue()))
    def close(self,ev):
        self.Close()
    def unindent(self,text):
        import re
        self.indent_chars = text[:len(text)-len(text.lstrip())]
        unindented = ""
        lines = re.split(r"(?:\r\n?|\n)",text)
        #print lines
        if len(lines) <= 1:
            return text
        for line in lines:
            if line.startswith(self.indent_chars):
                unindented += line[len(self.indent_chars):] + "\n"
            else:
                unindented += line + "\n"
        return unindented
    def reindent(self,text):
        import re
        lines = re.split(r"(?:\r\n?|\n)",text)
        if len(lines) <= 1:
            return text
        reindented = ""
        for line in lines:
            reindented += self.indent_chars + line + "\n"
        return reindented
        
        
if __name__ == '__main__':
    app = wx.App(False)
    main = PronterWindow()
    main.Show()
    try:
        app.MainLoop()
    except:
        pass

