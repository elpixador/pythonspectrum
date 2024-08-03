ZXports = None # el poso aquí per a que sigui global
ZXmem = bytearray(65536)

class IO(object):
    _addresses = []
    def read(self, address):
        pass
    def write(self, address, value):
        pass
    
class Interruptable(object):
    def interrupt(self):
        print ("interrupt")
        pass
   

    
class IOMap(object):
    def __init__(self):
        self.address = {}
        pass
    def addDevice(self, dev):
        assert isinstance(dev, IO)
        for i in dev._addresses:
            self.address[i] = dev
        
    def interupt(self):
        pass

    def read(self, portfull):
        port = portfull & 0xFF
        if port in self.address:
            return self.address[port].read(portfull)
        else:
            return 0x00

    def write(self, portfull, value):
        port = portfull & 0xFF
        if port in self.address:
            self.address[port].write(portfull, value)

    def keypress(self, scancode):
        self.address[0xFE].keypress(scancode)

    def keyrelease(self, scancode):
        self.address[0xFE].keyrelease(scancode)
