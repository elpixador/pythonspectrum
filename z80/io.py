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

class ay38912(object):
    _audioreg = [0]*16
    _audiosel = 0

    _audioregs01 = 0
    _audioregs23 = 0
    _audioregs45 = 0
    _audiovolums = (
        (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0), # volums 0-16 (16=envelope mode, emulat com a to normal a volum 7)
        (0, -625*1, -625*2, -625*3, -625*4, -625*5, -625*6, -625*7, -625*8, -625*9, -625*10, -625*11, -625*12, -625*13, -625*14, -625*15, -625*7)
    )

    _audioAPeriod = 0
    _audioAToca = 0
    _audioBPeriod = 0
    _audioBToca = 0
    _audioCPeriod = 0
    _audioCToca = 0
    _audioNPeriod = 0
    _audioNRand = 1
    _audioDecPeriod = 240500 // 12025 # Ajustament de la freqüència

    def __init__(self):
        self.reset()
    
    def reset(self):
        for n in range(len(self._audioreg)):
            self._audioreg[n] = 0
        self._audioreg[7] = 0x3F
        self._audioregs01 = 0
        self._audioregs23 = 0
        self._audioregs45 = 0
        self._audioAPeriod = 0
        self._audioAToca = 0
        self._audioBPeriod = 0
        self._audioBToca = 0
        self._audioCPeriod = 0
        self._audioCToca = 0
        self._audioNPeriod = 0
        self._audioNRand = 1

    def setaudiofreq(self, freq):
        self._audioDecPeriod = 240500 // freq

    def regselect(self, reg):
        self._audiosel = reg & 0x0F

    def regread(self):
        return self._audioreg[self._audiosel]
    
    def regwrite(self, value):
        self._audioreg[self._audiosel] = value
        match self._audiosel:
            case 0 | 1:
                self._audioregs01 = self._audioreg[0] | ((self._audioreg[1] & 0x0F) << 8)
            case 2 | 3:
                self._audioregs23 = self._audioreg[2] | ((self._audioreg[3] & 0x0F) << 8)
            case 4 | 5:
                self._audioregs45 = self._audioreg[4] | ((self._audioreg[5] & 0x0F) << 8)

    def calc(self):
        audioEnable = self._audioreg[7] ^ 0xFF # Lògica inversa
        if not(audioEnable & 0x3F): return 0
        
        res = 0

        if (audioEnable & 0x38): # soroll
            noise = self._audioNRand & 0x01
            if (self._audioNPeriod <= 0):                
                if (noise): self._audioNRand ^= 0x24000 # https://github.com/openMSX/openMSX/blob/master/src/sound/AY8910.cc
                self._audioNRand >>= 1
                self._audioNPeriod = self._audioreg[6] & 0x1F
            else: self._audioNPeriod -= self._audioDecPeriod

        if (audioEnable & 0x09): # canal A
            if (audioEnable & 0x01):
                if (self._audioAPeriod <= 0):
                    self._audioAToca ^= 1
                    self._audioAPeriod = self._audioregs01
                else: self._audioAPeriod -= self._audioDecPeriod
                tone = self._audioAToca
                if (audioEnable & 0x08): tone |= noise
            else: tone = noise            
            res += self._audiovolums[tone][self._audioreg[8]]

        if (audioEnable & 0x12): # canal B
            if (audioEnable & 0x02):
                if (self._audioBPeriod <= 0):
                    self._audioBToca ^= 1
                    self._audioBPeriod = self._audioregs23
                else: self._audioBPeriod -= self._audioDecPeriod
                tone = self._audioBToca
                if (audioEnable & 0x10): tone |= noise
            else: tone = noise
            res += self._audiovolums[tone][self._audioreg[9]]

        if (audioEnable & 0x24): # canal C
            if (audioEnable & 0x04):
                if (self._audioCPeriod <= 0):
                    self._audioCToca ^= 1
                    self._audioCPeriod = self._audioregs45
                else: self._audioCPeriod -= self._audioDecPeriod
                tone = self._audioCToca
                if (audioEnable & 0x20): tone |= noise
            else: tone = noise            
            res += self._audiovolums[tone][self._audioreg[10]]

        return res


ZXmem = mem()
ZXay = ay38912()

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

    def read(self, address):
        if address == 0xFFFD: return ZXay.regread()
        else: return 0xFF

    def write(self, address, value):
        if (address == 0x7FFD): # memory mapper
            ZXmem.changeMap(value)
        elif (address == 0xFFFD): # select audio register
            ZXay.regselect(value)
        elif (address == 0xBFFD): # write to selected audio register
            ZXay.regwrite(value)
    
    
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
