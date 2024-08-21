import pygame, sys, os
from tkinter import *
from tkinter import filedialog

#
## Z80 CPU Emulator
#This is a Zilog Z80 CPU emulator, written in Python. 
#https://github.com/cburbridge/z80
### Missing and todo
#- Most undocumented opcodes
#- Undocumented flags for `CPI` and `CPIR`.
from z80 import util,  io, registers, instructions

root = Tk() 
root.iconify() # per amagar la finestra 'root que obre el dialog box

# variables, estructures i coses
colorTable = ( # https://en.wikipedia.org/wiki/ZX_Spectrum_graphic_modes#Colour_palette
   (0x000000, 0x0100CE, 0xCF0100, 0xCF01CE, 0x00CF15, 0x01CFCF, 0xCFCF15, 0xCFCFCF), # bright 0
   (0x000000, 0x0200FD, 0xFF0201, 0xFF02FD, 0x00FF1C, 0x02FFFF, 0xFFFF1D, 0xFFFFFF)  # bright 1
)
flashReversed = False
pantalla = None
screenCache = []
unFlash = [[], []]
bordercolor = 0

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
      global bordercolor
      bordercolor = value & 0b00000111

#tratamiento ficheros
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
   return int.from_bytes(data, byteorder='big', signed=False)   

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


def readSpectrumFile():   
   fichero = filedialog.askopenfile(title='Obrir arxiu', filetypes=(('Arxius .SNA','*.SNA'), ('Arxius .SP','*.SP'), ('Arxius .Z80','*.Z80'), ('Tots','*')))
   
   if (fichero):
      io.ZXmem.reset()
      print("el fichero es "+str(fichero.name))
      nom, extensio = os.path.splitext(fichero.name)

      f = open(fichero.name, mode="rb")

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
            byteFromFile(f) # Bordercolor
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
            byteFromFile(f) # Border color
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

   else:
      print ("cancelada carga / ejecutamos ROM")
      mach.registers.reset()



  
#tratamiento video ULA
def decodecolor(atribut):
   # http://www.breakintoprogram.co.uk/hardware/computers/zx-spectrum/screen-memory-layout
   coltbl = colorTable[(atribut & 0b01000000)>>6]
   return (coltbl[atribut & 0b00000111], coltbl[(atribut & 0b00111000)>>3])

def renderline(screenY):
   # (376, 312)
   global bordercolor
   if (screenY < 60) or (screenY > 251):
      if screenCache[screenY][2] != bordercolor:
         pygame.draw.line(pantalla, colorTable[0][bordercolor], (0, screenY), (375, screenY))
         screenCache[screenY][2] = bordercolor
   else:
      y = screenY - 60
      adr_attributs = 6144 + ((y >> 3)*32)
      # 000 tt zzz yyy xxxxx
      adr_pattern = (((y & 0b11000000) | ((y & 0b111) << 3) | (y & 0b111000) >> 3) << 5)
      if screenCache[screenY][2] != bordercolor:
         border = colorTable[0][bordercolor]
         pygame.draw.line(pantalla, border, (0, screenY), (59, screenY))
         pygame.draw.line(pantalla, border, (316, screenY), (375, screenY))
         screenCache[screenY][2] = bordercolor
      x = 60
      for _ in range(32):
         attr = unFlash[flashReversed][io.ZXmem.screen(adr_attributs)]
         m = io.ZXmem.screen(adr_pattern)
         cc = screenCache[adr_pattern]
         if (cc[0] != m) or (cc[1] != attr):
            cc[0] = m
            cc[1] = attr
            ink, paper = decodecolor(attr)
            b = 0b10000000
            while b:
               if (m & b):
                  pantalla.set_at((x, screenY), ink)
               else:
                  pantalla.set_at((x, screenY), paper)
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

#Inici

mach = Z80()

#readROM("./jocs/spectrum.rom") #carreguem la rom sempre
readROM("roms/plus2-0.rom") #carreguem la rom sempre
readROM1("roms/plus2-1.rom") #carreguem la rom sempre
readSpectrumFile() #funció que càrrega qualsevol snapshoot de spectrum... en cas de no fer-ho arrenca la ROM per defecte

for i in range(6144): screenCache.append([-1, -1, -1]) # pattern, attribute, border
for i in range(256):
   unFlash[0].append(i)
   if (i & 0x80): unFlash[1].append((i & 0xC0) | ((i & 0x38) >> 3) | ((i & 0x07) << 3))
   else: unFlash[1].append(i)

pygame.init()
#pantalla = pygame.display.set_mode((376, 312), pygame.SCALED,  vsync=1)
pantalla = pygame.display.set_mode((376, 310), pygame.SCALED,  vsync=1)
pygame.display.set_caption("Hello from Spectrum World")


clock = pygame.time.Clock()
clock.tick(50) 

conta = 0
cicles = 0

while True:

  #print ('tick={}, fps={}'.format(clock.tick(60), clock.get_fps()))
   conta = conta +1

   if ((conta & 0b00011111) == 0):
      flashReversed = not flashReversed
   
   for y in range(312):
      cicles += 224
      cicles = mach.step_instruction(cicles)
      renderline(y)
   pygame.display.flip()      
   mach.interrupt()

   for event in pygame.event.get():

      if event.type == pygame.KEYDOWN:
         mach._iomap.keypress(event.scancode)
      
      elif event.type == pygame.KEYUP:
         mach._iomap.keyrelease(event.scancode)

      elif event.type == pygame.QUIT:
         pygame.quit()
         sys.exit()
