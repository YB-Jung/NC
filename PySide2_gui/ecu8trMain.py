#from io import IncrementalNewlineDecoder
#import logging
#from re import A
#import pyvisa

from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc

#from nrc import NRC_2_Str
import sys
import getopt
import struct
import time
import socket

from datetime import datetime

#custom imports
from mainFordSKModule import Ui_MainWindow
from tle9012source import  TLE9012

# sys.path.insert(0,'..')
# sys.path.insert(0, "../bms")
# sys.path.insert(0,'../env/Lib/site-packages')
sys.path.append(r'D:\001_project\2023\ecu8tr-gui-mak-1-12-24\bms')

from kvaser import Kvaser
from docan import DoCAN
from canlib import canlib

# Default source address
ID_SA = 0x0a
# Default Target address
ID_TA = 0x0b
OPTION_CONTROL = 0x03
UDS_IOCBI = 0x2F
ID1 = 0x00

UDP_TX_PORT_NUM = 8889 #default port address for initial connection
UDP_RX_PORT_NUM = 8888 #default port address for initial connection
ECU8TR_IP_ADDRESS = "192.168.1.170" # Default IP address for initial connection



class MainWindow(qtw.QMainWindow):
    
    readTimer = qtc.QTimer()
    expectedNumOfAFENodes = 1   #defaults to expect 1 node for min connection

    
    def __init__(self,parent = None):
        super(MainWindow,self).__init__(parent)        
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.ui.pushButtonStream.clicked.connect(self.buttonStreamClicked)
        self.ui.pushButtonConnect.clicked.connect(self.buttonConnectClicked)
        self.ui.pushButtonTest.clicked.connect(self.buttonTestClicked)
        
        #init CAN/BMS comms
        self.ui.radioButtonCANRX.setChecked(True)
        self.ui.radioButtonCANTX.setChecked(True)
        self.ui.radioButtonCANRX.setChecked(False)
        self.ui.radioButtonCANTX.setChecked(False)

        self.ui.listWidgetCANMessages.addItem("Peek CAN messages")

    def buttonTestClicked(self):
        #Commands are sent automatically to connect, disconnect, stream and stop streaming data
        if (self.ui.pushButtonConnect.text() == "CONNECT"):     #don't allow automated commands if using manual mode

            if (self.ui.pushButtonTest.text() == "TEST"):
                #RED blinking LED goes to GREEN blinking LED
                if (self.ui.comboBoxComms.currentText() =="CAN"):
                    print("Starting CAN Mode")
                    self.readTimer.timeout.connect(self.peekECU8TRStream)
                    self.connectModuleCAN()
                    self.ui.radioButtonCANRX.setChecked(False)
                elif (self.ui.comboBoxComms.currentText() =="ETHERNET"):
                    print("Starting Ethernet Mode")
                    self.readTimer.timeout.connect(self.peekECU8TRStreamIP)
                    self.connectModuleIP()
                    time.sleep(1)
                    self.streamModuleIP()
                    
                self.readTimer.start(200)
                self.ui.pushButtonTest.setText("END TEST")
                self.ui.labelActiveNodes.setText("1")
                
            else:
                #goes from GREEN blinking LED to RED blinking LED
                self.readTimer.stop()

                if (self.ui.comboBoxComms.currentText() =="CAN"):
                    self.readTimer.timeout.disconnect(self.peekECU8TRStream)                
                    self.disconnectModuleCAN()
                elif (self.ui.comboBoxComms.currentText() =="ETHERNET"):                
                    self.disconnectModuleIP()
                    time.sleep(1)
                    self.stopStreamModuleIP()

                self.ui.pushButtonTest.setText("TEST")
                self.ui.labelActiveNodes.setText("0")

    def buttonConnectClicked(self):
    #sends connect and disconnect commands only
        
        if (self.ui.pushButtonStream.text() == "STREAM"):    #don't allow sending disconnect message if streaming

            if (self.ui.pushButtonConnect.text() == "CONNECT"):
                #RED blinking LED goes to solid GREEN LED    
                if (self.ui.comboBoxComms.currentText() =="CAN"):
                    print("Connecting in CAN Mode")                
                    self.connectModuleCAN()                
                elif (self.ui.comboBoxComms.currentText() =="ETHERNET"):
                    print("Connecting in Ethernet Mode")                
                    self.connectModuleIP()
                        
                self.ui.pushButtonConnect.setText("DISCONNECT")
                self.ui.labelActiveNodes.setText("1")
                
            else:
                #solid GREEN LED goes to RED blinking LED
                if (self.ui.comboBoxComms.currentText() =="CAN"):                
                    self.disconnectModuleCAN()
                elif (self.ui.comboBoxComms.currentText() =="ETHERNET"):                
                    self.disconnectModuleIP()

                self.ui.pushButtonConnect.setText("CONNECT")
                self.ui.labelActiveNodes.setText("0")

    def buttonStreamClicked(self):
    #sends start and stop streaming commands
        if (self.ui.pushButtonConnect.text() == "DISCONNECT"):  #don't allow start streaming message if not connected
            #GREEN solid LED goes to GREEN blinking LED
            if (self.ui.pushButtonStream.text() == "STREAM"):
                    
                if (self.ui.comboBoxComms.currentText() =="CAN"):
                    print("Streaming in CAN Mode")
                    self.readTimer.timeout.connect(self.peekECU8TRStream)
                    self.connectModuleCAN()
                    self.ui.radioButtonCANRX.setChecked(False)
                elif (self.ui.comboBoxComms.currentText() =="ETHERNET"):
                    print("Streaming in Ethernet Mode")
                    self.readTimer.timeout.connect(self.peekECU8TRStreamIP)                
                    self.streamModuleIP()
                    
                self.readTimer.start(200)
                self.ui.pushButtonStream.setText("END STREAM")
                self.ui.labelActiveNodes.setText("1")
                
            else:
                #GREEN blinking LED goes to SOLID GREEN LED
                self.readTimer.stop()

                if (self.ui.comboBoxComms.currentText() =="CAN"):
                    self.readTimer.timeout.disconnect(self.peekECU8TRStream)                
                    self.disconnectModuleCAN()
                elif (self.ui.comboBoxComms.currentText() =="ETHERNET"):                
                    self.stopStreamModuleIP()

                self.ui.pushButtonStream.setText("STREAM")
                self.ui.labelActiveNodes.setText("0")
            
            

    def processFrameIntoFullMetrics(self,results_frame):
        #populates full metrics frame from individuals for ease of UI populating
   
        #print(int.from_bytes(results_frame[7:8],"little"))
        frame_id = int.from_bytes(results_frame[7:8],"little")

        if (frame_id == 1):
            print("frame 1")
            conversion_val = int.from_bytes(results_frame[0:2], "big")
            self.ui.labelHSModuleVal.setText(str(float(conversion_val)/1000))
            self.ui.labelModuleVal.setText(str(float(conversion_val)/1000))            
            conversion_val = int.from_bytes(results_frame[2:4], "big")
            self.ui.labelCellValHS1.setText(str(float(conversion_val)/1000))
            self.ui.progressBarCellValHS1.setValue(100/42*(conversion_val/100))
            conversion_val = int.from_bytes(results_frame[4:6], "big")
            self.ui.labelCellValHS2.setText(str(float(conversion_val)/1000))
            self.ui.progressBarCellValHS2.setValue(100/42*(conversion_val/100))

        elif (frame_id == 2):
            print("frame 2")
            conversion_val = int.from_bytes(results_frame[0:2], "big")
            self.ui.labelCellValHS3.setText(str(float(conversion_val)/1000))
            self.ui.progressBarCellValHS3.setValue(100/42*(conversion_val/100))
            conversion_val = int.from_bytes(results_frame[2:4], "big")
            self.ui.labelCellValHS4.setText(str(float(conversion_val)/1000))
            self.ui.progressBarCellValHS4.setValue(100/42*(conversion_val/100))
            conversion_val = int.from_bytes(results_frame[4:6], "big")
            self.ui.labelCellValHS5.setText(str(float(conversion_val)/1000))
            self.ui.progressBarCellValHS5.setValue(100/42*(conversion_val/100))

        elif (frame_id == 3):
            print("frame 3")
            conversion_val = int.from_bytes(results_frame[0:2], "big")
            self.ui.labelCellValHS6.setText(str(float(conversion_val)/1000))
            self.ui.progressBarCellValHS6.setValue(100/42*(conversion_val/100))
            conversion_val = int.from_bytes(results_frame[2:4], "big")
            self.ui.labelCellValHS7.setText(str(float(conversion_val)/1000))
            self.ui.progressBarCellValHS7.setValue(100/42*(conversion_val/100))
            conversion_val = int.from_bytes(results_frame[4:6], "big")
            self.ui.labelCellValHS8.setText(str(float(conversion_val)/1000))
            self.ui.progressBarCellValHS8.setValue(100/42*(conversion_val/100))

        elif (frame_id == 4):
            print("frame 4")
            conversion_val = int.from_bytes(results_frame[0:2], "big")
            self.ui.labelCellValHS9.setText(str(float(conversion_val)/1000))
            self.ui.progressBarCellValHS9.setValue(100/42*(conversion_val/100))
            conversion_val = int.from_bytes(results_frame[2:4], "big")
            self.ui.labelCellValHS10.setText(str(float(conversion_val)/1000))
            self.ui.progressBarCellValHS10.setValue(100/42*(conversion_val/100))
            conversion_val = int.from_bytes(results_frame[4:6], "big")
            self.ui.labelCellValHS11.setText(str(float(conversion_val)/1000))
            self.ui.progressBarCellValHS11.setValue(100/42*(conversion_val/100))
        elif (frame_id == 5):
            print("frame 5")
            conversion_val = int.from_bytes(results_frame[0:2], "big")
            self.ui.labelCellValHS12.setText(str(float(conversion_val)/1000))
            self.ui.progressBarCellValHS12.setValue(100/42*(conversion_val/100))
            #conversion_val = int.from_bytes(results_frame[2:4], "big")
            #self.ui.labelCellValHS4.setText(str(float(conversion_val)/1000))
            #conversion_val = int.from_bytes(results_frame[4:6], "big")
            #self.ui.labelCellValHS5.setText(str(float(conversion_val)/1000))            
        elif (frame_id == 6):
            print("frame 6")
            conversion_val = int.from_bytes(results_frame[0:2], "big")
            self.ui.labelTempDieVal.setText(str(float(conversion_val)/10))
            conversion_val = int.from_bytes(results_frame[2:4], "big")
            self.ui.labelTemp1Val.setText(str(float(conversion_val-10000)/1000))
            conversion_val = int.from_bytes(results_frame[4:6], "big")
            self.ui.labelTemp2Val.setText(str(float(conversion_val-10000)/1000))
        elif (frame_id == 7):
            print("frame 7")
            conversion_val = int.from_bytes(results_frame[0:2], "big")
            self.ui.labelTemp3Val.setText(str(float(conversion_val-10000)/1000))
            conversion_val = int.from_bytes(results_frame[2:4], "big")
            self.ui.labelTemp4Val.setText(str(float(conversion_val-10000)/1000))
            conversion_val = int.from_bytes(results_frame[4:6], "big")
            self.ui.labelTemp5Val.setText(str(float(conversion_val-10000)/1000))
        else:
            print("error in parsing CAN message number D7")
        
               
    def peekECU8TRStream(self):
        #check for CAN messages
        
        ch = canlib.openChannel(0, bitrate=canlib.canBITRATE_500K)
        ch.setBusOutputControl(canlib.canDRIVER_NORMAL)
        ch.busOn()
        
        timeout = 0.5
        
        print("Peeking CAN messages...")

        for loop_count in range(7):        
            frame = ch.read(timeout=int(timeout * 10000))
            frame_byte_data = bytes(frame.data)
            self.processFrameIntoFullMetrics(frame_byte_data)
            self.ui.listWidgetCANMessages.addItem(str(frame))
                    
        ch.busOff()
        ch.close()       

    def peekECU8TRStreamIP(self):
        #check for IP messages
               
        timeout = 0.5
        
        print("Peeking IP messages...")

        
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(('192.168.1.8', UDP_RX_PORT_NUM))    
            sock.settimeout(1)
            for loop_count in range(7):                
                
                try:
                    data, address = sock.recvfrom(8)
                    # print(data)
                    self.processFrameIntoFullMetrics(data)
                    self.ui.listWidgetCANMessages.addItem(str(data))
                    #print(f"Received {len(data)} bytes from {address}: {data.decode()}")
                except sock.timeout:
                    print("UDP timeout error")
                    continue
              
                
                
        


    def connectModuleCAN(self):
        #connect to module AFEs based on config
        print("connecting to battery module via CAN")

        canObj = Kvaser()
        canObj.start()
        bms = DoCAN( ID_SA, ID_TA, canObj )  
        bms.setRawOutput( False )

        ecu8tr_addr_connect = 0x12010a0b
        ecu8tr_addr_stream = 0x12020a0b
        disconnect_from_module = [0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        stop_stream_module = [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        
        bms.SendCANUniversalMessage(ecu8tr_addr_connect, disconnect_from_module)
        bms.SendCANUniversalMessage(ecu8tr_addr_stream, stop_stream_module)

        canObj.running = False
        del bms
        del canObj

    def connectModuleIP(self):
        #connect to module AFEs based on config
        
        connect_to_module = bytearray()        
        connect_to_module.append( 0x12 )  #Message ID 0x1201
        connect_to_module.append( 0x01 )  #Message ID 0x1201
        connect_to_module.append( 0x01 )
        connect_to_module.append( 0x01 )
        connect_to_module.append( 0x00 )
        connect_to_module.append( 0x00 )
        connect_to_module.append( 0x00 )
        connect_to_module.append( 0x00 )
        connect_to_module.append( 0x00 )
        connect_to_module.append( 0x00 )
        
        print("connecting to battery module via IP")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(connect_to_module, (ECU8TR_IP_ADDRESS, UDP_TX_PORT_NUM))            

    def streamModuleIP(self):
        #stream readings from module        

        start_stream_module = bytearray()        
        start_stream_module.append( 0x12 )  #Message ID 0x1202
        start_stream_module.append( 0x02 )  #Message ID 0x1202
        start_stream_module.append( 0x01 )
        start_stream_module.append( 0x01 )
        start_stream_module.append( 0x00 )
        start_stream_module.append( 0x00 )
        start_stream_module.append( 0x00 )
        start_stream_module.append( 0x00 )
        start_stream_module.append( 0x00 )
        start_stream_module.append( 0x00 )

        print("streaming data from battery module via IP")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:        
            sock.sendto(start_stream_module, (ECU8TR_IP_ADDRESS, UDP_TX_PORT_NUM))        


    def disconnectModuleCAN(self):
        #connect to module AFEs based on config
        print("disconnecting from battery module via CAN")

        canObj = Kvaser()
        canObj.start()
        bms = DoCAN( ID_SA, ID_TA, canObj )  
        bms.setRawOutput( False )

        ecu8tr_addr = 0x12010a0b
        ecu8tr_addr_stream = 0x12020a0b
        disconnect_from_module = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        stop_stream_module = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        
        bms.SendCANUniversalMessage(ecu8tr_addr_stream, stop_stream_module)
        bms.SendCANUniversalMessage(ecu8tr_addr, disconnect_from_module)
        
        canObj.running = False
        del bms
        del canObj
    
    def disconnectModuleIP(self):
        #connect to module AFEs based on config
        print("disconnecting from battery module via IP")

        #disconnect_from_module = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        #stop_stream_module = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

        disconnect_from_module = bytearray()        
        disconnect_from_module.append( 0x12 )  #Message ID 0x1201
        disconnect_from_module.append( 0x01 )  #Message ID 0x1201
        disconnect_from_module.append( 0x00 )
        disconnect_from_module.append( 0x00 )
        disconnect_from_module.append( 0x00 )
        disconnect_from_module.append( 0x00 )
        disconnect_from_module.append( 0x00 )
        disconnect_from_module.append( 0x00 )
        disconnect_from_module.append( 0x00 )
        disconnect_from_module.append( 0x00 )
       
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(disconnect_from_module, (ECU8TR_IP_ADDRESS, UDP_TX_PORT_NUM))            

    def stopStreamModuleIP(self):
        #stop streaming from module AFEs based on config
        print("stop streaming from battery module via IP")

        stop_stream_module = bytearray()        
        stop_stream_module.append( 0x12 )  #Message ID 0x1202
        stop_stream_module.append( 0x02 )  #Message ID 0x1202
        stop_stream_module.append( 0x00 )
        stop_stream_module.append( 0x00 )
        stop_stream_module.append( 0x00 )
        stop_stream_module.append( 0x00 )
        stop_stream_module.append( 0x00 )
        stop_stream_module.append( 0x00 )
        stop_stream_module.append( 0x00 )
        stop_stream_module.append( 0x00 )
        
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:            
            sock.sendto(stop_stream_module, (ECU8TR_IP_ADDRESS, UDP_TX_PORT_NUM)) 

    def genConnectMessageCAN(self):
        ID2 = 0x0A
        CANID0a = 0x12
        CANID0b = 0x01
        CANID0c = 0x0B
        CANID0d = 0x0A
        CELLMODULE_BYTE0 = 1
        CELLMODULE_BYTE1 = 1
        frame = bytearray()
        frame += struct.pack( ">B", CANID0a )
        frame += struct.pack( ">B", CANID0b )
        frame += struct.pack( ">B", CANID0c )
        frame += struct.pack( ">B", CANID0d )
        frame += struct.pack( ">B", CELLMODULE_BYTE0 )
        frame += struct.pack( ">B", CELLMODULE_BYTE1 )        
        return frame


    def enableStreamModule(self):
        #initiate the reading and streaming of cell data
        print("initiate cell data streaming")



    def readNodes(self):
        #self.onReadNode1()
        print("in Read Timer")
        if (self.ui.radioButtonCANRX.isChecked()):
            self.ui.radioButtonCANRX.setChecked(False)
            print("was checked")
        else:
            self.ui.radioButtonCANRX.setChecked(False)
            print("was not checked")
        
        self.readTimer.start(1000)

        
  
def main():       
    print("Starting ECU8TR Application V0.0.3")
    # Handle high resolution displays:
    if hasattr(qtc.Qt, 'AA_EnableHighDpiScaling'):
        qtw.QApplication.setAttribute(qtc.Qt.AA_EnableHighDpiScaling, True)
    if hasattr(qtc.Qt, 'AA_UseHighDpiPixmaps'):
        qtw.QApplication.setAttribute(qtc.Qt.AA_UseHighDpiPixmaps, True)
    
    app =qtw.QApplication([])
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()