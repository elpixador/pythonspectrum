import pygame
import sys

#
## Z80 CPU Emulator
# This is a Zilog Z80 CPU emulator, written in Python.
# https://github.com/cburbridge/z80
### Missing and todo
# - Most undocumented opcodes
# - Undocumented flags for `CPI` and `CPIR`.
from z80 import util, io, registers, instructions


class portFE(io.IO):
    _addresses = [0xFE]

    _keysSpectrum = (
        {  # http://www.breakintoprogram.co.uk/hardware/computers/zx-spectrum/keyboard
            0x7F: 0b10111111,
            0xBF: 0b10111111,
            0xDF: 0b10111111,
            0xEF: 0b10111111,
            0xF7: 0b10111111,
            0xFB: 0b10111111,
            0xFD: 0b10111111,
            0xFE: 0b10111111,
        }
    )

    _pygameKeys = {  # scancode
        30: [0xF7, 0x01],
        31: [0xF7, 0x02],
        32: [0xF7, 0x04],
        33: [0xF7, 0x08],
        34: [0xF7, 0x10],  # 12345
        35: [0xEF, 0x10],
        36: [0xEF, 0x08],
        37: [0xEF, 0x04],
        38: [0xEF, 0x02],
        39: [0xEF, 0x01],  # 67890
        20: [0xFB, 0x01],
        26: [0xFB, 0x02],
        8: [0xFB, 0x04],
        21: [0xFB, 0x08],
        23: [0xFB, 0x10],  # qwert
        28: [0xDF, 0x10],
        24: [0xDF, 0x08],
        12: [0xDF, 0x04],
        18: [0xDF, 0x02],
        19: [0xDF, 0x01],  # yuiop
        4: [0xFD, 0x01],
        22: [0xFD, 0x02],
        7: [0xFD, 0x04],
        9: [0xFD, 0x08],
        10: [0xFD, 0x10],  # asdfg
        11: [0xBF, 0x10],
        13: [0xBF, 0x08],
        14: [0xBF, 0x04],
        15: [0xBF, 0x02],  # hjkl
        29: [0xFE, 0x02],
        27: [0xFE, 0x04],
        6: [0xFE, 0x08],
        25: [0xFE, 0x10],  # zxcv
        5: [0x7F, 0x10],
        17: [0x7F, 0x08],
        16: [0x7F, 0x04],  # bnm
        40: [0xBF, 0x01],  # Enter
        44: [0x7F, 0x01],  # Space
        226: [0x7F, 0x02],  # Sym (Alt)
        225: [0xFE, 0x01],
        229: [0xFE, 0x01],  # Shift (LShift, RShift)
        80: [0xEF, 0x10],
        79: [0xEF, 0x08],
        81: [0xEF, 0x04],
        82: [0xEF, 0x02],
        228: [0xEF, 0x01],  # Sinclair Interface II (Cursors, RCtrl)
    }

    def keypress(self, scancode):
        if scancode in self._pygameKeys:
            k = self._pygameKeys[scancode]
            self._keysSpectrum[k[0]] = self._keysSpectrum[k[0]] & (k[1] ^ 0xFF)

    def keyrelease(self, scancode):
        if scancode in self._pygameKeys:
            k = self._pygameKeys[scancode]
            self._keysSpectrum[k[0]] = self._keysSpectrum[k[0]] | k[1]

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

        # audioword = 0x0000
        global nborder, audioword

        # new values out volume
        if (value & 0b00011000) == 24:
            audioword = 29569
        elif (value & 0b00010000) == 16:
            audioword = 28445
        elif (value & 0b00001000) == 8:
            audioword = 3113
        elif (value & 0b00000000) == 0:
            audioword = 0

        # gestió del color del borde
        main_screen.set_bcolor(value & 0b00000111)


class Z80(io.Interruptable):
    def __init__(self):
        self.registers = registers.Registers()
        self.instructions = instructions.InstructionSet(self.registers)
        self._memory = io.ZXmem
        io.ZXports = io.IOMap()
        io.ZXports.addDevice(portFE())
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
                    ins, args = self.instructions << self._memory[(imadr+1) & 0xFFFF]
                else:
                    ins, args = self.instructions << 0xFF
            else:
                while not ins:
                    ins, args = self.instructions << self._memory[pc]
                    self.registers.PC = pc = (pc + 1) & 0xFFFF
                #print( "{0:X} : {1} ".format(pc, ins.assembler(args)))
                #with open("sortida.txt", 'a') as file1: file1.write("{0:04X} : {1}\n".format(pc, ins.assembler(args)))
        
            ins.execute(args)

            cicles -= ins.tstates
        return cicles


# Funcions
def quit_app():
    print("Emulator quitting...")
    pygame.quit()
    sys.exit()


#tractament d'arxius
def readROM(aFilename):
   f = open(aFilename, mode="rb")
   dir = 0
   data = f.read(1)
   while (data):
      io.ZXmem.writeROM(dir, int.from_bytes(data, byteorder='big', signed=False))
      dir = dir + 1
      data = f.read(1)
   f.close()
   print("ROM cargada")

def readROM1(aFilename):
   f = open(aFilename, mode="rb")
   dir = 0
   data = f.read(1)
   while (data):
      io.ZXmem.writeROM1(dir, int.from_bytes(data, byteorder='big', signed=False))
      dir = dir + 1
      data = f.read(1)
   f.close()
   print("ROM cargada")

def byteFromFile(aFile):
    data = aFile.read(1)
    return int.from_bytes(data, byteorder="big", signed=False)


def memFromFile(aFile):
    dir = 16384
    data = aFile.read(1)
    while data:
        io.ZXmem[dir] = int.from_bytes(data, byteorder="big", signed=False)
        dir = dir + 1
        data = aFile.read(1)


def memFromPackedFile(aFile, aInici, aLongitud):
    dir = aInici
    old = 0
    while aLongitud > 0:
        bb = byteFromFile(aFile)
        aLongitud -= 1
        if (old == 0xED) & (bb == 0xED):
            dir -= 1
            cops = byteFromFile(aFile)
            if cops == 0:
                break
            bb = byteFromFile(aFile)
            for i in range(cops):
                if dir <= 0xFFFF:
                    io.ZXmem[dir] = bb
                dir += 1
            aLongitud -= 2
            old = 0
        else:
            if dir <= 0xFFFF:
                io.ZXmem[dir] = bb
            old = bb
            dir += 1


def readSpectrumFile(fichero):
    global nborder
    if fichero:

        extensio = os.path.splitext(fichero)[1]
        nom = os.path.basename(fichero)
        print("file to load is: " + nom)

        f = open(fichero, mode="rb")

        # no se puede utilizar match sino es python >3.10

        if (
            extensio.upper() == ".Z80"
        ):  # https://worldofspectrum.org/faq/reference/z80format.htm
            f.seek(0, 2)
            sz = f.tell()
            f.seek(0, 0)
            mach.registers.A = byteFromFile(f)
            mach.registers.F = byteFromFile(f)
            mach.registers.C = byteFromFile(f)
            mach.registers.B = byteFromFile(f)
            mach.registers.L = byteFromFile(f)
            mach.registers.H = byteFromFile(f)
            mach.registers.PC = byteFromFile(f) | (byteFromFile(f) << 8)
            mach.registers.SP = byteFromFile(f) | (byteFromFile(f) << 8)
            mach.registers.I = byteFromFile(f)
            mach.registers.R = byteFromFile(f) & 0x7F
            b = byteFromFile(f)  # Bordercolor etc
            nborder = (b & 0b00001110) > 1

            mach.registers.R = mach.registers.R | ((b & 0x01) << 7)
            isPacked = (b & 0b00100000) >> 5
            mach.registers.E = byteFromFile(f)
            mach.registers.D = byteFromFile(f)
            mach.registers.C_ = byteFromFile(f)
            mach.registers.B_ = byteFromFile(f)
            mach.registers.E_ = byteFromFile(f)
            mach.registers.D_ = byteFromFile(f)
            mach.registers.L_ = byteFromFile(f)
            mach.registers.H_ = byteFromFile(f)
            mach.registers.A_ = byteFromFile(f)
            mach.registers.F_ = byteFromFile(f)
            mach.registers.IY = byteFromFile(f) | (byteFromFile(f) << 8)
            mach.registers.IX = byteFromFile(f) | (byteFromFile(f) << 8)
            mach.registers.IFF = byteFromFile(f)
            mach.registers.IFF2 = byteFromFile(f)
            mach.registers.IM = byteFromFile(f) & 0x03
            if mach.registers.PC == 0:  # Versions 2 i 3 del format
                b = byteFromFile(f) | (byteFromFile(f) << 8)
                mach.registers.PC = byteFromFile(f) | (byteFromFile(f) << 8)
                print("Hardware mode: " + str(byteFromFile(f)))
                f.read(b - 3)  # Skip b-3 bytes
                while sz > f.tell():
                    lon = byteFromFile(f) | (
                        byteFromFile(f) << 8
                    )  # length of compressed data
                    b = byteFromFile(f)  # page
                    if b == 4:
                        memFromPackedFile(f, 0x8000, lon)
                    elif b == 5:
                        memFromPackedFile(f, 0xC000, lon)
                    elif b == 8:
                        memFromPackedFile(f, 0x4000, lon)
                    else:
                        print("Skipping page: " + str(b))
                        memFromPackedFile(f, 0xFFFFF, lon)
            else:  # Versió 1 del format
                if isPacked:
                    memFromPackedFile(f, 16384, 49152)
                else:
                    memFromFile(f)
            f.close()

        elif (
            extensio.upper() == ".SNA"
        ):  # https://worldofspectrum.org/faq/reference/formats.htm
            mach.registers.I = byteFromFile(f)
            mach.registers.L_ = byteFromFile(f)
            mach.registers.H_ = byteFromFile(f)
            mach.registers.E_ = byteFromFile(f)
            mach.registers.D_ = byteFromFile(f)
            mach.registers.C_ = byteFromFile(f)
            mach.registers.B_ = byteFromFile(f)
            mach.registers.F_ = byteFromFile(f)
            mach.registers.A_ = byteFromFile(f)
            mach.registers.L = byteFromFile(f)
            mach.registers.H = byteFromFile(f)
            mach.registers.E = byteFromFile(f)
            mach.registers.D = byteFromFile(f)
            mach.registers.C = byteFromFile(f)
            mach.registers.B = byteFromFile(f)
            mach.registers.IY = byteFromFile(f) | (byteFromFile(f) << 8)
            mach.registers.IX = byteFromFile(f) | (byteFromFile(f) << 8)
            b = byteFromFile(f)
            mach.registers.IFF = (b >> 2) & 1
            mach.registers.IFF2 = (b >> 2) & 1
            mach.registers.R = byteFromFile(f)
            mach.registers.F = byteFromFile(f)
            mach.registers.A = byteFromFile(f)
            mach.registers.SP = byteFromFile(f) | (byteFromFile(f) << 8)
            mach.registers.IM = byteFromFile(f) & 0x03
            nborder = byteFromFile(f)  # Bordercolor

            memFromFile(f)
            f.close()
            mach.registers.PC = (
                mach._memory[mach.registers.SP]
                | (mach._memory[mach.registers.SP + 1]) << 8
            )
            mach.registers.SP += 2

        elif (
            extensio.upper() == ".SP"
        ):  # https://rk.nvg.ntnu.no/sinclair/faq/fileform.html#SP
            f.read(6)  # signatura i cacones
            mach.registers.C = byteFromFile(f)
            mach.registers.B = byteFromFile(f)
            mach.registers.E = byteFromFile(f)
            mach.registers.D = byteFromFile(f)
            mach.registers.L = byteFromFile(f)
            mach.registers.H = byteFromFile(f)
            mach.registers.F = byteFromFile(f)
            mach.registers.A = byteFromFile(f)
            mach.registers.IX = byteFromFile(f) | (byteFromFile(f) << 8)
            mach.registers.IY = byteFromFile(f) | (byteFromFile(f) << 8)
            mach.registers.C_ = byteFromFile(f)
            mach.registers.B_ = byteFromFile(f)
            mach.registers.E_ = byteFromFile(f)
            mach.registers.D_ = byteFromFile(f)
            mach.registers.L_ = byteFromFile(f)
            mach.registers.H_ = byteFromFile(f)
            mach.registers.F_ = byteFromFile(f)
            mach.registers.A_ = byteFromFile(f)
            mach.registers.R = byteFromFile(f)
            mach.registers.I = byteFromFile(f)
            mach.registers.SP = byteFromFile(f) | (byteFromFile(f) << 8)
            mach.registers.PC = byteFromFile(f) | (byteFromFile(f) << 8)
            byteFromFile(f)  # reserved
            byteFromFile(f)  # reserved
            nborder = byteFromFile(f)  # Bordercolor

            byteFromFile(f)  # reserved
            b = byteFromFile(f)  # status word low
            mach.registers.IFF = b & 1
            mach.registers.IFF2 = (b >> 2) & 1
            if (b & 0b00001000) == 0:
                mach.registers.IM = ((b & 0b00000010) >> 1) + 1
            else:
                mach.registers.IM = 0
            byteFromFile(f)  # status word high
            memFromFile(f)
            f.close()

    renderscreenFull()




def quit_app():
    print("Emulator quitting...")
    pygame.quit()
    sys.exit()
