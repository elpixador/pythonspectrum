import pygame

# internal modules
import zxlibs
from zxlibs import AppScreen, Spectrum

# INICI
zxlibs.init_terminal()

# Initialize the app screen
app = AppScreen()

# Initialize the ZXSpectrum
spectrum = Spectrum()
spectrum.plusmode = True
spectrum.readROM() # accepts a custom rom file as a parameter

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
        spectrum.run_frame()
        app.draw_screen(spectrum.get_surface())


    app.ui.update(0)
    app.ui.draw_ui(app.get_screen())
    pygame.display.flip()

zxlibs.quit_app()
