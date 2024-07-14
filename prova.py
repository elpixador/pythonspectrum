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


def readSpectrumFile():

   
   fichero = filedialog.askopenfile(title='Obrir arxiu', filetypes=(('Arxius .SNA','*.SNA'), ('Arxius .SP','*.SP'), ('Arxius .Z80','*.Z80'), ('Tots','*')))
   
   if (fichero):
      print("el fichero es "+str(fichero.name))
      nom, extensio = os.path.splitext(fichero.name)

      f = open(fichero.name, mode="rb")

      #no se puede utilizar match sino es python >3.10

      if extensio.upper() == '.Z80': # https://worldofspectrum.org/faq/reference/z80format.htm
           data = f.read(30) # lee los registros del procesador
      elif extensio.upper() == '.SNA': # https://worldofspectrum.org/faq/reference/formats.htm
            data = f.read(27) # lee los registros del procesador
      elif extensio.upper() == '.SP':
              data = f.read(6+32) # lee los registros del procesador
      

      #carga el fichero restante a partir de la memoria de pantalla
      dir = 16384
      data = f.read(1)
      while (data):
         mem[dir] = int.from_bytes(data, byteorder='big', signed=False)
         dir = dir + 1
         data = f.read(1)
      f.close()

   else:
      print ("cancelada carga / ejecutamos ROM")

  
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
            self.registers.IFF = False
            self._interrupted = False
            if self.registers.IM == 1:
                print ("!!! Interrupt  !!!")
             #   ins, args = self.instructions << 0xCD
                ins, args = self.instructions << 0x38
              #  ins, args = self.instructions << 0x00
                self.registers.IFF = False
        else:        
            while not ins:
                ins, args = self.instructions << self._memory[self.registers.PC]
                self.registers.PC = util.inc16(self.registers.PC)
            print( "{0:X} : {1} ".format(pc, ins.assembler(args)))
        
        rd =  ins.get_read_list(args)
        data = [0] * len(rd)
        for n, i in enumerate(rd):
            if i < 0x10000:
                data[n] = self._memory[i]
            else:
                address = i & 0xFF
                data[n] = self._iomap.address[address].read(address)
        wrt = ins.execute(data, args)
        for i in wrt:

            if i[0] > 0x10000:
                address = i[0] & 0xFF
                #iomap.address[address].write.emit(address, i[1])
                ##self._iomap.address[address].write(address, i[1])
                #print (chr(i[1]))
            else:
               adr = i[0]
               if (adr > 16383) & (self._memory[adr] != i[1]):
                  self._memory[adr] = i[1]
                  if adr < 22528:
                     tilechanged[((adr & 0b0001100000000000) >> 3) | adr & 0b11111111] = True
                  elif (adr < 23296):
                     tilechanged[adr & 0b0000001111111111] = True
        
        return ins, args

#Inici

readROM("jocs/spectrum.rom") #carreguem la rom sempre
readSpectrumFile() #funció que càrrega qualsevol snapshoot de spectrum... en cas de no fer-ho arrenca la ROM per defecte

pygame.init()
pantalla = pygame.display.set_mode((256, 192), pygame.SCALED,  vsync=1)
pygame.display.set_caption("Hello from Spectrum World")

mach = Z80()

def worker():
   t = time()
   cicles = 70908
             
   while True:
      # t = time()
      ins,  args =  mach.step_instruction()
      """
      cicles -= ins.tstates
      if (cicles<0):
         cicles += 70908
         mach.interrupt()
      """
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

   if ((conta & 0b00001111) == 0):
      flashReversed = not flashReversed
      for p in range(0, 768):
         if ((mem[22528+p] & 0b10000000) != 0):
            tilechanged[p] = True

   renderscreenDiff()
   pygame.display.flip()

   for event in pygame.event.get():

      if event.type == pygame.QUIT:
         response=messagebox.askquestion("Sortida "," Voleu sortir del programa (Yes)?\n Càrregar un altre arxiu (No)\n Continuar (Cancel)\n",   icon='warning', type='yesnocancel')
         if   response == "yes":
            pygame.quit()
            sys.exit()
         if   response == "no":
            readSpectrumFile()
            renderscreenFull()