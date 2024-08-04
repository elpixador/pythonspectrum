from ast import main
import sys, os, threading, platform
import numpy
import pygame
# PyGame_GUI https://pygame-gui.readthedocs.io/en/latest/quick_start.html
import pygame_gui
from pygame_gui.core.utility import create_resource_path

## Z80 CPU Emulator / https://github.com/cburbridge/z80
from z80 import util, io, registers, instructions

# variables, estructures i coses
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
tilechanged = [True] * 768

# classes
class portFE(io.IO):
    _addresses = [0xFE]

    _keysSpectrum = { # http://www.breakintoprogram.co.uk/hardware/computers/zx-spectrum/keyboard
        0x7F: 0b10111111, 0xBF: 0b10111111, 0xDF: 0b10111111, 0xEF: 0b10111111,
        0xF7: 0b10111111, 0xFB: 0b10111111, 0xFD: 0b10111111, 0xFE: 0b10111111
    }

    _pygameKeys = { # scancode
        30: [0xF7, 0x01], 31: [0xF7, 0x02], 32: [0xF7, 0x04], 33: [0xF7, 0x08], 34: [0xF7, 0x10], # 12345
        35: [0xEF, 0x10], 36: [0xEF, 0x08], 37: [0xEF, 0x04], 38: [0xEF, 0x02], 39: [0xEF, 0x01], # 67890
        20: [0xFB, 0x01], 26: [0xFB, 0x02], 8: [0xFB, 0x04], 21: [0xFB, 0x08], 23: [0xFB, 0x10], # qwert
        28: [0xDF, 0x10], 24: [0xDF, 0x08], 12: [0xDF, 0x04], 18: [0xDF, 0x02], 19: [0xDF, 0x01], # yuiop
        4: [0xFD, 0x01], 22: [0xFD, 0x02], 7: [0xFD, 0x04], 9: [0xFD, 0x08], 10: [0xFD, 0x10], # asdfg
        11: [0xBF, 0x10], 13: [0xBF, 0x08], 14: [0xBF, 0x04], 15: [0xBF, 0x02], # hjkl
        29: [0xFE, 0x02], 27: [0xFE, 0x04], 6: [0xFE, 0x08], 25: [0xFE, 0x10], # zxcv
        5: [0x7F, 0x10], 17: [0x7F, 0x08], 16: [0x7F, 0x04],  # bnm
        40: [0xBF, 0x01], # Enter
        44: [0x7F, 0x01], # Space
        226: [0x7F, 0x02], # Sym (Alt)
        225: [0xFE, 0x01], 229: [0xFE, 0x01], # Shift (LShift, RShift)
        80: [0xEF, 0x10], 79: [0xEF, 0x08], 81: [0xEF, 0x04], 82: [0xEF, 0x02], 228: [0xEF, 0x01] # Sinclair Interface II (Cursors, RCtrl)
    }

    def keypress(self, scancode):
        if scancode in self._pygameKeys:
            k = self._pygameKeys[scancode]
            self._keysSpectrum[k[0]] = self._keysSpectrum[k[0]] & (k[1]^0xFF)

    def keyrelease(self, scancode):
        if scancode in self._pygameKeys:
            k = self._pygameKeys[scancode]
            self._keysSpectrum[k[0]] = self._keysSpectrum[k[0]] | k[1]

    def read(self, address):
        adr = address >> 8
        res = 0xBF
        b = 0x80
        while b:
            if ((adr & b) == 0): res &= self._keysSpectrum[b ^ 0xFF]
            b >>= 1
        return res

    def write(self, address, value):
        #Bit   7   6   5   4   3   2   1   0
        #  +-------------------------------+
        #  |   |   |   | E | M |   Border  |
        #  +-------------------------------+

        # print((i[1] & 0b00010000) >> 4) #filtrem el bit de audio output per generar el so
        #cal cridar la funció que toca per el so

        #audioword = 0x0000
        global nborder,  contaudio, bufferlen, bufaudio, audioword

        if((value & 0b00010000) >> 4):
            audioword = 256
        else:
            audioword = 0


        if (contaudio & bufferlen):
            sound = pygame.sndarray.make_sound(bufaudio)
            sound.play()
            contaudio=0
            bufaudio = numpy.zeros((bufferlen, 2), dtype = numpy.int16)
        else:
            bufaudio[contaudio][0] = audioword # left
            bufaudio[contaudio][1] = audioword  # right
            contaudio = contaudio + 1

        #gestio del color del borde
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

            if self._interrupted and self.registers.IFF:
                self._interrupted = False
                if self.registers.HALT:
                    self.registers.HALT = False
                    self.registers.PC = util.inc16(self.registers.PC)
                if self.registers.IM == 1:
                    # print ("!!! Interrupt Mode 1 !!!")
                    #ins, args = self.instructions << 0xCD
                    #ins, args = self.instructions << 0x38
                    #ins, args = self.instructions << 0x00
                    ins, args = self.instructions << 0xFF
                elif self.registers.IM == 2:
                    # print ("!!! Interrupt Mode 2 !!!")
                    imadr = (self.registers.I << 8) | 0xFF
                    ins, args = self.instructions << 0xCD
                    ins, args = self.instructions << self._memory[imadr & 0xFFFF]
                    ins, args = self.instructions << self._memory[(imadr + 1) & 0xFFFF]
            else:
                while not ins:
                    ins, args = self.instructions << self._memory[self.registers.PC]
                    self.registers.PC = (self.registers.PC + 1) & 0xFFFF
                #print("{0:X} : {1} ".format(pc, ins.assembler(args)))

            wrt = ins.execute(args)

            for i in wrt:
                adr = i[0]
                if (adr > 23295): self._memory[adr] = i[1] # RAM normal
                elif ((adr > 16383) and (self._memory[adr] != i[1])): # És pantalla i ha canviat?
                    self._memory[adr] = i[1]
                    if (adr < 22528): # Patrons o atributs?
                        tilechanged[((adr & 0b0001100000000000) >> 3) | adr & 0b11111111] = True
                    else:
                        tilechanged[adr & 0b0000001111111111] = True

            cicles -= ins.tstates

        return cicles

class Worker:
    def __init__(self):
        self.stop_event = threading.Event()
        self.thread = None

    def loop(self):
        cicles = 0
        while not self.stop_event.is_set():
            cicles += 69888
            cicles = mach.step_instruction(cicles)
            mach.interrupt()
    
    def start(self):
        if self.thread is not None and self.thread.is_alive():
            print("Worker is already running")
            return

        self.stop_event.clear()
        self.thread = threading.Thread(target=self.loop, daemon=True) 
        self.thread.start()
        print("Worker started")

    def stop(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join()
        print("Worker stopped")

    def restart(self):
        self.stop()
        self.start()
        print("Worker restarted")

class Screen():
    DEFAULT_SCALE = 3
    MAXSCALE = 5
    UI_HEIGHT = 30

    def __init__(self):
        self.scale = self.DEFAULT_SCALE
        # margin (unscaled)
        self.margin = 40
        # margin (scaled)
        self.smargin = self.get_smargin()
        # dimensions of app window (all scaled: ui, border + internal zx)
        self.dimensions = self.width, self.height = self.update_dimensions()
        # dimensions of internal surface for scaled zx screen 
        self.indimensions = self.inwidth, self.inheight = self.update_indimensions()

        # border color
        self.bcolor = 7 # white, default screen
        # window name
        self.caption = "Pythonspectrum"
        # app icon
        self.icon = "./window.png"
        # placeholders for screen and ui_manager
        self.screen = None
        self.ui_manager = None

        pygame.init()
        # basic initializations
        pygame.display.set_caption(self.caption)
        pygame.display.set_icon(pygame.image.load(self.icon))

        self._init_screen()
        self.init_gui()

    def _init_screen(self):
        # init main screen to fit it all (spectrum, border & gui) 
        self.screen = pygame.display.set_mode(self.dimensions, vsync=0)
        # pintem un fons maco on posarem els botonets
        fons = pygame.image.load('buttonbg.png').convert()
        fons = pygame.transform.scale(fons, (self.width, self.UI_HEIGHT))
        self.screen.blit(fons,(0,0))
    
    def init_gui(self):
        self.ui_manager = pygame_gui.UIManager(self.dimensions)
        buttonWidth = 90
        buttonHeight = self.UI_HEIGHT-4
        numButtons = 3
        gap = 3
        startingPoint = (self.width - ((buttonWidth * numButtons) + (gap * (numButtons - 1)))) / 2
        self.b_load_game = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((startingPoint, 1), (buttonWidth, buttonHeight)), 
            text='Load Game', 
            manager=self.ui_manager)
        self.b_scale_game = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((startingPoint+buttonWidth+gap, 1), (buttonWidth, buttonHeight)), 
            text='Scale: ' + str(self.scale), 
            manager=self.ui_manager)
        self.b_quit_game = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((startingPoint+((buttonWidth+gap)*2), 1), (buttonWidth, buttonHeight)), 
            text='Quit Game', 
            manager=self.ui_manager)

    def draw_screen(self, surface): 
        # only if the border has changed, draw it
        if self.get_hwbcolor() != colorTable[0][self.bcolor]:
            self.draw_border(self.bcolor)
        # draw the standard zx screen onto the scaled one 
        self.screen.blit(pygame.transform.scale(surface, self.indimensions), (self.smargin, self.smargin + self.UI_HEIGHT)) 

    def draw_border(self, color):
            self.screen.fill(colorTable[0][color],rect=(0,self.UI_HEIGHT,self.width,self.height))

    def get_scale(self):
        return self.scale
    
    def set_scale(self, scale):
        self.scale = scale
    
    def scale_up(self):
        # increases scale between 1 and MAXSCALE
        self.scale = (self.scale % self.MAXSCALE) + 1
        # update scaled margin and dimensions with new scale
        self.smargin = self.get_smargin()
        self.dimensions = self.update_dimensions()
        self.indimensions = self.update_indimensions()
        self._init_screen()

    def get_hwbcolor(self): # border color currently displayed
        hwbcolor = '#{:02X}{:02X}{:02X}'.format(*self.screen.get_at((0,self.UI_HEIGHT))[:3])
        return hwbcolor
    
    def get_bcolor(self) -> int:
        return self.bcolor

    def set_bcolor(self, color):
        self.bcolor = color
    
    def update_dimensions(self):
        self.width = self.get_width()
        self.height = self.get_height()
        return self.width, self.height

    def get_width(self) -> int:
        return self.get_inwidth() + (self.get_smargin() * 2)
    
    def get_height(self) -> int:
        return self.get_inheight() + (self.get_smargin() * 2) + self.UI_HEIGHT

    def update_indimensions(self):
        self.inwidth = self.get_inwidth()
        self.inheight = self.get_inheight()
        return self.inwidth, self.inheight
    
    def get_inwidth(self) -> int:
        return ZXWIDTH * self.scale
    
    def get_inheight(self) -> int:
        return ZXHEIGHT * self.scale
    
    def get_smargin(self) -> int:
        return (self.margin * self.scale)

    def set_margin(self, margin):
        self.margin = margin

    def print_info(self):
        print("Scale is: ", self.scale)
        print("Screen dimensions: ", self.dimensions)
        print("ZX scaled dimensions: ", self.indimensions)
        print("Margin is: ", self.margin)
        print("Scaled margin is: ", self.smargin)

# Funcions
def quit_app():
    print("Emulator quitting...")
    worker.stop()
    pygame.quit()
    sys.exit()

def readROM():
    f = open(ROM, mode="rb")
    dir = 0
    data = f.read(1)
    while data:
        io.ZXmem[dir] = int.from_bytes(data, byteorder="big", signed=False)
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
   while (data):
      io.ZXmem[dir] = int.from_bytes(data, byteorder='big', signed=False)
      dir = dir + 1
      data = aFile.read(1)

def memFromPackedFile(aFile, aInici, aLongitud):
   dir = aInici
   old = 0
   while (aLongitud > 0):
      bb = byteFromFile(aFile)
      aLongitud -= 1
      if ((old == 0xED) & (bb == 0xED)):
         dir -= 1
         cops = byteFromFile(aFile)
         if (cops == 0): break
         bb = byteFromFile(aFile)
         for i in range(cops):
            if dir <= 0xFFFF: io.ZXmem[dir] = bb
            dir += 1
         aLongitud -= 2
         old = 0
      else:
         if dir <= 0xFFFF: io.ZXmem[dir] = bb
         old = bb
         dir += 1


def readSpectrumFile(fichero):
    global nborder
    if fichero:
        worker.stop()

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
            b = byteFromFile(f) # Bordercolor etc
            nborder = (b & 0b00001110 ) > 1
            
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
            if (mach.registers.PC == 0): # Versions 2 i 3 del format
               b = byteFromFile(f) | (byteFromFile(f) << 8)
               mach.registers.PC = byteFromFile(f) | (byteFromFile(f) << 8)
               print('Hardware mode: '+str(byteFromFile(f)))
               f.read(b-3) # Skip b-3 bytes
               while (sz > f.tell()):
                  lon = byteFromFile(f) | (byteFromFile(f) << 8) # length of compressed data
                  b = byteFromFile(f) # page
                  if (b == 4): memFromPackedFile(f, 0x8000, lon)
                  elif (b == 5): memFromPackedFile(f, 0xC000, lon)
                  elif (b == 8): memFromPackedFile(f, 0x4000, lon)
                  else: 
                     print('Skipping page: '+str(b))
                     memFromPackedFile(f, 0xFFFFF, lon)
            else: # Versió 1 del format
               if (isPacked): memFromPackedFile(f, 16384, 49152)
               else: memFromFile(f)
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
    worker.start()


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
        ink, paper = decodecolor(io.ZXmem[adr_attributs])
        m = io.ZXmem[adr_pattern]
        b = 0b10000000
        while b:
            if (m & b):
                zx_screen.set_at((x, y), ink)
            else:
                zx_screen.set_at((x, y), paper)
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
            ink, paper = decodecolor(io.ZXmem[22528 + p])
            # 000 tt zzz yyy xxxxx
            adr_pattern = 16384 + ((p & 0b0000001100000000) << 3) + (p & 0b11111111)
            y = (p >> 5) * 8
            for offset in range(0, 2048, 256):
                m = io.ZXmem[adr_pattern + offset]
                x = (p & 0b00011111) * 8
                b = 0b10000000
                while b:
                    if (m & b):
                        zx_screen.set_at((x, y), ink)
                    else:
                        zx_screen.set_at((x, y), paper)
                    b >>= 1
                    x += 1
                y += 1
            tilechanged[p] = False


# INICI
print("Platform is: ", platform.system())

ZX_RES = ZXWIDTH, ZXHEIGHT = 256, 192
UI_HEIGHT = 30
ROM = "jocs/spectrum.rom"

contaudio = 0
bufferlen = 32
bits = -16

pygame.mixer.pre_init(44100, bits, 2, bufferlen)
#pygame.mixer.music.set_volume(1)
bufaudio = numpy.zeros((bufferlen, 2), dtype = numpy.int16)

# Initialize Pygame and the clock
clock = pygame.time.Clock()

# Initialize the Z80 machine
mach = Z80()

# Initialize graphics and GUI
main_screen = Screen()

# Set up the ZX Spectrum screen surface
zx_screen = pygame.Surface(ZX_RES) 

clock.tick(50)
is_running = True

readROM()
renderscreenFull()

# Start worker thread
worker = Worker()
worker.start() 

conta = 0
audioword = 0

# Main loop
while is_running:
    conta += 1
    if (conta & 0b00011111) == 0:
        flashReversed = not flashReversed
        for p in range(0, 768):
            if (io.ZXmem[22528 + p] & 0b10000000):
                tilechanged[p] = True

    for event in pygame.event.get():
        match event.type:
            case pygame.KEYDOWN:
                mach._iomap.keypress(event.scancode)

            case pygame.KEYUP:
                mach._iomap.keyrelease(event.scancode)

            case pygame.QUIT:
                worker.stop()
                quit_app()

            case pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
                readSpectrumFile(create_resource_path(event.text))

            case pygame_gui.UI_BUTTON_PRESSED:
                match event.ui_element:
                    case main_screen.b_quit_game:
                        # we trigger an exit event
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    
                    case main_screen.b_scale_game:
                        main_screen.scale_up()
                        main_screen.init_gui()

                    case main_screen.b_load_game:
                        file_requester = pygame_gui.windows.UIFileDialog(
                            pygame.Rect(main_screen.smargin, main_screen.smargin + main_screen.UI_HEIGHT, main_screen.inwidth, main_screen.inheight),
                            main_screen.ui_manager,
                            window_title='Open file...',
                            initial_file_path='./jocs/',
                            allow_picking_directories=False,
                            allow_existing_files_only=True,
                            visible=1,
                            allowed_suffixes={""})
 
        main_screen.ui_manager.process_events(event)

    renderscreenDiff()
    main_screen.draw_screen(zx_screen)
    time_delta = clock.tick(60)/1000.0
    main_screen.ui_manager.update(time_delta)
    main_screen.ui_manager.draw_ui(main_screen.screen) # type: ignore

    pygame.display.update()

quit_app()
