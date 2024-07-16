import pygame, sys, os, threading
from tkinter import *
from tkinter import filedialog, messagebox
from time import sleep, time
## Z80 CPU Emulator / https://github.com/cburbridge/z80
from z80 import util, io, registers, instructions


# variables, estructures i coses
mem = bytearray(65536)
colorTable = ( # https://en.wikipedia.org/wiki/ZX_Spectrum_graphic_modes#Colour_palette
   (0x000000, 0x0100CE, 0xCF0100, 0xCF01CE, 0x00CF15, 0x01CFCF, 0xCFCF15, 0xCFCFCF), # bright 0
   (0x000000, 0x0200FD, 0xFF0201, 0xFF02FD, 0x00FF1C, 0x02FFFF, 0xFFFF1D, 0xFFFFFF)  # bright 1
)
flashReversed = False
pantalla = None
tilechanged = [True] * 768
running = True

def stop_running(): # signals the end of the program
    global running
    running = False


# init gui and pygame windows/screens 
root = Tk() 

menubar = Menu(root)
filemenu = Menu(menubar, tearoff=0)
filemenu.add_command(label="Open ROM...", command=stop_running)
filemenu.add_command(label="Quit", command=root.quit)
menubar.add_cascade(label="File", menu=filemenu)
root.config(menu=menubar)

WIDTH = 256
HEIGHT = 192
SCALE = 3
embed = Frame(root, width=WIDTH*SCALE, height=HEIGHT*SCALE)
embed.pack()
root.update()

pygame.init()
# Tell pygame to use the tk window we created as a display
os.environ['SDL_WINDOWID'] = str(embed.winfo_id())
os.environ['SDL_VIDEODRIVER'] = 'windib'
pygame.display.init()
pantalla = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED, vsync=1)
pygame.display.set_caption("Hello from Spectrum World")
pygame.display.flip()

#root.protocol("WM_DELETE_WINDOW", lambda:pygame.quit())


while True:
    #your code here
    if running: 
        print("running")
        root.update()
        root.event_info
    else: #sortim del programa (ordenadament)
        pygame.quit()
        root.quit()
        sys.exit()