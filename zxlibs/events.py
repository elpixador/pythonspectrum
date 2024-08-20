import pygame, pygame_gui
from .zxscreen import *

def check_events(event,app,spectrum):
    match event.type:
        case pygame.KEYDOWN:
            mach._iomap.keypress(event.scancode)

        case pygame.KEYUP:
            mach._iomap.keyrelease(event.scancode)

        case pygame.QUIT:
            app.is_running = False

        case pygame.WINDOWRESIZED:
            app.init_screen((event.x, event.y))
            app.ui = UILayer(app.display_resolution)

        case pygame_gui.UI_BUTTON_PRESSED:
            match event.ui_element.text.split()[0]: # Match first word only 
                case "Load":
                    file_requester(app, app.ui)

        case pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
            readSpectrumFile(create_resource_path(event.text))

        case pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            print(event.text) # DEBUG_INFO to be removed
            match event.text.split()[0]: # matching first word only
                case "Quit":
                    # we trigger an exit event
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
                case "Reset":
                    mach.registers.reset()

                case "Screenshot":
                    pygame.image.save(spectrum.get_surface(), "screenshot.png")

                case "Freeze":
                    spectrum.is_running = not spectrum.is_running

                case "About":
                    about_window(self.zx_screen, self.ui_manager)

            app.ui.reset_ui()

          # Reset to the first option
"""          dropdown_menu.selected_option = dropdown_options[0]
          dropdown_menu.selected_option_text = dropdown_options[0]
          dropdown_menu.set_item_list(dropdown_options)  # Update the dropdown menu"""

# main_screen.ui_manager.process_events(event)
