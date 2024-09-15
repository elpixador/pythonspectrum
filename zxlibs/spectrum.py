import pygame
# PyGame_GUI https://pygame-gui.readthedocs.io/en/latest/quick_start.html
from .constants import ZX_RES, APPNAME, APPVERSION, rompath, romfile
from .sound import AudioInterface
## Z80 CPU Emulator / https://github.com/cburbridge/z80
from z80 import util, io, registers, instructions
from .other import *

class Spectrum:
    def __init__(self):
        self.plusmode = True # True = Spectrum 128 / False = ZX Spectrum 48k  
        self.screen = ZXScreen((ZX_RES[0], ZX_RES[1]))
        self.audio = AudioInterface()  # this is where the audio stuff will happen
        self.memory = io.mem()
        self.IO = io.IO()  # TODO:
        self.cpu = Z80()
        self.flashCount = 0
        self.flashReversed = False
        self.cicles = 0
        self.is_running = True

    # Load ROM
    def readROM(self, zxromfile=romfile):
        # If no romfile is provided, use the default (48k)
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
            self.memory.writeROM(dir, int.from_bytes(data, byteorder='big', signed=False))
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

            renderline(y)
            # self.screen.renderline(y)

        self.cpu.interrupt()


class ZXScreen(pygame.Surface):
    def __new__(cls, size):
        # creates a new pygame.Surface object
        return super(ZXScreen, cls).__new__(cls)

    def __init__(self, size):
        super().__init__(size)
        self.screenCache = []
        for i in range(6144):
            self.screenCache.append([-1, -1, -1, -1])  # attr, ink, paper, border
        self.flashReversed = False


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
