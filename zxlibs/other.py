import pygame
import os, sys

#
## Z80 CPU Emulator
# This is a Zilog Z80 CPU emulator, written in Python.
# https://github.com/cburbridge/z80
### Missing and todo
# - Most undocumented opcodes
# - Undocumented flags for `CPI` and `CPIR`.
from z80 import util, io, registers, instructions


# Funcions
def quit_app():
    print("Emulator quitting...")
    pygame.quit()
    sys.exit()


# tractament d'arxius

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


def readSpectrumFile(spectrum, fichero):
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
            spectrum.cpu.registers.A = byteFromFile(f)
            spectrum.cpu.registers.F = byteFromFile(f)
            spectrum.cpu.registers.C = byteFromFile(f)
            spectrum.cpu.registers.B = byteFromFile(f)
            spectrum.cpu.registers.L = byteFromFile(f)
            spectrum.cpu.registers.H = byteFromFile(f)
            spectrum.cpu.registers.PC = byteFromFile(f) | (byteFromFile(f) << 8)
            spectrum.cpu.registers.SP = byteFromFile(f) | (byteFromFile(f) << 8)
            spectrum.cpu.registers.I = byteFromFile(f)
            spectrum.cpu.registers.R = byteFromFile(f) & 0x7F
            b = byteFromFile(f)  # Bordercolor etc
            nborder = (b & 0b00001110) > 1

            spectrum.cpu.registers.R = spectrum.cpu.registers.R | ((b & 0x01) << 7)
            isPacked = (b & 0b00100000) >> 5
            spectrum.cpu.registers.E = byteFromFile(f)
            spectrum.cpu.registers.D = byteFromFile(f)
            spectrum.cpu.registers.C_ = byteFromFile(f)
            spectrum.cpu.registers.B_ = byteFromFile(f)
            spectrum.cpu.registers.D_ = byteFromFile(f)
            spectrum.cpu.registers.E_ = byteFromFile(f)
            spectrum.cpu.registers.L_ = byteFromFile(f)
            spectrum.cpu.registers.H_ = byteFromFile(f)
            spectrum.cpu.registers.A_ = byteFromFile(f)
            spectrum.cpu.registers.F_ = byteFromFile(f)
            spectrum.cpu.registers.IY = byteFromFile(f) | (byteFromFile(f) << 8)
            spectrum.cpu.registers.IX = byteFromFile(f) | (byteFromFile(f) << 8)
            spectrum.cpu.registers.IFF = byteFromFile(f)
            spectrum.cpu.registers.IFF2 = byteFromFile(f)
            spectrum.cpu.registers.IM = byteFromFile(f) & 0x03
            if spectrum.cpu.registers.PC == 0:  # Versions 2 i 3 del format
                b = byteFromFile(f) | (byteFromFile(f) << 8)
                spectrum.cpu.registers.PC = byteFromFile(f) | (
                    byteFromFile(f) << 8
                )
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
            spectrum.cpu.registers.I = byteFromFile(f)
            spectrum.cpu.registers.L_ = byteFromFile(f)
            spectrum.cpu.registers.H_ = byteFromFile(f)
            spectrum.cpu.registers.E_ = byteFromFile(f)
            spectrum.cpu.registers.D_ = byteFromFile(f)
            spectrum.cpu.registers.C_ = byteFromFile(f)
            spectrum.cpu.registers.B_ = byteFromFile(f)
            spectrum.cpu.registers.F_ = byteFromFile(f)
            spectrum.cpu.registers.A_ = byteFromFile(f)
            spectrum.cpu.registers.L = byteFromFile(f)
            spectrum.cpu.registers.H = byteFromFile(f)
            spectrum.cpu.registers.E = byteFromFile(f)
            spectrum.cpu.registers.D = byteFromFile(f)
            spectrum.cpu.registers.C = byteFromFile(f)
            spectrum.cpu.registers.B = byteFromFile(f)
            spectrum.cpu.registers.IY = byteFromFile(f) | (byteFromFile(f) << 8)
            spectrum.cpu.registers.IX = byteFromFile(f) | (byteFromFile(f) << 8)
            b = byteFromFile(f)
            spectrum.cpu.registers.IFF = (b >> 2) & 1
            spectrum.cpu.registers.IFF2 = (b >> 2) & 1
            spectrum.cpu.registers.R = byteFromFile(f)
            spectrum.cpu.registers.F = byteFromFile(f)
            spectrum.cpu.registers.A = byteFromFile(f)
            spectrum.cpu.registers.SP = byteFromFile(f) | (byteFromFile(f) << 8)
            spectrum.cpu.registers.IM = byteFromFile(f) & 0x03
            nborder = byteFromFile(f)  # Bordercolor

            memFromFile(f)
            f.close()
            spectrum.cpu.registers.PC = (
                spectrum.cpu._memory[spectrum.cpu.registers.SP]
                | (spectrum.cpu._memory[spectrum.cpu.registers.SP + 1]) << 8
            )
            spectrum.cpu.registers.SP += 2

        elif (
            extensio.upper() == ".SP"
        ):  # https://rk.nvg.ntnu.no/sinclair/faq/fileform.html#SP
            f.read(6)  # signatura i cacones
            spectrum.cpu.registers.C = byteFromFile(f)
            spectrum.cpu.registers.B = byteFromFile(f)
            spectrum.cpu.registers.E = byteFromFile(f)
            spectrum.cpu.registers.D = byteFromFile(f)
            spectrum.cpu.registers.L = byteFromFile(f)
            spectrum.cpu.registers.H = byteFromFile(f)
            spectrum.cpu.registers.F = byteFromFile(f)
            spectrum.cpu.registers.A = byteFromFile(f)
            spectrum.cpu.registers.IX = byteFromFile(f) | (byteFromFile(f) << 8)
            spectrum.cpu.registers.IY = byteFromFile(f) | (byteFromFile(f) << 8)
            spectrum.cpu.registers.C_ = byteFromFile(f)
            spectrum.cpu.registers.B_ = byteFromFile(f)
            spectrum.cpu.registers.E_ = byteFromFile(f)
            spectrum.cpu.registers.D_ = byteFromFile(f)
            spectrum.cpu.registers.L_ = byteFromFile(f)
            spectrum.cpu.registers.H_ = byteFromFile(f)
            spectrum.cpu.registers.F_ = byteFromFile(f)
            spectrum.cpu.registers.A_ = byteFromFile(f)
            spectrum.cpu.registers.R = byteFromFile(f)
            spectrum.cpu.registers.I = byteFromFile(f)
            spectrum.cpu.registers.SP = byteFromFile(f) | (byteFromFile(f) << 8)
            spectrum.cpu.registers.PC = byteFromFile(f) | (byteFromFile(f) << 8)
            byteFromFile(f)  # reserved
            byteFromFile(f)  # reserved
            nborder = byteFromFile(f)  # Bordercolor

            byteFromFile(f)  # reserved
            b = byteFromFile(f)  # status word low
            spectrum.cpu.registers.IFF = b & 1
            spectrum.cpu.registers.IFF2 = (b >> 2) & 1
            if (b & 0b00001000) == 0:
                spectrum.cpu.registers.IM = ((b & 0b00000010) >> 1) + 1
            else:
                spectrum.cpu.registers.IM = 0
            byteFromFile(f)  # status word high
            memFromFile(f)
            f.close()

    renderscreenFull()
