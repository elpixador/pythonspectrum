import sys, os, threading, platform
from turtle import width
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
screenCache = []

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
        global nborder, audioword

        # new values out volume
        if((value & 0b00011000) == 24):
           audioword = 29569 
        elif ((value & 0b00010000) == 16):
           audioword = 28445
        elif ((value & 0b00001000) == 8):
           audioword = 3113
        elif ((value & 0b00000000) == 0):
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

    def step_instruction(self):
        ins = False
        pc = dict(self.registers)["PC"]

        if self._interrupted and self.registers.IFF:
            self._interrupted = False
            if self.registers.HALT:
                self.registers.HALT = False
                self.registers.PC = util.inc16(pc)
            if self.registers.IM == 1:
                # print ("!!! Interrupt Mode 1 !!!")
                ins, args = self.instructions << 0xFF
            elif self.registers.IM == 2:
                # print ("!!! Interrupt Mode 2 !!!")
                imadr = (self.registers.I << 8) | 0xFF
                ins, args = self.instructions << 0xCD
                ins, args = self.instructions << self._memory[imadr & 0xFFFF]
                ins, args = self.instructions << self._memory[(imadr + 1) & 0xFFFF]
        else:
            while not ins:
                ins, args = self.instructions << self._memory[pc]
                self.registers.PC = pc = (pc + 1) & 0xFFFF
            #print("{0:X} : {1} ".format(pc, ins.assembler(args)))

        ins.execute(args)

        return ins.tstates


class Worker:
    def __init__(self):
        self.stop_event = threading.Event()
        self.thread = None

    def loop(self):
        global bufferlen, audiocount, buffaudio, audioword
        ciclesAudio = 0
        ciclesScan = 0
        cicles = 0
        y = 0
        while not self.stop_event.is_set():

            cicles = mach.step_instruction()

            ciclesAudio -= cicles
            ciclesScan -= cicles

            if (ciclesAudio <= 0):
                ciclesAudio += 158
                if (audiocount == bufferlen):
                    audiocount = 0
                else:
                    buffaudio[audiocount] = audioword 
                    audiocount += 1

            if (ciclesScan <= 0):
                ciclesScan += 224
                renderline(y)
                y += 1
                if (y == 312):
                    y = 0
                    mach.interrupt()
                    clock.tick(50)

    
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

    def toggle(self):
        if self.thread is not None and self.thread.is_alive():
            self.stop()
            print("Worker stopped")
        else:
            self.start()
            print("Worker started")

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
                        (20, 20, "Manel Calvet (programming, audio)"),
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

class EmulatorScreen:
    def __init__(self):
        self.zx_resolution = ZX_RES
        # basic initializations
        pygame.init()
        # window title
        pygame.display.set_caption(APPNAME)
        # window icon
        pygame.display.set_icon(pygame.image.load("./assets/window.png")) 
        display_info = pygame.display.Info()
        self.display_resolution = display_info.current_w, display_info.current_h
        # define the height of the button bar for gui
        self.bbar_height = 40  
        self.init_screen(self.display_resolution)

    def get_size(self):
        return self.screen.get_size()

    def get_screen(self):
        return self.screen

    def init_screen(self, resolution):
        # calculates default scale for screen to fit nicely on current screen
        self.scale = self.calculate_scale((self.zx_resolution[0], self.zx_resolution[1] + self.bbar_height), resolution)
        # our app screen dimensions will be the scaled zx spectrum + the button bar
        app_size = self.zx_resolution[0] * self.scale, (self.zx_resolution[1] * self.scale) + self.bbar_height
        # initialize the root surface
        self.screen = pygame.display.set_mode(app_size, pygame.RESIZABLE)
        self.screen.fill(pygame.Color('#606861'))
        # pintem una banda maca on posarem els botonets
        banda = pygame.image.load("./assets/buttonbg.png").convert()
        banda = pygame.transform.scale(banda, (self.screen.get_width(), self.bbar_height))
        self.screen.blit(banda,(0,0))

    # calculates max scale factor to fit a smaller surface into current screen
    def calculate_scale(self, area_to_fit, big_area) -> int:
        # gets the monitor resolution
        max_scale_width = big_area[0] // area_to_fit[0]
        max_scale_height = big_area[1] // area_to_fit[1]
        return min(max_scale_width, max_scale_height)

class UILayer(pygame_gui.UIManager):
    def __init__(self, dimension):
        super().__init__(dimension, "./assets/theme.json")
        # dimensions of each button
        button_size = button_width, button_height = 110, 30
        # gap between buttons
        gap = 3
        # we are going to allow just 1 dropdown and as many buttons as you want
        buttons = [
            ("Load Game", "button"),
            ("Options", "dropdown"),
        ]
        dropdown_list = [
            "Options",  # sync this with dropdown button
            "Scale ",
            "Freeze",
            "Reset",
            "Screenshot",
            "About",
            "Quit",
        ]
        num_buttons = len(buttons)
        button_row = []
        button_area_length = (button_width * num_buttons) + (gap * (num_buttons - 1))
        # initial position (x and y) for buttons on the button bar
        position_y = 6
        position_x = (pygame.display.Info().current_w - button_area_length) // 2
        for i, (text, button_type) in enumerate(buttons):
            position = (position_x + (i * (button_width + gap)), position_y)
            if button_type == "button":
                button_row.append(
                    pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect(position, button_size),
                        text=text,
                        manager=self,
                    )
                )
            elif button_type == "dropdown":
                button_row.append(
                    pygame_gui.elements.UIDropDownMenu(
                        relative_rect=pygame.Rect(position, button_size),
                        options_list=dropdown_list,
                        starting_option=dropdown_list[0],
                        manager=self,
                    )
                )

class Application:
    def __init__(self):
        self.zx_screen = EmulatorScreen()
        # ui initialization
        self.ui_manager = pygame_gui.UIManager((0,0))
        self.init_gui()

        # setting the clock and running flag
        self.clock = pygame.time.Clock()
        self.is_running = True

    def init_gui(self):
        self.ui_manager = UILayer(self.zx_screen.get_size())
    
    def init_screen(self, dimension):
        self.zx_screen.init_screen(dimension)

    def run(self):
        while self.is_running:
            time_delta = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.is_running = False
                if event.type == pygame.WINDOWRESIZED:
                    self.init_screen((event.x,event.y))
                    self.init_gui()
                self.ui_manager.process_events(event)
            self.ui_manager.update(time_delta)
            self.ui_manager.draw_ui(self.zx_screen.get_screen())
            pygame.display.update()


class Screen():
    DEFAULT_SCALE = 3
    MAXSCALE = 5
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
        self.screen = pygame.display.set_mode(self.dimensions, vsync=0)
        # pintem un fons maco on posarem els botonets
        fons = pygame.image.load('./assets/buttonbg.png').convert()
        fons = pygame.transform.scale(fons, (self.width, self.UI_HEIGHT))
        self.screen.blit(fons,(0,0))
    
    def init_gui(self):
        self.ui_manager = pygame_gui.UIManager(self.dimensions,'./assets/theme.json')
        buttonWidth = 110
        buttonHeight = self.UI_HEIGHT-2
        gap = 3
        ddm_options = ["Options","Scale (" + str(self.scale)+")","Freeze","Reset","Screenshot","About","Quit"]
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
        # update scaled dimensions with new scale
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
    worker.stop()
    pygame.quit()
    sys.exit()

def readROM():
    f = open(ROM, mode="rb")
    dir = 0
    data = f.read(1)
    while data:
        io.ZXmem.writeROM(dir, int.from_bytes(data, byteorder="big", signed=False))
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


def renderline(screenY):
   # (376, 312)
   global main_screen
   if (screenY < 60) or (screenY > 251):
      if screenCache[screenY][3] != main_screen.bcolor:
         pygame.draw.line(zx_screen, colorTable[0][main_screen.bcolor], (0, screenY), (375, screenY))
         screenCache[screenY][3] = main_screen.bcolor
   else:
      y = screenY - 60
      adr_attributs = 22528 + ((y >> 3)*32)
      # 000 tt zzz yyy xxxxx
      adr_pattern = 16384 + (((y & 0b11000000) | ((y & 0b111) << 3) | (y & 0b111000) >> 3) << 5)
      if screenCache[screenY][3] != main_screen.bcolor:
         border = colorTable[0][main_screen.bcolor]
         pygame.draw.line(zx_screen, border, (0, screenY), (59, screenY))
         pygame.draw.line(zx_screen, border, (316, screenY), (375, screenY))
         screenCache[screenY][3] = main_screen.bcolor
      x = 60
      for col in range(32):
         ink, paper = decodecolor(io.ZXmem[adr_attributs])
         m = io.ZXmem[adr_pattern]
         cc = screenCache[adr_pattern & 0x1FFF]
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


# INICI
print("Platform is: ", platform.system())

APPNAME = "Pythonspectrum"
APPVERSION = "1.0"
ZX_RES = ZXWIDTH, ZXHEIGHT = 376, 312
BORDER = 60
ROM = "jocs/spectrum.rom"

# initialize audio
bufferlen = 960
buffaudio = numpy.zeros((bufferlen, 1), dtype = numpy.int16)
audiocount = 0
audioword = 0

stream = sd.RawOutputStream(13500, channels=1, dtype=numpy.int16)
stream.start()

# Initialize screen cache
for i in range(6144): screenCache.append([-1, -1, -1, -1]) # attr, ink, paper, border

# Initialize Pygame and the clock
clock = pygame.time.Clock()

# Initialize the Z80 machine
mach = Z80()

# Initialize graphics and GUI
main_screen = Screen()

# Set up the ZX Spectrum screen surface
zx_screen = pygame.Surface(ZX_RES) 

clock.tick(50)

readROM()
renderscreenFull()

# Start worker thread
worker = Worker()
worker.start() 

conta = 0

# Main loop
while True:
    conta += 1
    if (conta & 0b00011111) == 0:
        flashReversed = not flashReversed

    for event in pygame.event.get():
        match event.type:
            case pygame.KEYDOWN:
                mach._iomap.keypress(event.scancode)

            case pygame.KEYUP:
                mach._iomap.keyrelease(event.scancode)

            case pygame.QUIT:
                worker.stop()
                stream.stop()
                quit_app()

            case pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
                readSpectrumFile(create_resource_path(event.text))

            case pygame_gui.UI_BUTTON_PRESSED:
                match event.ui_element:
                    case main_screen.b_load_game:
                        file_requester = pygame_gui.windows.UIFileDialog(
                            pygame.Rect(0, main_screen.UI_HEIGHT, main_screen.inwidth, main_screen.inheight),
                            main_screen.ui_manager,
                            window_title='Open file...',
                            initial_file_path='./jocs/',
                            allow_picking_directories=False,
                            allow_existing_files_only=True,
                            visible=1,
                            allowed_suffixes={""})

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
                        worker.stop()
                        mach.registers.reset()
                        worker.start()
                    case "Screenshot":
                        area = main_screen.dimensions[0], main_screen.dimensions[1] - main_screen.UI_HEIGHT
                        screenshot = pygame.Surface(area)
                        screenshot.blit(main_screen.screen,(0,-main_screen.UI_HEIGHT))
                        pygame.image.save(screenshot,"screenshot.png")
                    case "Freeze":
                        worker.toggle()
                    case "About":
                        about_window = AboutWindow(((10, 50), (280, 190)),main_screen.ui_manager)

                main_screen.b_dropdown.rebuild()
                """# Reset to the first option
                dropdown_menu.selected_option = dropdown_options[0]
                dropdown_menu.selected_option_text = dropdown_options[0]
                dropdown_menu.set_item_list(dropdown_options)  # Update the dropdown menu"""

        main_screen.ui_manager.process_events(event)

    main_screen.draw_screen(zx_screen)
    main_screen.ui_manager.update(0)
    main_screen.ui_manager.draw_ui(main_screen.screen) # type: ignore
    stream.write(buffaudio)
    pygame.display.flip()

quit_app()
