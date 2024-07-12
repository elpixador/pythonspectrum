import pygame, sys

mem = bytearray(65536)

def readz80file(aFilename):
   # https://worldofspectrum.org/faq/reference/z80format.htm
   f = open(aFilename, mode="rb")
   data = f.read(30)
   dir = 16384
   data = f.read(1)
   while (data):
      mem[dir] = int.from_bytes(data, byteorder='big', signed=False)
      dir = dir + 1
      data = f.read(1)
   f.close()
   print(dir)

def readsnafile(aFilename):
   # https://worldofspectrum.org/faq/reference/formats.htm
   f = open(aFilename, mode="rb")
   data = f.read(27)
   dir = 16384
   data = f.read(1)
   while (data):
      mem[dir] = int.from_bytes(data, byteorder='big', signed=False)
      dir = dir + 1
      data = f.read(1)
   f.close()
   print(dir)

def readspfile(aFilename):
   f = open(aFilename, mode="rb")
   data = f.read(6+32)
   dir = 16384
   data = f.read(1)
   while (data):
      mem[dir] = int.from_bytes(data, byteorder='big', signed=False)
      dir = dir + 1
      data = f.read(1)
   f.close()
   print(dir)

def decodecolor(atribut,special):
   # https://en.wikipedia.org/wiki/ZX_Spectrum_graphic_modes#Colour_palette
   coloret = (
      (0x000000, 0x0100CE, 0xCF0100, 0xCF01CE, 0x00CF15, 0x01CFCF, 0xCFCF15, 0xCFCFCF), # bright 0
      (0x000000, 0x0200FD, 0xFF0201, 0xFF02FD, 0x00FF1C, 0x02FFFF, 0xFFFF1D, 0xFFFFFF)  # bright 1
   )
   # http://www.breakintoprogram.co.uk/hardware/computers/zx-spectrum/screen-memory-layout
   bright = (atribut & 0b01000000)>>6
   flash = atribut & 0b10000000;

   tinta = coloret[bright][atribut & 0b00000111]
   paper = coloret[bright][(atribut & 0b00111000)>>3]
   
   if (flash >>7 & special ):   
      return (paper, tinta)
   else:
      return (tinta, paper)

def renderline(lienzo, y, adr_pattern, special):
   adr_attributs = 22528 + ((y >> 3)*32)
   x = 0
   for col in range(32):      
      ink, paper = decodecolor(mem[adr_attributs], special)
      b = 0b10000000
      while (b>0):
         if ((mem[adr_pattern] & b) == 0):
            lienzo.set_at((x, y), paper)
         else:
            lienzo.set_at((x, y), ink)
         x = x + 1
         b = b >> 1
      adr_pattern = adr_pattern + 1
      adr_attributs = adr_attributs + 1


def renderscreen1(lienzo, special):
   dir = 16384
   for y in range(192):
      # 000 tt zzz yyy xxxxx
      offset = ((y & 0b11000000) | ((y & 0b111) << 3) | (y & 0b111000) >> 3) << 5
      renderline(lienzo, y, dir+offset, special)


def renderscreen2(lienzo):
   dir = 16384
   offset = 0
   for terc in range(0, 192, 64):
      for avall in range(8):
         for y in range(0, 64, 8):
            renderline(lienzo, y+avall+terc, dir+offset)
            offset = offset + 32


print("inici")
#readz80file("jocs/Jet Set Willy (1984)(Software Projects).z80")
#readsnafile("jocs/uridium.sna")
#readspfile("jocs/GEOGRAP.SP")
#readspfile("jocs/KNLORE.SP")
readsnafile("Jetman.sna")

pygame.init()
screen = pygame.display.set_mode((256, 192), pygame.SCALED,  vsync=1)
pygame.display.set_caption("Hello World")

clock = pygame.time.Clock()
clock.tick(50) 

conta = 0
copia = 0

while True:

  #print ('tick={}, fps={}'.format(clock.tick(60), clock.get_fps()))
   conta = conta +1

   if (conta & 0b00100000):
      renderscreen1(screen,0)      
   else:
      renderscreen1(screen,1)         

   pygame.display.flip()

   for event in pygame.event.get():

      if event.type == pygame.QUIT:
         pygame.quit()
         sys.exit()
    
      

      

 
