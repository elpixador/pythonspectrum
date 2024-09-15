import pygame

# internal modules
import zxlibs
from zxlibs import AppScreen, Spectrum

# INICI
zxlibs.show_platform()

# Initialize the app screen
app = AppScreen()

# Initialize the ZXSpectrum
spectrum = Spectrum()
spectrum.readROM()

# setting the clock and running flag
clock = pygame.time.Clock()
clock.tick(50)

# Main loop
while app.is_running:

    for event in pygame.event.get():
        zxlibs.check_events(event,app,spectrum)
        app.ui.process_events(event)

    if spectrum.is_running:
        # mach.interrupt()
        # app.draw_screen(spectrum.get_surface())

        #spectrum.run_frame()
        pass


    app.fill_screen()  # DEBUG_INFO to be removed
    app.ui.update(0)
    app.ui.draw_ui(app.get_screen())
    pygame.display.flip()

zxlibs.quit_app()
