import pygame
# PyGame_GUI https://pygame-gui.readthedocs.io/en/latest/quick_start.html
from .constants import ZX_RES, rompath, romfile48k, romfile128k, colorTable
from .sound import AudioInterface
## Z80 CPU Emulator / https://github.com/cburbridge/z80
from z80 import util, io, registers, instructions
from .other import *


class Spectrum:
    def __init__(self):
        self.plusmode = True # True = Spectrum 128 / False = ZX Spectrum 48k  
        self.screen = ZXScreen(ZX_RES)
        self.audio = AudioInterface()  # this is where the audio stuff will happen
        self.memory = io.mem()
        self.cpu = Z80()
        self.ports = portFE()
        self.flashCount = 0
        self.flashReversed = False
        self.cicles = 0 
        self.is_running = True

    # Load ROM
    def readROM(self): 
        if self.plusmode == True: 
            print("Mode 128k ON")
            zxromfile = romfile128k
        else: 
            print("Mode 48k ON")
            zxromfile = romfile48k
        zxromfile = rompath + "/" + zxromfile
        f = open(zxromfile, mode="rb")
        dir = 0
        data = f.read(1)
        while (data):
            self.memory.writeROM(dir, int.from_bytes(data, byteorder='big', signed=False))
            dir = dir + 1
            data = f.read(1)
        f.close()
        if (self.plusmode == True):
            zxromfile = zxromfile[::-1].replace('0', '1', 1)[::-1]
            f = open(zxromfile, mode="rb")
            dir = 0
            data = f.read(1)
            while (data):
                self.memory.writeROM1(dir, int.from_bytes(data, byteorder='big', signed=False))
                dir = dir + 1
                data = f.read(1)
            f.close()
        print("ROM loaded")

    def get_surface(self):
        return self.screen

    def run_frame(self):
        # gestió del flash
        if ((self.flashCount & 0b00011111) == 0):
            self.flashReversed = not self.flashReversed
        self.flashCount += 1

        for y in range(312):
            self.cicles += 224
            # cicles += 248
            self.cicles = self.cpu.step_instruction(self.cicles)

            if (self.audio.playAudio):
                # buffer d'audio
                if (self.audio.audiocount == self.audio.bufferlen):
                    self.audio.audiocount = 0
                    self.audio.stream.write(self.audio.buffaudio) #comentar en cas d'anar lent                
                else:
                    self.audio.buffaudio[self.audio.audiocount] = self.audio.audioword # + io.ZXay.calc()
                    self.audio.audiocount += 1

            self.screen.renderline(y, self.memory)

        self.cpu.interrupt()


class ZXScreen(pygame.Surface):    

    def __new__(cls, size):
        # creates a new pygame.Surface object
        return super(ZXScreen, cls).__new__(cls)

    def __init__(self, size):
        super().__init__(size)
        self.screenCache = []
        self.unFlash = [[], []]
        self.flashReversed = False
        self.bcolor = 0
        
        for i in range(6144):
            self.screenCache.append([-1, -1, -1, -1])  # attr, ink, paper, border
        for i in range(256):
            self.unFlash[0].append(i)
            if (i & 0x80): self.unFlash[1].append((i & 0xC0) | ((i & 0x38) >> 3) | ((i & 0x07) << 3))
            else: self.unFlash[1].append(i)

    def decodecolor(self, atribut):
        # http://www.breakintoprogram.co.uk/hardware/computers/zx-spectrum/screen-memory-layout
        coltbl = colorTable[(atribut & 0b01000000)>>6]
        return (coltbl[atribut & 0b00000111], coltbl[(atribut & 0b00111000)>>3])

    def renderline(self, screenY, mem):
        # (376, 312)
        if (screenY < 60) or (screenY > 251):
            if self.screenCache[screenY][2] != self.bcolor:
                pygame.draw.line(self, colorTable[0][self.bcolor], (0, screenY), (375, screenY))
                self.screenCache[screenY][2] = self.bcolor
        else:
            y = screenY - 60
            adr_attributs = 6144 + ((y >> 3)*32)
            # 000 tt zzz yyy xxxxx
            adr_pattern = (((y & 0b11000000) | ((y & 0b111) << 3) | (y & 0b111000) >> 3) << 5)
            if self.screenCache[screenY][2] != self.bcolor:
                border = colorTable[0][self.bcolor]
                pygame.draw.line(self, border, (0, screenY), (59, screenY))
                pygame.draw.line(self, border, (316, screenY), (375, screenY))
                self.screenCache[screenY][2] = self.bcolor
            x = 60
            for _ in range(32):
                attr = self.unFlash[self.flashReversed][mem.screen(adr_attributs)]
                m = mem.screen(adr_pattern)
                cc = self.screenCache[adr_pattern]
                if (cc[0] != m) or (cc[1] != attr):
                    cc[0] = m
                    cc[1] = attr
                    ink, paper = self.decodecolor(attr)
                    b = 0b10000000
                    while b:
                        if (m & b):
                            self.set_at((x, screenY), ink)
                        else:
                            self.set_at((x, screenY), paper)
                        x += 1
                        b >>= 1
                else:
                    x += 8
                adr_pattern += 1
                adr_attributs += 1

    def renderscreenFull(self, mem):
        for y in range(len(self.screenCache)):
            cc = self.screenCache[y]
            for n in range(len(cc)): cc[n] = -1
        for y in range(312): self.renderline(y, mem)


class Z80(io.Interruptable):
    def __init__(self):
        self.registers = registers.Registers()
        self.instructions = instructions.InstructionSet(self.registers)
        self._memory = io.ZXmem
        io.ZXports = io.IOMap()
        io.ZXports.addDevice(portFE())
        io.ZXports.addDevice(io.portFD())
        self._iomap = io.ZXports
        self._interrupted = False

    def interrupt(self):
        self._interrupted = True

    def step_instruction(self, cicles):
        while cicles > 0:
            ins = False
            pc = dict(self.registers)["PC"]

            if self._interrupted and self.registers.IFF:
                self._interrupted = False
                if self.registers.HALT:
                    self.registers.HALT = False
                    self.registers.PC = util.inc16(pc)
                if self.registers.IM == 2:
                    imadr = (self.registers.I << 8) | 0xFF
                    ins, args = self.instructions << 0xCD
                    ins, args = self.instructions << self._memory[imadr & 0xFFFF]
                    ins, args = self.instructions << self._memory[(imadr + 1) & 0xFFFF]
                else:
                    ins, args = self.instructions << 0xFF
            else:
                while not ins:
                    ins, args = self.instructions << self._memory[pc]
                    self.registers.PC = pc = (pc + 1) & 0xFFFF
                # print( "{0:X} : {1} ".format(pc, ins.assembler(args)))
                # with open("sortida.txt", 'a') as file1: file1.write("{0:04X} : {1}\n".format(pc, ins.assembler(args)))

            ins.execute(args)

            cicles -= ins.tstates
        return cicles


class portFE(io.IO):

    _addresses = [0xFE] # TODO: investigate

    _keysSpectrum = { # http://www.breakintoprogram.co.uk/hardware/computers/zx-spectrum/keyboard
        0x7F: 0b10111111, 0xBF: 0b10111111, 0xDF: 0b10111111, 0xEF: 0b10111111,
        0xF7: 0b10111111, 0xFB: 0b10111111, 0xFD: 0b10111111, 0xFE: 0b10111111
    }

    _pygameKeys = { # scancode
        30: [[0xF7, 0x01]], 31: [[0xF7, 0x02]], 32: [[0xF7, 0x04]], 33: [[0xF7, 0x08]], 34: [[0xF7, 0x10]], # 12345
        35: [[0xEF, 0x10]], 36: [[0xEF, 0x08]], 37: [[0xEF, 0x04]], 38: [[0xEF, 0x02]], 39: [[0xEF, 0x01]], # 67890
        20: [[0xFB, 0x01]], 26: [[0xFB, 0x02]], 8: [[0xFB, 0x04]], 21: [[0xFB, 0x08]], 23: [[0xFB, 0x10]], # qwert
        28: [[0xDF, 0x10]], 24: [[0xDF, 0x08]], 12: [[0xDF, 0x04]], 18: [[0xDF, 0x02]], 19: [[0xDF, 0x01]], # yuiop
        4: [[0xFD, 0x01]], 22: [[0xFD, 0x02]], 7: [[0xFD, 0x04]], 9: [[0xFD, 0x08]], 10: [[0xFD, 0x10]], # asdfg
        11: [[0xBF, 0x10]], 13: [[0xBF, 0x08]], 14: [[0xBF, 0x04]], 15: [[0xBF, 0x02]], # hjkl
        29: [[0xFE, 0x02]], 27: [[0xFE, 0x04]], 6: [[0xFE, 0x08]], 25: [[0xFE, 0x10]], # zxcv
        5: [[0x7F, 0x10]], 17: [[0x7F, 0x08]], 16: [[0x7F, 0x04]],  # bnm
        40: [[0xBF, 0x01]], # Enter
        44: [[0x7F, 0x01]], # Space
        226: [[0x7F, 0x02]], 224: [[0x7F, 0x02]], 228: [[0x7F, 0x02]],# Sym (Alt, LCtrl, RCtrl)
        225: [[0xFE, 0x01]], 229: [[0xFE, 0x01]], # Shift (LShift, RShift)
        # Tecles combinades
        42: [[0xFE, 0x01], [0xEF, 0x01]], # Backspace
        80: [[0xFE, 0x01], [0xF7, 0x10]], # Cursor LEFT
        81: [[0xFE, 0x01], [0xEF, 0x10]], # Cursor DOWN
        82: [[0xFE, 0x01], [0xEF, 0x08]], # Cursor UP
        79: [[0xFE, 0x01], [0xEF, 0x04]], # Cursor RIGHT
        54: [[0x7F, 0x02], [0x7F, 0x08]], # Coma
        55: [[0x7F, 0x02], [0x7F, 0x04]], # Punt
        # Sinclair Interface II
        92: [[0xEF, 0x10]], 94: [[0xEF, 0x08]], 90: [[0xEF, 0x04]], 93: [[0xEF, 0x04]], 96: [[0xEF, 0x02]], 98: [[0xEF, 0x01]] # (teclat numèric)
    }

    def __init__(self):
        self.nborder = None
        # audioword = 0x0000
        self.audioword = None

    def keypress(self, scancode):
        if scancode in self._pygameKeys:
            k = self._pygameKeys[scancode]
            for par in k:
                self._keysSpectrum[par[0]] = self._keysSpectrum[par[0]] & (par[1]^0xFF)

    def keyrelease(self, scancode):
        if scancode in self._pygameKeys:
            k = self._pygameKeys[scancode]
            for par in k:
                self._keysSpectrum[par[0]] = self._keysSpectrum[par[0]] | par[1]

    def read(self, address):
        adr = address >> 8
        res = 0xBF
        b = 0x80
        while b:
            if (adr & b) == 0:
                res &= self._keysSpectrum[b ^ 0xFF]
            b >>= 1
        return res

    def write(self, address, value):
        # Bit   7   6   5   4   3   2   1   0
        #  +-------------------------------+
        #  |   |   |   | E | M |   Border  |
        #  +-------------------------------+

        # print((i[1] & 0b00010000) >> 4) #filtrem el bit de audio output per generar el so
        # cal cridar la funció que toca per el so

        # new values out volume
        if (value & 0b00011000) == 24:
            self.audioword = 29569
        elif (value & 0b00010000) == 16:
            self.audioword = 28445
        elif (value & 0b00001000) == 8:
            self.audioword = 3113
        elif (value & 0b00000000) == 0:
            self.audioword = 0

        # gestió del color del borde
        #main_screen.set_bcolor(value & 0b00000111)
