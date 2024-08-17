import sys, os, threading, platform

import pygame
# PyGame_GUI https://pygame-gui.readthedocs.io/en/latest/quick_start.html
import pygame_gui
from pygame_gui.core.utility import create_resource_path

import numpy
import pygame_gui.elements.ui_window
import sounddevice as sd

## Z80 CPU Emulator / https://github.com/cburbridge/z80
from z80 import util, io, registers, instructions

# our internal modules
import zxlibs as zx
from zxlibs import ZX_RES

flashReversed = False
screenCache = []

bufferlen = 960
buffaudio = numpy.zeros((bufferlen, 1), dtype=numpy.int16)
audiocount = 0
audioword = 0

# initialize audio
stream = sd.RawOutputStream(13500, channels=1, dtype=numpy.int16)
stream.start()

# Initialize screen cache
for i in range(6144):
    screenCache.append([-1, -1, -1, -1])  # attr, ink, paper, border

print("Platform is:", platform.system()) # DEBUG_INFO

zx_appscreen = zx.EmulatorScreen()
ui_manager = zx.UILayer(zx_appscreen.get_size())

# setting the clock and running flag
clock = pygame.time.Clock()
is_running = True

# Initialize the Z80 machine
mach = zx.Z80()

# Set up the ZX Spectrum screen surface
zx_screen = pygame.Surface(ZX_RES)
clock.tick(50)

zx.readROM()
zx.renderscreenFull()

# Start worker thread
worker = zx.Worker()
worker.start()

conta = 0

# Main loop
while is_running:
    conta += 1
    if (conta & 0b00011111) == 0:
        flashReversed = not flashReversed

    time_delta = clock.tick(60) / 1000.0
    for event in pygame.event.get():
        zx.check_events(event,zx_appscreen)
        ui_manager.process_events(event)
    ui_manager.update(time_delta)
    ui_manager.draw_ui(zx_appscreen.get_screen())
    pygame.display.update()
zx.quit_app()

while True:

    for event in pygame.event.get():
        match event.type:
            case pygame.KEYDOWN:
                mach._iomap.keypress(event.scancode)

            case pygame.KEYUP:
                mach._iomap.keyrelease(event.scancode)

            case pygame.QUIT:
                worker.stop()
                stream.stop()
                quit_app()

            case pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
                readSpectrumFile(create_resource_path(event.text))

            case pygame_gui.UI_BUTTON_PRESSED:
                match event.ui_element:
                    case main_screen.b_load_game:
                        file_requester = pygame_gui.windows.UIFileDialog(
                            pygame.Rect(
                                0,
                                main_screen.UI_HEIGHT,
                                main_screen.inwidth,
                                main_screen.inheight,
                            ),
                            main_screen.ui_manager,
                            window_title="Open file...",
                            initial_file_path="./jocs/",
                            allow_picking_directories=False,
                            allow_existing_files_only=True,
                            visible=1,
                            allowed_suffixes={""},
                        )

            case pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
                print(event.text) # to be removed
                match event.text.split()[0]: # matching first word only
                    case "Scale":
                        main_screen.scale_up()
                        main_screen.init_gui()
                    case "Quit":
                        # we trigger an exit event
                        pygame.event.post(pygame.event.Event(pygame.QUIT))
                    case "Reset":
                        worker.stop()
                        mach.registers.reset()
                        worker.start()
                    case "Screenshot":
                        area = main_screen.dimensions[0], main_screen.dimensions[1] - main_screen.UI_HEIGHT
                        screenshot = pygame.Surface(area)
                        screenshot.blit(main_screen.screen,(0,-main_screen.UI_HEIGHT))
                        pygame.image.save(screenshot,"screenshot.png")
                    case "Freeze":
                        worker.toggle()
                    case "About":
                        about_window = AboutWindow(((10, 50), (280, 190)),main_screen.ui_manager)

                main_screen.b_dropdown.rebuild()
                """# Reset to the first option
                dropdown_menu.selected_option = dropdown_options[0]
                dropdown_menu.selected_option_text = dropdown_options[0]
                dropdown_menu.set_item_list(dropdown_options)  # Update the dropdown menu"""

        main_screen.ui_manager.process_events(event)

    main_screen.draw_screen(zx_screen)
    main_screen.ui_manager.update(0)
    main_screen.ui_manager.draw_ui(main_screen.screen) # type: ignore
    stream.write(buffaudio)
    pygame.display.flip()

quit_app()

"""if __name__ == "__main__":
    # ^  This is a guard statement that will prevent the following code from
    #    being executed in the case someone imports this file instead of
    #    executing it as a script.
    #    https://docs.python.org/3/library/__main__.html

    # After installing your project with pip, users can also run your Python
    # modules as scripts via the ``-m`` flag, as defined in PEP 338::
    #
    #     python -m my_project.skeleton 42
    #
    """
