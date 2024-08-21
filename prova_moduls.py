import sys, pygame

# internal modules
import zxlibs
from zxlibs import AppScreen, Spectrum

# INICI
zxlibs.show_platform()

"""# Initialize the Z80 machine
mach = Z80()
readROM()"""

# Initialize the app screen
app = AppScreen()
# Initialize the ZXSpectrum
spectrum = Spectrum()

# setting the clock and running flag
clock = pygame.time.Clock()
clock.tick(50)

conta = 0
cicles = 0
pausa = False

# Main loop
while app.is_running:

    time_delta = clock.tick(50) / 1000.0

    for event in pygame.event.get():
        zxlibs.check_events(event,app,spectrum)
        app.ui.process_events(event)

    if spectrum.is_running:
        # mach.interrupt()
        # app.draw_screen(spectrum.get_surface())

        """    # print ('tick={}, fps={}'.format(clock.tick(60), clock.get_fps()))
        if (not pausa):
            conta = conta +1

        # gestió del flash
        if (conta & 0b00011111) == 0:
            spectrum.flashReversed = not spectrum.flashReversed"""

        for y in range(312):
            cicles += 224
            # cicles = mach.step_instruction(cicles)

            if spectrum.audio.playAudio:
                # buffer d'audio
                if spectrum.audio.audiocount == spectrum.audio.bufferlen:
                    spectrum.audio.audiocount = 0
                    spectrum.audio.stream.write(
                        spectrum.audio.buffaudio
                    )  # comentar en cas d'anar lent
                else:
                    spectrum.audio.buffaudio[spectrum.audio.audiocount] = (
                        spectrum.audio.audioword
                    )
                    spectrum.audio.audiocount += 1

                # renderline(y)

    app.fill_screen()  # DEBUG_INFO to be removed
    app.ui.update(time_delta)
    app.ui.draw_ui(app.get_screen())
    pygame.display.update()

sys.exit() # TODO: make it nicer that this
