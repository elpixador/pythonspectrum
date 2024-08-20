import sys, os, threading, platform
from typing import Optional

import pygame
# PyGame_GUI https://pygame-gui.readthedocs.io/en/latest/quick_start.html
import pygame_gui
from pygame_gui.core.utility import create_resource_path

import numpy
import sounddevice as sd

## Z80 CPU Emulator / https://github.com/cburbridge/z80
from z80 import util, io, registers, instructions

# variables, estructures i coses
colorTable = ( # https://en.wikipedia.org/wiki/ZX_Spectrum_graphic_modes#Colour_palette
   (0x000000, 0x0100CE, 0xCF0100, 0xCF01CE, 0x00CF15, 0x01CFCF, 0xCFCF15, 0xCFCFCF), # bright 0
   (0x000000, 0x0200FD, 0xFF0201, 0xFF02FD, 0x00FF1C, 0x02FFFF, 0xFFFF1D, 0xFFFFFF)  # bright 1
)

flashReversed = False
screenCache = []

# classes
class portFE(io.IO):
    _addresses = [0xFE]

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
        global audioword

         # gestió del color del borde
        main_screen.set_bcolor(value & 0b00000111) 

        # gestió del audio
        # new values out volume
        if((value & 0b00011000) == 24):
           audioword = 29569 
        elif ((value & 0b00010000) == 16):
           audioword = 28445
        elif ((value & 0b00001000) == 8):
           audioword = 3113
        else:
           audioword = 0


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
        
class AboutWindow(pygame_gui.elements.UIWindow):
    def __init__(self, rect, ui_manager):
        super().__init__(rect, ui_manager,
                        window_display_title='About '+APPNAME+"...",
                        object_id='#about_window',
                        resizable=True)
        image = pygame.image.load('./assets/zxspectrum.png').convert_alpha()
        self.test_image = pygame_gui.elements.UIImage(
            pygame.Rect((10, 10), (self.get_container().get_size()[0] - 20,
            self.get_container().get_size()[1] - 20)),
            image, 
            self.ui_manager,
            container=self
        )
        text_contents = [(70, 30, (str(APPNAME) + " v" + str(APPVERSION))),
                        (20, 20, "Pixador (Z80 tweaking)"),
                        (20, 20, "Dionichi (programming, audio)"),
                        (20, 20, "Speedball (UI, support)"),
                        (20, 10, "Based on the Z80 emulator by"),
                        (20, 10, "Chris Burbridge"),
                        (20, 10, "https://github.com/cburbridge/z80")]
        ypos = 20
        for xpos, linspace, text in text_contents:
            pygame_gui.elements.UILabel(
                                    pygame.Rect((xpos,ypos), (-1, -1)),
                                    text,
                                    self.ui_manager,
                                    container=self
                                    )
            ypos += linspace

        self.set_blocking(True)
        
class Screen():
    DEFAULT_SCALE = 3
    MAXSCALE = 3
    UI_HEIGHT = 30

    def __init__(self):
        self.scale = self.DEFAULT_SCALE
        # dimensions of app window (all scaled: ui, border + internal zx)
        self.dimensions = self.width, self.height = self.update_dimensions()
        # dimensions of internal surface for scaled zx screen 
        self.indimensions = self.inwidth, self.inheight = self.update_indimensions()

        # border color
        self.bcolor = 7 # white, default screen
        # window name
        self.caption = APPNAME
        # app icon
        self.icon = "./assets/window.png"
        # placeholders for screen and ui_manager
        self.screen: Optional[Screen] = None
        self.ui_manager = None
        # dropdown menu options
        self.ddm_options = None


        pygame.init()
        # basic initializations
        pygame.display.set_caption(self.caption)
        pygame.display.set_icon(pygame.image.load(self.icon))

        self._init_screen()
        self.init_gui()

    def _init_screen(self):
        # init main screen to fit it all (spectrum, border & gui) 
        self.screen = pygame.display.set_mode(self.dimensions, vsync=1)
        # pintem un fons maco on posarem els botonets
        fons = pygame.image.load('./assets/buttonbg.png').convert()
        fons = pygame.transform.scale(fons, (self.width, self.UI_HEIGHT))
        self.screen.blit(fons,(0,0))
    
    def init_gui(self):
        self.ui_manager = pygame_gui.UIManager(self.dimensions,'./assets/theme.json')
        buttonWidth = 110
        buttonHeight = self.UI_HEIGHT-2
        gap = 3
        ddm_options = ["Options","Scale (" + str(self.scale)+")","Freeze","Reset","Screenshot","Un/Mute","About","Quit"]
        button_info = [
            ("Load Game", "b_load_game", "UIButton"),
            (ddm_options[0], "b_dropdown", "UIDropdownMenu")
        ]
        numButtons = len(button_info)
        startingPoint = (self.width - ((buttonWidth * numButtons) + (gap * (numButtons - 1)))) / 2

        for i, (text, attr, button_type) in enumerate(button_info):
            position = (startingPoint + i * (buttonWidth + gap), 2)
            size = (buttonWidth, buttonHeight)

            if button_type == "UIButton":
                button = pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect(position, size),
                    text=text,
                    manager=self.ui_manager
                )
            elif button_type == "UIDropdownMenu":
                button = pygame_gui.elements.UIDropDownMenu(
                    options_list=ddm_options,
                    starting_option=ddm_options[0],
                    relative_rect=pygame.Rect(position, size),
                    manager=self.ui_manager,
                )
            setattr(self, attr, button)


    def draw_screen(self, surface): 
       # draw the standard zx screen onto the scaled one 
       self.screen.blit(pygame.transform.scale(surface, self.indimensions), (0, self.UI_HEIGHT))

    def get_scale(self):
        return self.scale
    
    def set_scale(self, scale):
        self.scale = scale
    
    def scale_up(self):
        # increases scale between 1 and MAXSCALE
        self.scale = (self.scale % self.MAXSCALE) + 1
        self.dimensions = self.update_dimensions()
        self.indimensions = self.update_indimensions()
        self._init_screen()
   
    def get_bcolor(self) -> int:
        return self.bcolor

    def set_bcolor(self, color):
        self.bcolor = color
    
    def update_dimensions(self):
        self.width = self.get_width()
        self.height = self.get_height()
        return self.width, self.height

    def get_width(self) -> int:
        return self.get_inwidth()
    
    def get_height(self) -> int:
        return self.get_inheight() + self.UI_HEIGHT

    def update_indimensions(self):
        self.inwidth = self.get_inwidth()
        self.inheight = self.get_inheight()
        return self.inwidth, self.inheight
    
    def get_inwidth(self) -> int:
        return ZXWIDTH * self.scale
    
    def get_inheight(self) -> int:
        return ZXHEIGHT * self.scale
    

    def print_info(self):
        print("Scale is: ", self.scale)
        print("Screen dimensions: ", self.dimensions)
        print("ZX scaled dimensions: ", self.indimensions)

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
    
    if fichero:
      extensio = os.path.splitext(fichero)[1]
      nom = os.path.basename(fichero)
      print("file to load is: " + nom)
      io.ZXmem.reset()
      io.ZXay.reset()
      f = open(fichero, mode="rb")

      #no se puede utilizar match sino es python >3.10
      if extensio.upper() == '.Z80': # https://worldofspectrum.org/faq/reference/z80format.htm
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
            bordercolor = (b & 0b00001110 ) > 1
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
               hwm = byteFromFile(f)
               print('Hardware mode: '+str(hwm))
               if (hwm < 3):
                  io.ZXmem.set48mode()
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
               else:
                  map = byteFromFile(f)
                  f.read(b-4) # Skip b-4 bytes
                  while (sz > f.tell()):
                     lon = byteFromFile(f) | (byteFromFile(f) << 8) # length of compressed data
                     b = byteFromFile(f) # page
                     io.ZXmem.changeMap(b-3)
                     memFromPackedFile(f, 0xC000, lon)
                  io.ZXmem.changeMap(map)
            else: # Versió 1 del format
               io.ZXmem.set48mode()
               if (isPacked): memFromPackedFile(f, 16384, 49152)
               else: memFromFile(f)
            f.close()

      elif extensio.upper() == '.SNA': # https://worldofspectrum.org/faq/reference/formats.htm
            io.ZXmem.set48mode()
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
            bordercolor = byteFromFile(f) # Bordercolor
            memFromFile(f)
            f.close()
            mach.registers.PC = mach._memory[mach.registers.SP] | (mach._memory[mach.registers.SP+1]) << 8
            mach.registers.SP += 2
            
      elif extensio.upper() == '.SP': # https://rk.nvg.ntnu.no/sinclair/faq/fileform.html#SP
            io.ZXmem.set48mode()
            f.read(6) # signatura i cacones
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
            byteFromFile(f) # reserved
            byteFromFile(f) # reserved
            bordercolor = byteFromFile(f) # Border color
            byteFromFile(f) # reserved
            b = byteFromFile(f) # status word low
            mach.registers.IFF = b & 1
            mach.registers.IFF2 = (b >> 2) & 1
            if ((b & 0b00001000) == 0):
               mach.registers.IM = ((b & 0b00000010) >> 1) + 1
            else:
               mach.registers.IM = 0
            byteFromFile(f) # status word high
            memFromFile(f)
            f.close()

      main_screen.set_bcolor(bordercolor) 

#tratamiento video ULA
def decodecolor(atribut):
   # http://www.breakintoprogram.co.uk/hardware/computers/zx-spectrum/screen-memory-layout
   bright = (atribut & 0b01000000)>>6
   flash = (atribut & 0b10000000)>>7

   tinta = colorTable[bright][atribut & 0b00000111]
   paper = colorTable[bright][(atribut & 0b00111000)>>3]
   
   if (flash & flashReversed):
      return (paper, tinta)
   else:
      return (tinta, paper)

def renderline(screenY):
   # (376, 312)
   global main_screen
   if (screenY < 60) or (screenY > 251):
      if screenCache[screenY][3] != main_screen.bcolor:
         pygame.draw.line(zx_screen, colorTable[0][main_screen.bcolor], (0, screenY), (375, screenY))
         screenCache[screenY][3] = main_screen.bcolor
   else:
      y = screenY - 60
      adr_attributs = 6144 + ((y >> 3)*32)
      # 000 tt zzz yyy xxxxx
      adr_pattern = (((y & 0b11000000) | ((y & 0b111) << 3) | (y & 0b111000) >> 3) << 5)
      if screenCache[screenY][3] != main_screen.bcolor:
         border = colorTable[0][main_screen.bcolor]
         pygame.draw.line(zx_screen, border, (0, screenY), (59, screenY))
         pygame.draw.line(zx_screen, border, (316, screenY), (375, screenY))
         screenCache[screenY][3] = main_screen.bcolor
      x = 60
      for col in range(32):
         ink, paper = decodecolor(io.ZXmem.screen(adr_attributs))
         m = io.ZXmem.screen(adr_pattern)
         cc = screenCache[adr_pattern]
         if (cc[0] != m) or (cc[1] != ink) or (cc[2] != paper):
            cc[0] = m
            cc[1] = ink
            cc[2] = paper
            b = 0b10000000
            while b:
               if (m & b):
                  zx_screen.set_at((x, screenY), ink)
               else:
                  zx_screen.set_at((x, screenY), paper)
               x += 1
               b >>= 1
         else:
            x += 8
         adr_pattern += 1
         adr_attributs += 1



def renderscreenFull():
    for y in range(len(screenCache)):
      cc = screenCache[y]
      for n in range(len(cc)): cc[n] = -1
    for y in range(312): renderline(y)


def screen_shoot():
    area = main_screen.dimensions[0], main_screen.dimensions[1] - main_screen.UI_HEIGHT
    screenshot = pygame.Surface(area)
    screenshot.blit(main_screen.screen,(0,-main_screen.UI_HEIGHT))
    pygame.image.save(screenshot,"screenshot.png")


def load_game():
    file_requester = pygame_gui.windows.UIFileDialog(
                            pygame.Rect(0, main_screen.UI_HEIGHT, main_screen.inwidth, main_screen.inheight),
                            main_screen.ui_manager,
                            window_title='Open file...',
                            initial_file_path='./jocs/',
                            allow_picking_directories=False,
                            allow_existing_files_only=True,
                            visible=1,
                            allowed_suffixes={""})



# INICI
print("Platform is: ", platform.system())

APPNAME = "Pythonspectrum"
APPVERSION = "1.0"
ZX_RES = ZXWIDTH, ZXHEIGHT = 376, 312 #ressolució original + borders


# Initialize the Z80 machine
mach = Z80()
#readROM("./jocs/spectrum.rom")
readROM("roms/plus2-0.rom")
readROM1("roms/plus2-1.rom")

#inicialitza pantalla
for i in range(6144): screenCache.append([-1, -1, -1, -1]) # attr, ink, paper, border
pygame.init()

main_screen = Screen()
# Set up the ZX Spectrum screen surface
zx_screen = pygame.Surface(ZX_RES) 


#initialize audio
bufferlen = 32
buffaudio = numpy.zeros((bufferlen, 1), dtype = numpy.int16)
audiocount = 0
stream = sd.RawOutputStream(12025, channels=1, dtype=numpy.int16)
stream.start()

# Initialize Pygame and the clock
clock = pygame.time.Clock()
clock.tick(50)

conta = 0
cicles = 0
audioword = 0
pausa = False
playAudio = True

# Main loop
while True:

  #print ('tick={}, fps={}'.format(clock.tick(60), clock.get_fps()))
   if (not pausa):
    conta = conta +1

    #gestió del flash
    if ((conta & 0b00011111) == 0):
            flashReversed = not flashReversed

    for y in range(312):
        cicles += 224
        #cicles += 248
        cicles = mach.step_instruction(cicles)

        if (playAudio):
            #buffer d'audio
            if (audiocount == bufferlen):
                    audiocount = 0
                    stream.write(buffaudio) #comentar en cas d'anar lent                
            else:
                    buffaudio[audiocount] = audioword + io.ZXay.calc()
                    audiocount += 1
                
        renderline(y)
        
        
    pygame.display.flip()      
    mach.interrupt()
    main_screen.draw_screen(zx_screen)
   main_screen.ui_manager.update(0)
   main_screen.ui_manager.draw_ui(main_screen.screen) # type: ignore

   for event in pygame.event.get():
        match event.type:
            case pygame.KEYDOWN:
                match event.scancode:
                    case 70: #grabar pantalla 'Impr'
                        screen_shoot()
                    case 71: #grabar video 'BLQ/desp'
                        pass
                    case 72: #Pausa 'Pausa/Intr'
                        if(pausa==False):
                            pausa = True
                        else:
                            pausa = False
                        
                    case 86: #vol Down '-'
                        pass
                    case 87: #vol Up '+'
                        pass
                    case 85: #togle scale '*'
                        main_screen.scale_up()
                        main_screen.init_gui()
                    case 41: #Abrir fichero 'ESC'
                        load_game()

                mach._iomap.keypress(event.scancode)
            case pygame.KEYUP:
                mach._iomap.keyrelease(event.scancode)
            case pygame.QUIT:
                pygame.quit()
                stream.stop()
                sys.exit()
            case pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
                readSpectrumFile(create_resource_path(event.text))
            case pygame_gui.UI_BUTTON_PRESSED:
                match event.ui_element:
                    case main_screen.b_load_game:
                        load_game()

            case pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
                print(event.text) # to be removed
                match event.text.split()[0]: # matching first word only
                    case "Scale":
                        main_screen.scale_up()
                        main_screen.init_gui()
                    case "Quit":
                        # we trigger an exit event
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    case "Reset":
                        mach.registers.reset()
                        io.ZXmem.reset()
                        io.ZXay.reset()
                    case "Screenshot":
                        screen_shoot()
                    case "Freeze":
                        if(pausa==False):
                            pausa = True
                        else:
                            pausa = False
                    case "Un/Mute":
                        playAudio = not playAudio
                    case "About":
                        about_window = AboutWindow(((10  * main_screen.get_scale(), 50 * main_screen.get_scale()), (280 * main_screen.get_scale(), 190 * main_screen.get_scale())),main_screen.ui_manager)

                main_screen.b_dropdown.rebuild()
             
        main_screen.ui_manager.process_events(event)
