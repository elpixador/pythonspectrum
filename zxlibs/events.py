import pygame, pygame_gui
from .zxscreen import *

def check_events(event,screen):
  match event.type:
      case pygame.KEYDOWN:
          mach._iomap.keypress(event.scancode)

      case pygame.KEYUP:
          mach._iomap.keyrelease(event.scancode)

      case pygame.QUIT:
          is_running = False

      case pygame.WINDOWRESIZED:
          self.init_screen((event.x,event.y))
          self.init_gui()

      case pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
          readSpectrumFile(create_resource_path(event.text))

      case pygame_gui.UI_BUTTON_PRESSED:
          match event.ui_element.text.split()[0]: # Match first word only 
              case "Load":
                  file_requester(self.zx_screen, self.ui_manager)

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
                  """case "Screenshot":
                      area = main_screen.dimensions[0], main_screen.dimensions[1] - main_screen.UI_HEIGHT
                      screenshot = pygame.Surface(area)
                      screenshot.blit(main_screen.screen,(0,-main_screen.UI_HEIGHT))
                      pygame.image.save(screenshot,"screenshot.png")"""
              case "Freeze":
                  worker.toggle()
              case "About":
                  about_window(self.zx_screen, self.ui_manager)

          """main_screen.b_dropdown.rebuild()
          # Reset to the first option
          dropdown_menu.selected_option = dropdown_options[0]
          dropdown_menu.selected_option_text = dropdown_options[0]
          dropdown_menu.set_item_list(dropdown_options)  # Update the dropdown menu"""

  # main_screen.ui_manager.process_events(event)