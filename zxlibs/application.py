import pygame
# PyGame_GUI https://pygame-gui.readthedocs.io/en/latest/quick_start.html
import pygame_gui
from .constants import ZX_RES, APPNAME, APPVERSION
from .other import *

class AppScreen:
    def __init__(self):
        # basic initializations
        self.is_running = True
        self.is_frozen = False
        pygame.init()
        # window title
        pygame.display.set_caption(APPNAME)
        # window icon
        pygame.display.set_icon(pygame.image.load("./assets/window.png"))
        display_info = pygame.display.Info()
        self.display_resolution = display_info.current_w, display_info.current_h
        # define the height of the button bar for gui
        self.bbar_height = 40
        self.init_screen(self.display_resolution)
        self.ui = UILayer(self.display_resolution)

    def get_size(self):
        return self.screen.get_size()

    def get_width(self):
        return self.screen.get_size()[0]

    def get_height(self):
        return self.screen.get_size()[1]

    def get_screen(self):
        return self.screen

    def get_scale(self):
        return self.scale

    def init_screen(self, resolution):
        # calculates default scale for screen to fit nicely on current screen
        self.scale = self.calculate_scale(
            (ZX_RES[0], ZX_RES[1] + self.bbar_height), resolution
        )
        # our app screen dimensions will be the scaled zx spectrum + the button bar
        app_size = (ZX_RES[0] * self.scale, (ZX_RES[1] * self.scale) + self.bbar_height)
        # initialize the root surface
        self.screen = pygame.display.set_mode(app_size, pygame.RESIZABLE)
        self.fill_screen()


    # calculates max scale factor to fit a smaller surface into current screen
    def calculate_scale(self, area_to_fit, big_area) -> int:
        # gets the monitor resolution
        max_scale_width = big_area[0] // area_to_fit[0]
        max_scale_height = big_area[1] // area_to_fit[1]
        return min(max_scale_width, max_scale_height)

    # draws the spectrum screen onto the app screen
    def draw_screen(self, surface):
        self.screen.blit(
            pygame.transform.scale(surface,self.get_size()), (0, self.bbar_height)
        )

    # fills the app screen with a background
    def fill_screen(self):
        self.screen.fill(pygame.Color("#606861"))
        # pintem una banda maca on posarem els botonets
        banda = pygame.image.load("./assets/buttonbg.png").convert()
        banda = pygame.transform.scale(
            banda, (self.screen.get_width(), self.bbar_height)
        )
        self.screen.blit(banda, (0, 0))

class UILayer(pygame_gui.UIManager):
    def __init__(self, dimension):
        super().__init__(dimension, "./assets/theme.json")
        self.reset_ui()

    def reset_ui(self):
        # dimensions of each button
        button_size = button_width, button_height = 120, 30
        # gap between buttons
        gap = 3
        # we are going to allow just 1 dropdown and as many buttons as you want
        buttons = [
            ("Load Game", "button"),
            ("Options", "dropdown")
        ]
        self.dropdown_list = [
            "Options",  # sync this with dropdown button
            "Freeze",
            "Reset",
            "Screenshot",
            "About",
            "Quit"
        ]
        num_buttons = len(buttons)
        button_row = []
        button_area_length = (button_width * num_buttons) + (gap * (num_buttons - 1))
        # initial position (x and y) for buttons on the button bar
        position_y = 6
        position_x = (pygame.display.Info().current_w - button_area_length) // 2
        for i, (text, button_type) in enumerate(buttons):
            position = (position_x + (i * (button_width + gap)), position_y)
            if button_type == "button":
                button_row.append(
                    pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect(position, button_size),
                        text=text,
                        manager=self
                    )
                )
            elif button_type == "dropdown":
                button_row.append(
                    pygame_gui.elements.UIDropDownMenu(
                        relative_rect=pygame.Rect(position, button_size),
                        options_list=self.dropdown_list,
                        starting_option=self.dropdown_list[0],
                        manager=self
                    )
                )


# FUNCTIONS
def center_me(unscaled_surface, unscaled_margins, scale):
    margin_x, margin_y = unscaled_margins
    surface_x, surface_y = unscaled_surface
    scaled_margin_x = margin_x * scale
    scaled_margin_y = margin_y * scale
    scaled_surface_x = surface_x * scale
    scaled_surface_y = surface_y * scale

    return (
        scaled_margin_x,
        scaled_margin_y,
        scaled_surface_x - 2 * scaled_margin_x,
        scaled_surface_y - 2 * scaled_margin_y,
    )


def file_requester(app, manager):
    gap = gap_x, gap_y = 40, 30
    scale = app.get_scale()
    dimensions = ZX_RES
    pygame_gui.windows.UIFileDialog(
        pygame.Rect(center_me(dimensions, gap, scale)),
        manager,
        window_title="Open file...",
        initial_file_path="./jocs/",
        allow_picking_directories=False,
        allow_existing_files_only=True,
        visible=1,
        allowed_suffixes={""},
    )


def about_window(zx_surface, manager):
    gap = gap_x, gap_y = 60, 60
    scale = zx_surface.get_scale()
    dimensions = ZX_RES
    # we are going to need this later on for the labels
    buffer = center_me(dimensions, gap, 1)
    unscaled_about_x = buffer[2] - buffer[0]
    unscaled_about_y = buffer[1] - buffer[3]
    # centered about window
    about = pygame_gui.elements.UIWindow(
        pygame.Rect(center_me(dimensions, gap, scale)),
        manager,
        window_display_title="About " + APPNAME + "...",
        resizable=False,
        draggable=False,
    )
    # let's place a background into the window
    window_size = about.get_abs_rect()[2], about.get_abs_rect()[3]
    image_background = pygame_gui.elements.UIImage(
        relative_rect=pygame.Rect((0, 0), window_size),
        image_surface=pygame.image.load("./assets/zxspectrum.png").convert_alpha(),
        manager=manager,
        container=about,
    )
    # now lets type the text
    margin_x, margin_y = 10, 15

    text_contents = [
        ("center", 0, (str(APPNAME) + " v" + str(APPVERSION))),
        (20, 10, "Pixador (Z80 tweaking)"),
        (20, 10, "Dionichi (programming, audio)"),
        (20, 10, "Speedball (UI, support)"),
        ("left", 20, "Based on the Z80 emulator by"),
        ("left", 10, "Chris Burbridge"),
        ("left", 10, "https://github.com/cburbridge/z80"),
    ]

    for justification, linspace, text in text_contents:
        margin_y += linspace
        # first we create the hidden label
        # then we place it in the x axis according to the content
        # and make it visible
        label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((0, 0), (-1, -1)),
            text=text,
            manager=manager,
            container=about,
            visible=0,
        )
        # TODO: center using this approach
        new_pos = center_me(
            (unscaled_about_x, unscaled_about_y), (margin_x, margin_y), scale
        )
        if justification == "center":
            text_size = label.get_abs_rect()[2], label.get_abs_rect()[3]
            label.set_relative_position(
                (((window_size[0] - text_size[0]) // 2), margin_y)
            )
        elif justification == "left":
            new_pos = center_me(
                (unscaled_about_x, unscaled_about_y), (margin_x, margin_y), scale
            )
            label.set_relative_position((new_pos[0], new_pos[1]))
        else:
            try:
                new_pos = center_me(
                    (unscaled_about_x, unscaled_about_y), (margin_x, margin_y), scale
                )
                label.set_relative_position(
                    (new_pos[0] + int(justification), new_pos[1])
                )
            except ValueError:
                pass
        label.visible = 1
