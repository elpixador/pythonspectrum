import sys, pygame

# internal modules
import zxlibs
from zxlibs import AppScreen, Spectrum

# INICI
zxlibs.show_platform()

# Initialize the app screen
app = AppScreen()

# Initialize the ZXSpectrum
spectrum = Spectrum()
#readROM("./jocs/spectrum.rom")
zxlibs.readROM("roms/plus2-0.rom")
zxlibs.readROM1("roms/plus2-1.rom")

# setting the clock and running flag
clock = pygame.time.Clock()
clock.tick(50)

pausa = False

# Main loop
while app.is_running:

    for event in pygame.event.get():
        zxlibs.check_events(event,app,spectrum)
        app.ui.process_events(event)

    if spectrum.is_running:
        # mach.interrupt()
        # app.draw_screen(spectrum.get_surface())

        spectrum.run_frame()


    app.fill_screen()  # DEBUG_INFO to be removed
    app.ui.update(0)
    app.ui.draw_ui(app.get_screen())
    pygame.display.flip()

sys.exit() # TODO: make it nicer that this
