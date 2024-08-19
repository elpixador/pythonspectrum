import pygame

# internal modules
import zxlibs as zx
from zxlibs import AppScreen, UILayer, ZXScreen
from zxlibs import ZXWIDTH, ZXHEIGHT

# INICI
zx.show_platform()

"""# Initialize the Z80 machine
mach = Z80()
readROM()"""

# initialize app screen
app_screen = AppScreen()
ui_manager = UILayer(app_screen.get_size())
# Set up the ZX Spectrum screen
zx_screen = ZXScreen(ZXWIDTH, ZXHEIGHT)

# initialize audio
zxsound = zx.AudioInterface()  

# setting the clock and running flag
clock = pygame.time.Clock()
clock.tick(50)

conta = 0
cicles = 0
pausa = False

# Main loop
while True:
    # print ('tick={}, fps={}'.format(clock.tick(60), clock.get_fps()))
    if (not pausa):
        conta = conta +1

    # gestió del flash
    if (conta & 0b00011111) == 0:
        zx_screen.flashReversed = not zx_screen.flashReversed

    for y in range(312):
        cicles += 224
        # cicles = mach.step_instruction(cicles)

        if zxsound.playAudio:
            # buffer d'audio
            if zxsound.audiocount == zxsound.bufferlen:
                zxsound.audiocount = 0
                zxsound.stream.write(zxsound.buffaudio)  # comentar en cas d'anar lent
            else:
                zxsound.buffaudio[zxsound.audiocount] = zxsound.audioword
                zxsound.audiocount += 1

        # renderline(y)

    # mach.interrupt()
    # main_screen.draw_screen(zx_screen)
    time_delta = clock.tick(50) / 1000.0
    for event in pygame.event.get():
        zx.check_events(event,app_screen)
        ui_manager.process_events(event)
    ui_manager.update(time_delta)
    ui_manager.draw_ui(app_screen.get_screen())
    pygame.display.update()
