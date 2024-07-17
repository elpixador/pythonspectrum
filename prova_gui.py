import pygame, sys, os, threading, platform
from tkinter import *
from tkinter import filedialog, messagebox
from time import sleep, time

## Z80 CPU Emulator / https://github.com/cburbridge/z80
from z80 import util, io, registers, instructions

# variables, estructures i coses
mem = bytearray(65536)
colorTable = (  # https://en.wikipedia.org/wiki/ZX_Spectrum_graphic_modes#Colour_palette
    (
        0x000000,
        0x0100CE,
        0xCF0100,
        0xCF01CE,
        0x00CF15,
        0x01CFCF,
        0xCFCF15,
        0xCFCFCF,
    ),  # bright 0
    (
        0x000000,
        0x0200FD,
        0xFF0201,
        0xFF02FD,
        0x00FF1C,
        0x02FFFF,
        0xFFFF1D,
        0xFFFFFF,
    ),  # bright 1
)
flashReversed = False
pantalla = None
tilechanged = [True] * 768
keysSpectrum = {
   0x7FFE: 0b10111111, 0xBFFE: 0b10111111, 0xDFFE: 0b10111111, 0xEFFE: 0b10111111,
   0xF7FE: 0b10111111, 0xFBFE: 0b10111111, 0xFDFE: 0b10111111, 0xFEFE: 0b10111111
}
running = True
ROM = "jocs/spectrum.rom"


# classes
class Z80(io.Interruptable):
    def __init__(self):
        self.registers = registers.Registers()
        self.instructions = instructions.InstructionSet(self.registers)
        self._memory = mem
        self._iomap = io.IOMap()
        self._interrupted = False

    def interrupt(self):
        self._interrupted = True

    def step_instruction(self):
        ins, args = False, []
        pc = self.registers.PC

        if self._interrupted and self.registers.IFF:
            self._interrupted = False
            if self.registers.HALT == 1:
                self.registers.HALT = 2  # 0=normal, 1=waiting, 2=interrupted
            if self.registers.IM == 1:
                # print ("!!! Interrupt Mode 1 !!!")
                ins, args = self.instructions << 0xCD
                ins, args = self.instructions << 0x38
                ins, args = self.instructions << 0x00
            elif self.registers.IM == 2:
                # print ("!!! Interrupt Mode 2 !!!")
                imadr = (self.registers.I << 8) | 0xFF
                ins, args = self.instructions << 0xCD
                ins, args = self.instructions << self._memory[imadr & 0xFFFF]
                ins, args = self.instructions << self._memory[(imadr + 1) & 0xFFFF]
        else:
            while not ins:
                ins, args = self.instructions << self._memory[self.registers.PC]
                self.registers.PC = util.inc16(self.registers.PC)
            #print("{0:X} : {1} ".format(pc, ins.assembler(args)))

        rd = ins.get_read_list(args)
        data = [0] * len(rd)
        for n, i in enumerate(rd):
            if i < 0x10000:
                data[n] = self._memory[i]
            else:
                address = i & 0xFFFF
                if address in keysSpectrum:
                    data[n] = keysSpectrum[address]
                else:
                    data[n] = 0xFF

        wrt = ins.execute(data, args)
        for i in wrt:
            adr = i[0]
            if adr > 0x10000:
                address = adr & 0xFF
                # iomap.address[address].write.emit(address, i[1])
                ##self._iomap.address[address].write(address, i[1])
                # print (chr(i[1]))
            else:
                if adr > 16383:  # Només escrivim a la RAM
                    # Caché per a renderscreenDiff
                    if (adr < 23296) & (
                        self._memory[adr] != i[1]
                    ):  # És pantalla i ha canviat?
                        if adr < 22528:  # Patrons o atributs?
                            tilechanged[
                                ((adr & 0b0001100000000000) >> 3) | adr & 0b11111111
                            ] = True
                        else:
                            tilechanged[adr & 0b0000001111111111] = True
                    # Escrivim
                    self._memory[adr] = i[1]

        return ins, args


# global procedures
def stop_running():  # signals the end of the program
    global running
    running = False


def quit_app():
    root.destroy()
    pygame.quit()
    sys.exit()


def readROM():
    f = open(ROM, mode="rb")
    dir = 0
    data = f.read(1)
    while data:
        mem[dir] = int.from_bytes(data, byteorder="big", signed=False)
        dir = dir + 1
        data = f.read(1)
    f.close()
    print("ROM cargada")

def byteFromFile(aFile):
    data = aFile.read(1)
    return int.from_bytes(data, byteorder="big", signed=False)


def readSpectrumFile():
    fichero = filedialog.askopenfile(
        title="Obrir arxiu",
        filetypes=(
            ("Arxius .SNA", "*.SNA"),
            ("Arxius .SP", "*.SP"),
            ("Arxius .Z80", "*.Z80"),
            ("Tots", "*"),
        ),
    )

    if fichero:
        print("el fichero es " + str(fichero.name))
        nom, extensio = os.path.splitext(fichero.name)

        f = open(fichero.name, mode="rb")

        # no se puede utilizar match sino es python >3.10

        if (
            extensio.upper() == ".Z80"
        ):  # https://worldofspectrum.org/faq/reference/z80format.htm
            data = f.read(30)  # lee los registros del procesador
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
            mach.registers.IFF = b & 1
            mach.registers.IFF2 = (b >> 2) & 1
            mach.registers.R = byteFromFile(f)
            mach.registers.F = byteFromFile(f)
            mach.registers.A = byteFromFile(f)
            mach.registers.SP = byteFromFile(f) | (byteFromFile(f) << 8)
            mach.registers.IM = byteFromFile(f) & 0x03
            byteFromFile(f)  # Bordercolor

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
            byteFromFile(f)  # Border color
            byteFromFile(f)  # reserved
            b = byteFromFile(f)  # status word low
            mach.registers.IFF = b & 1
            mach.registers.IFF2 = (b >> 2) & 1
            if (b & 0b00001000) == 0:
                mach.registers.IM = ((b & 0b00000010) >> 1) + 1
            else:
                mach.registers.IM = 0
            byteFromFile(f)  # status word high

        # carga el fichero restante a partir de la memoria de pantalla
        dir = 16384
        data = f.read(1)
        while data:
            mem[dir] = int.from_bytes(data, byteorder="big", signed=False)
            dir = dir + 1
            data = f.read(1)
        f.close()

        if extensio.upper() == ".SNA":
            mach.registers.PC = (
                mach._memory[mach.registers.SP]
                | (mach._memory[mach.registers.SP + 1]) << 8
            )
            mach.registers.SP += 2

    else:
        print("cancelada carga / ejecutamos ROM")
        mach.registers.reset()

    renderscreenFull()


def decodecolor(atribut):
    # http://www.breakintoprogram.co.uk/hardware/computers/zx-spectrum/screen-memory-layout
    bright = (atribut & 0b01000000) >> 6
    flash = (atribut & 0b10000000) >> 7

    tinta = colorTable[bright][atribut & 0b00000111]
    paper = colorTable[bright][(atribut & 0b00111000) >> 3]

    if flash & flashReversed:
        return (paper, tinta)
    else:
        return (tinta, paper)


def renderline(y, adr_pattern):
    adr_attributs = 22528 + ((y >> 3) * 32)
    x = 0
    for col in range(32):
        ink, paper = decodecolor(mem[adr_attributs])
        b = 0b10000000
        while b > 0:
            if (mem[adr_pattern] & b) == 0:
                pantalla.set_at((x, y), paper)
            else:
                pantalla.set_at((x, y), ink)
            x = x + 1
            b = b >> 1
        adr_pattern = adr_pattern + 1
        adr_attributs = adr_attributs + 1


def renderscreenFull():
    dir = 16384
    for y in range(192):
        # 000 tt zzz yyy xxxxx
        offset = ((y & 0b11000000) | ((y & 0b111) << 3) | (y & 0b111000) >> 3) << 5
        renderline(y, dir + offset)


def renderscreenDiff():
    for p in range(0, 768):
        if tilechanged[p] == True:
            ink, paper = decodecolor(mem[22528 + p])
            # 000 tt zzz yyy xxxxx
            adr_pattern = 16384 + ((p & 0b0000001100000000) << 3) + (p & 0b11111111)
            y = (p >> 5) * 8
            for offset in range(0, 2048, 256):
                x = (p & 0b00011111) * 8
                b = 0b10000000
                while b > 0:
                    if (mem[adr_pattern + offset] & b) == 0:
                        pantalla.set_at((x, y), paper)
                    else:
                        pantalla.set_at((x, y), ink)
                    b >>= 1
                    x += 1
                y += 1
            tilechanged[p] = False


def worker():
    t = time()
    cicles = 70908

    while running == True:
        # t = time()
        ins, args = mach.step_instruction()
        cicles -= ins.tstates
        if cicles < 0:
            cicles += 70908
            mach.interrupt()
    raise Exception("Emulator Quitting...")


# init gui and pygame windows/screens
def init_tk():
    menubar = Menu(root)
    filemenu = Menu(menubar, tearoff=0)
    filemenu.add_command(label="Open File...", command=readSpectrumFile)
    filemenu.add_command(label="Quit", command=stop_running)
    menubar.add_cascade(label="File", menu=filemenu)
    root.config(menu=menubar)
    global embed
    embed = Frame(root, width=WIDTH * SCALE, height=HEIGHT * SCALE)
    embed.pack()
    root.protocol("WM_DELETE_WINDOW", stop_running)
    root.update()


def init_pygame():
    pygame.init()
    # Tell pygame to use the tk window we created as a display
    system = platform.system()
    if system == "Windows":
        os.environ["SDL_VIDEODRIVER"] = "windib"
    elif system == "Linux":
        os.environ["SDL_VIDEODRIVER"] = "x11"
    else:
        os.environ["SDL_VIDEODRIVER"] = "cocoa"
    os.environ["SDL_WINDOWID"] = str(embed.winfo_id())
    pygame.display.init()
    global pantalla
    pantalla = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED, vsync=1)
    pygame.display.set_caption("Hello from Spectrum World")
    pygame.display.flip()


# INICI
WIDTH = 256
HEIGHT = 192
SCALE = 3

mach = Z80()

root = Tk()
init_tk()
init_pygame()

readROM()
renderscreenFull()
thread = threading.Thread(target=worker, daemon=True)
thread.start()

clock = pygame.time.Clock()
clock.tick(50)

conta = 0

while True:
    if running:
        conta = conta + 1
        if (conta & 0b00011111) == 0:
            flashReversed = not flashReversed
            for p in range(0, 768):
                if (mem[22528 + p] & 0b10000000) != 0:
                    tilechanged[p] = True

        renderscreenDiff()
        pygame.display.flip()
        root.update()
    else:  # sortim del programa (ordenadament)
        quit_app()
