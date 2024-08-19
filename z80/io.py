ZXports = None # els poso aquí per a que siguin globals
ZXRegisterR = 0

class mem(object):
    _rom0 = bytearray(16384)
    _rom1 = bytearray(16384)
    _bank = [0]*8
    _scrath = bytearray(16384)
    _memread = [0]*4
    _memwrit = [0]*4
    _screen = 0
    _locked = False

    def __init__(self):
        for n in range(8):
            self._bank[n] = bytearray(16384)
        self.reset()

    def reset(self):
        self._memread[0] = self._rom0                
        self._memread[1] = self._bank[5]
        self._memread[2] = self._bank[2]
        self._memread[3] = self._bank[0]

        self._memwrit[0] = self._scrath
        self._memwrit[1] = self._memread[1]
        self._memwrit[2] = self._memread[2]
        self._memwrit[3] = self._memread[3]

        self._screen = self._bank[5]
        self._locked = False

    def __getitem__(self, index):
        return self._memread[index >> 14][index & 0x3FFF]

    def __setitem__(self, index, value):
        self._memwrit[index >> 14][index & 0x3FFF] = value

    def screen(self, index):
        return self._screen[index]

    def writeROM0(self, index, value):
        self._rom0[index & 0x3FFF] = value

    def writeROM1(self, index, value):
        self._rom1[index & 0x3FFF] = value
    
    def writeBank(self, bank, index, value):
        self._bank[bank & 0x07][index & 0x3FFF] = value

    def writeROM(self, index, value):
        self.writeROM0(index, value)

    def changeMap(self, map):
        if (self._locked): return

        self._memread[3] = self._bank[map & 0x07]
        self._memwrit[3] = self._memread[3]

        if (map & 0x08): self._screen = self._bank[7]
        else: self._screen = self._bank[5]

        if (map & 0x10): self._memread[0] = self._rom1
        else: self._memread[0] = self._rom0

        if (map & 0x20): self._locked = True
    
    def set48mode(self):
        self.changeMap(0b00110000)


ZXmem = mem()

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
   

class portFD(IO):
    _addresses = [0xFD]

    _audioreg = [0]*16
    _audiosel = 0

    def read(self, address):
        if address == 0xFFFD: return self._audioreg[self._audiosel]
        else: return 0xFF

    def write(self, address, value):
        if (address == 0x7FFD): # memory mapper
            ZXmem.changeMap(value)
        elif (address == 0xFFFD): # select audio register
            self._audiosel = value & 0x0F
        elif (address == 0xBFFD): # write to selected audio register
            self._audioreg[self._audiosel] = value
    
    
class IOMap(object):
    def __init__(self):
        self.address = {}
        self.initAY() # prova, no hauria d'estar aqui
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

    # funcions de prova, no haurien d'estar aquí
    def initAY(self):
        self.audioAPeriod = 0
        self.audioAToca = False
        self.audioBPeriod = 0
        self.audioBToca = False
        self.audioCPeriod = 0
        self.audioCToca = False
        self.audioDecPeriod = 20 # Ajustament de la freqüència

    def calcAY(self):
        ay = self.address[0xFD]
        audioEnable = ay._audioreg[7]

        if (audioEnable & 0x01): audioAWord = 0
        else:
            if (self.audioAPeriod <= 0):
                self.audioAToca = not self.audioAToca
                self.audioAPeriod = ((ay._audioreg[1] << 8) | ay._audioreg[0])
            else: self.audioAPeriod -= self.audioDecPeriod
            if self.audioAToca: audioAWord = -625 * ay._audioreg[8]
            else: audioAWord = 0

        if (audioEnable & 0x02): audioBWord = 0
        else:
            if (self.audioBPeriod <= 0):
                self.audioBToca = not self.audioBToca
                self.audioBPeriod = ((ay._audioreg[3] << 8) | ay._audioreg[2])
            else: self.audioBPeriod -= self.audioDecPeriod
            if self.audioBToca: audioBWord = -625 * ay._audioreg[9]
            else: audioBWord = 0

        if (audioEnable & 0x04): audioCWord = 0
        else:
            if (self.audioCPeriod <= 0):
                self.audioCToca = not self.audioCToca
                self.audioCPeriod = ((ay._audioreg[5] << 8) | ay._audioreg[4])
            else: self.audioCPeriod -= self.audioDecPeriod
            if self.audioCToca: audioCWord = -625 * ay._audioreg[10]
            else: audioCWord = 0

        return audioAWord + audioBWord + audioCWord

