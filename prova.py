import pygame, sys, os, threading
from tkinter import *
from tkinter import filedialog, messagebox
from time import sleep, time

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
mem = bytearray(65536)
colorTable = ( # https://en.wikipedia.org/wiki/ZX_Spectrum_graphic_modes#Colour_palette
   (0x000000, 0x0100CE, 0xCF0100, 0xCF01CE, 0x00CF15, 0x01CFCF, 0xCFCF15, 0xCFCFCF), # bright 0
   (0x000000, 0x0200FD, 0xFF0201, 0xFF02FD, 0x00FF1C, 0x02FFFF, 0xFFFF1D, 0xFFFFFF)  # bright 1
)
flashReversed = False
pantalla = None
tilechanged = [True] * 768

keysSpectrum = { # http://www.breakintoprogram.co.uk/hardware/computers/zx-spectrum/keyboard
   0x7F: 0b10111111, 0xBF: 0b10111111, 0xDF: 0b10111111, 0xEF: 0b10111111,
   0xF7: 0b10111111, 0xFB: 0b10111111, 0xFD: 0b10111111, 0xFE: 0b10111111
}

pygameKeys = { # scancode
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

tkKeys = { # keycode
   10: [0xF7, 0x01], 11: [0xF7, 0x02], 12: [0xF7, 0x04], 13: [0xF7, 0x08], 14: [0xF7, 0x10], # 12345
   15: [0xEF, 0x10], 16: [0xEF, 0x08], 17: [0xEF, 0x04], 18: [0xEF, 0x02], 19: [0xEF, 0x01], # 67890
   24: [0xFB, 0x01], 25: [0xFB, 0x02], 26: [0xFB, 0x04], 27: [0xFB, 0x08], 28: [0xFB, 0x16], # qwert
   29: [0xDF, 0x10], 30: [0xDF, 0x08], 31: [0xDF, 0x04], 32: [0xDF, 0x02], 33: [0xDF, 0x01], # yuiop
   38: [0xFD, 0x01], 39: [0xFD, 0x02], 40: [0xFD, 0x04], 41: [0xFD, 0x08], 42: [0xFD, 0x10], # asdfg
   43: [0xBF, 0x10], 44: [0xBF, 0x08], 45: [0xBF, 0x04], 46: [0xBF, 0x02], # hjkl
   52: [0xFE, 0x02], 53: [0xFE, 0x04], 54: [0xFE, 0x08], 55: [0xFE, 0x10], # zxcv
   56: [0x7F, 0x10], 57: [0x7F, 0x08], 58: [0x7F, 0x04], # bnm
   36: [0xBF, 0x01], # Enter
   65: [0x7F, 0x01], # Space
   64: [0x7F, 0x02], # Sym (Alt)
   50: [0xFE, 0x01], 62: [0xFE, 0x01] # Shift (LShift, RShift)
}

#tratamiento emulación Z80


#tratamiento ficheros
def readROM(aFilename):
   
   f = open(aFilename, mode="rb")
   dir = 0
   data = f.read(1)
   while (data):
      mem[dir] = int.from_bytes(data, byteorder='big', signed=False)
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
      mem[dir] = int.from_bytes(data, byteorder='big', signed=False)
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
            if dir <= 0xFFFF: mem[dir] = bb
            dir += 1
         aLongitud -= 2
         old = 0
      else:
         if dir <= 0xFFFF: mem[dir] = bb
         old = bb
         dir += 1


def readSpectrumFile():   
   fichero = filedialog.askopenfile(title='Obrir arxiu', filetypes=(('Arxius .SNA','*.SNA'), ('Arxius .SP','*.SP'), ('Arxius .Z80','*.Z80'), ('Tots','*')))
   
   if (fichero):
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
            isPacked = (b & 0b00100000 >> 5)
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
               f.read(b-2) # Skip b-2 bytes
               while (sz > f.tell()):
                  lon = byteFromFile(f) | (byteFromFile(f) << 8) # length of compressed data
                  b = byteFromFile(f) # page
                  if (b == 4): memFromPackedFile(f, 0x8000, lon)
                  elif (b == 5): memFromPackedFile(f, 0xC000, lon)
                  elif (b == 8): memFromPackedFile(f, 0x4000, lon)
            else: # Versió 1 del format
               if (isPacked): memFromPackedFile(f, 16384, 49152)
               else: memFromFile(f)
            f.close()

      elif extensio.upper() == '.SNA': # https://worldofspectrum.org/faq/reference/formats.htm            
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
            byteFromFile(f) # Bordercolor
            memFromFile(f)
            f.close()
            mach.registers.PC = mach._memory[mach.registers.SP] | (mach._memory[mach.registers.SP+1]) << 8
            mach.registers.SP += 2
            
      elif extensio.upper() == '.SP': # https://rk.nvg.ntnu.no/sinclair/faq/fileform.html#SP
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
   bright = (atribut & 0b01000000)>>6
   flash = (atribut & 0b10000000)>>7

   tinta = colorTable[bright][atribut & 0b00000111]
   paper = colorTable[bright][(atribut & 0b00111000)>>3]
   
   if (flash & flashReversed):
      return (paper, tinta)
   else:
      return (tinta, paper)

def renderline(y, adr_pattern):
   adr_attributs = 22528 + ((y >> 3)*32)
   x = 0
   for col in range(32):      
      ink, paper = decodecolor(mem[adr_attributs])
      b = 0b10000000
      while (b>0):
         if ((mem[adr_pattern] & b) == 0):
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
      renderline(y, dir+offset)

'''
def renderscreen2():
   dir = 16384
   offset = 0
   for terc in range(0, 192, 64):
      for avall in range(8):
         for y in range(0, 64, 8):
            renderline(y+avall+terc, dir+offset)
            offset = offset + 32
'''

def renderscreenDiff():
   for p in range(0, 768):
      if tilechanged[p] == True:
         ink, paper = decodecolor(mem[22528+p])         
         # 000 tt zzz yyy xxxxx
         adr_pattern = 16384 + ((p & 0b0000001100000000) << 3) + (p & 0b11111111)
         y = (p >> 5) * 8
         for offset in range(0, 2048, 256):
            x = (p & 0b00011111) * 8
            b = 0b10000000
            while (b>0):
               if ((mem[adr_pattern + offset] & b) == 0):
                  pantalla.set_at((x, y), paper)
               else:
                  pantalla.set_at((x, y), ink)
               b >>= 1
               x += 1
            y += 1
         tilechanged[p] = False


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
            if (self.registers.HALT == 1): self.registers.HALT = 2 # 0=normal, 1=waiting, 2=interrupted
            if self.registers.IM == 1:
                #print ("!!! Interrupt Mode 1 !!!")
                ins, args = self.instructions << 0xCD
                ins, args = self.instructions << 0x38
                ins, args = self.instructions << 0x00
            elif self.registers.IM == 2:
                #print ("!!! Interrupt Mode 2 !!!")
                imadr = (self.registers.I << 8) | 0xFF
                ins, args = self.instructions << 0xCD
                ins, args = self.instructions << self._memory[imadr & 0xFFFF]
                ins, args = self.instructions << self._memory[(imadr+1) & 0xFFFF]
        else:        
            while not ins:
                ins, args = self.instructions << self._memory[self.registers.PC]
                self.registers.PC = util.inc16(self.registers.PC)
            #print( "{0:X} : {1} ".format(pc, ins.assembler(args)))
        
        rd =  ins.get_read_list(args)
        data = [0] * len(rd)
        for n, i in enumerate(rd):
            if i < 0x10000:
                data[n] = self._memory[i]
            else:
               port = i & 0xFF
               if port == 0xFE: # keyboard
                  adr = (i & 0xFFFF) >> 8
                  res = 0xBF
                  b = 0x80
                  while (b != 0):
                     if ((adr & b) == 0): res &= keysSpectrum[b ^ 0xFF]
                     b >>= 1
                  data[n] = res
               else:
                  data[n] = 0xFF

        wrt = ins.execute(data, args)
        for i in wrt:
            adr = i[0]
            if adr > 0x10000:
                address = adr & 0xFF
                #iomap.address[address].write.emit(address, i[1])
                ##self._iomap.address[address].write(address, i[1])
                #print (chr(i[1]))
            else:
               if (adr > 16383): # Només escrivim a la RAM
                  # Caché per a renderscreenDiff
                  if ((adr < 23296) & (self._memory[adr] != i[1])): # És pantalla i ha canviat?
                     if (adr < 22528): # Patrons o atributs?
                        tilechanged[((adr & 0b0001100000000000) >> 3) | adr & 0b11111111] = True
                     else:
                        tilechanged[adr & 0b0000001111111111] = True
                  # Escrivim
                  self._memory[adr] = i[1]
        
        return ins, args

#Inici

mach = Z80()

readROM("jocs/spectrum.rom") #carreguem la rom sempre
readSpectrumFile() #funció que càrrega qualsevol snapshoot de spectrum... en cas de no fer-ho arrenca la ROM per defecte

pygame.init()
pantalla = pygame.display.set_mode((256, 192), pygame.SCALED,  vsync=1)
pygame.display.set_caption("Hello from Spectrum World")


def worker():
   t = time()
   cicles = 70908
             
   while True:
      # t = time()
      ins,  args =  mach.step_instruction()
      cicles -= ins.tstates
      if (cicles <= 0):
         cicles += 70908
         mach.interrupt()

 #     print (ins.assembler(args))
      #sleep(0.00000001) eliminada la pausa per accelar l'execució
      # print (time() - t) / ins.tstates
            
      # mach._mem_view.update()
      # mach._reg_gui.update()

thread = threading.Thread(target=worker, daemon= True)
thread.start()





clock = pygame.time.Clock()
clock.tick(50) 

conta = 0

while True:

  #print ('tick={}, fps={}'.format(clock.tick(60), clock.get_fps()))
   conta = conta +1

   if ((conta & 0b00011111) == 0):
      flashReversed = not flashReversed
      for p in range(0, 768):
         if ((mem[22528+p] & 0b10000000) != 0):
            tilechanged[p] = True

   renderscreenDiff()
   pygame.display.flip()

   for event in pygame.event.get():

      if event.type == pygame.KEYDOWN:
         if event.scancode in pygameKeys:
            k = pygameKeys[event.scancode]
            keysSpectrum[k[0]] = keysSpectrum[k[0]] & (k[1]^0xFF)
      
      elif event.type == pygame.KEYUP:
         if event.scancode in pygameKeys:
            k = pygameKeys[event.scancode]
            keysSpectrum[k[0]] = keysSpectrum[k[0]] | k[1]

      elif event.type == pygame.QUIT:
         response=messagebox.askquestion("Sortida "," Voleu sortir del programa (Yes)?\n Càrregar un altre arxiu (No)\n Continuar (Cancel)\n",   icon='warning', type='yesnocancel')
         if   response == "yes":
            pygame.quit()
            sys.exit()
         if   response == "no":
            readSpectrumFile()
            renderscreenFull()