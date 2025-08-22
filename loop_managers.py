import json
import os
import pygame

class MenuLoopManager:
    def __init__(self, screen):
        self.button_height = 70
        self.screen = screen
        self.maps = [QuizButton(i.replace(".json", ""), json.load(open(f"maps/learning_sets/{i}", 'r'))["Continent"], json.load(open(f"maps/learning_sets/{i}", 'r'))["items"], self.button_height) for i in os.listdir("maps/learning_sets")]
        self.active = True
        self.new_b = NewButton()
        self.items_width = 300
        self.scroll_pos = 0

    def update(self, scroll_value):

        y_offset = 0
        # draw the scrollbar

        if len(self.maps) * self.button_height > self.screen.get_height() - self.new_b.height:
            # calculate the height of the scrollbar
            percentage = (self.screen.get_height() - self.new_b.height) / (len(self.maps) * self.button_height)
            scrollbar_height = percentage * (self.screen.get_height() - self.new_b.height)
            max_scroll = self.screen.get_height() - self.new_b.height - scrollbar_height
            if max_scroll > 0:
                y_offset = int((self.scroll_pos / max_scroll) * (len(self.maps) * self.button_height - (self.screen.get_height() - self.new_b.height)))
            else:
                y_offset = 0
            
            # handle scrolling
            self.scroll_pos += scroll_value
            self.scroll_pos = max(0, self.scroll_pos)  # prevent scrolling above the top
            self.scroll_pos = min(self.scroll_pos, self.screen.get_height() - self.new_b.height - scrollbar_height)  # prevent scrolling below the bottom

            
            # draw the scrollbar
            pygame.draw.rect(self.screen, (200, 40, 40), (self.items_width + 5, self.scroll_pos, 20, scrollbar_height))
        else:
            pygame.draw.rect(self.screen, (255, 255, 255), (self.items_width + 5, 0, 20, self.screen.get_height()), 2)
            y_offset = 0
        
        pygame.draw.rect(self.screen, (0, 0, 0), (self.items_width, 0, 30, self.screen.get_height() - self.new_b.height), 4)  # sets up the scrollbar

        y = - y_offset  # start drawing from the scroll position
        # draw the premade quizzes
        for button in self.maps:
            if not button.draw(self.screen, y, self.items_width):  # false if the button was pressed
                self.active = False

                return 2, button.item_list

            y += self.button_height
        
        # draw the new quiz button
        if not self.new_b.draw(self.screen, self.items_width):  # false if the button was pressed
            self.active = False
            return 1, None

        return 0, None  # return 0 to indicate that the menu is still active

    def __bool__(self):
        return self.active


class QuizLoopManager:
    def __init__(self, screen, map, quiz_info):
        self.screen = screen
        self.map_data = map
        self.items = quiz_info
        self.active = True
        self.position = [1500, 0]
        self.scale = 7
        self.MAX_SCALE = 30  # Maximum scale factor
        self.MIN_SCALE = 5  # Minimum scale factor
        self.SCALE_STEP = 1.4  # Scale step for zooming in and out
        self.mouse_pos = None
        self.original_map_size = [400, 400] # 0, 0 is in the middle of the map

    def __bool__(self):
        return self.active

    def input(self, event):


        # scale changes
        if event.type == pygame.MOUSEWHEEL:
            if event.y > 0 and not self.scale * self.SCALE_STEP > self.MAX_SCALE:  # Zoom in
                mouse_x, mouse_y = pygame.mouse.get_pos()
                self.position = [
                    mouse_x - (mouse_x - self.position[0]) * self.SCALE_STEP,
                    mouse_y - (mouse_y - self.position[1]) * self.SCALE_STEP,
                ]
                self.scale *= self.SCALE_STEP
            elif event.y < 0 and not self.scale / self.SCALE_STEP < self.MIN_SCALE:  # Zoom out
                mouse_x, mouse_y = pygame.mouse.get_pos()
                self.position = [
                    mouse_x - (mouse_x - self.position[0]) / self.SCALE_STEP,
                    mouse_y - (mouse_y - self.position[1]) / self.SCALE_STEP,
                ]
                self.scale /= self.SCALE_STEP

        self.clamp_position()  # to not go out of bounds

        # moving the map
        for i in pygame.mouse.get_pressed():
            if i == 1:
                if self.mouse_pos is None:
                    self.mouse_pos = pygame.mouse.get_pos()
                else:
                    diff = (pygame.mouse.get_pos()[0] - self.mouse_pos[0], pygame.mouse.get_pos()[1] - self.mouse_pos[1])
                    self.position = [self.position[0] + diff[0], self.position[1] + diff[1]]
                    self.mouse_pos = pygame.mouse.get_pos()

        for i in pygame.mouse.get_just_released():
            if i == 1:
                self.mouse_pos = None

        self.clamp_position()  # to not go out of bounds

    def update(self):

        self.clamp_position()  # to not go out of bounds


        # Draw the map data
        for name, data in self.map_data.items():
            bb = False
            if name in self.items:
                bb = True
            for polygons in data["geometry"]:  # [[...], [...], [...]] example
                if len(polygons) < 3:
                    continue

                # Draw the polygon
                # Scale the polygon coordinates
                scaled_polygon = [(x * self.scale + self.position[0], -y * self.scale + self.position[1]) for x, y in polygons]

                # trim the exterior coordinates to the screen size
                p = [(x, y) for x, y in scaled_polygon if 0 <= x <= self.screen.get_width() and 0 <= y <= self.screen.get_height()]

                # Skip polygons that are outside the screen
                if not p:
                    continue

                # Skip polygons that are too small
                if len(p) < 3:
                    continue

                # Draw the polygon
                if bb:
                    pygame.draw.polygon(self.screen, (255, 0, 0), scaled_polygon)
                pygame.draw.aalines(self.screen, (0, 0, 0), False, scaled_polygon)

    def clamp_position(self):
        """Clamp self.position so the map (centered at pos) stays inside screen."""
        map_width  = self.original_map_size[0] * self.scale
        map_height = self.original_map_size[1] * self.scale
        screen_width, screen_height = self.screen.get_size()

        # Calculate allowed ranges for the map center
        min_x = screen_width  - map_width/2
        max_x = map_width/2
        min_y = screen_height - map_height/2
        max_y = map_height/2

        # Clamp position (map center)
        self.position[0] = max(min_x, min(self.position[0], max_x))
        self.position[1] = max(min_y, min(self.position[1], max_y))


class CreatorLoopManager:
    def __init__(self, screen):
        self.screen = screen
        self.active = False
        self.name = ""
        self.max_name_length = 24
        self.continent = ""
        self.objects = [i for i in json.load(open("maps/World.json", 'r'))]
        self.my_objects = []
        self.object_text = ""
        self.input_capture = InputCapture()
        self.input_active = 0
        self.font = pygame.font.SysFont("monospace", 40)
        self.object_font = pygame.font.SysFont("monospace", 20)
        self.padding = 6

    def __bool__(self):
        return self.active

    def change_input_goal(self, i):
        self.input_active = i
        if self.input_active:
            self.input_capture.activate()
            if i == 1:
                self.input_capture.input_text = self.name  # pokud jmeno, tak necht co tam bylo
            elif i == 2:
                self.input_capture.input_text = self.continent
        else:
            self.input_capture.deactivate()

    def update(self):

        # hande where keyboard input from IC goes
        if self.input_active == 1:
            if len(self.input_capture.get_text()) > self.max_name_length:
                self.input_capture.input_text = self.input_capture.input_text[:self.max_name_length]
            self.name = self.input_capture.get_text()
        if self.input_active == 2:
            if len(self.input_capture.get_text()) > self.max_name_length:
                self.input_capture.input_text = self.input_capture.input_text[:self.max_name_length]
            self.continent = self.input_capture.get_text()
        if self.input_active == 3:
            self.object_text = self.input_capture.get_text()

        # create a rectangle that encapsulates creator GUI
        thickness = int(((self.screen.get_height() * self.screen.get_width()) / (1920 * 1080)) * 10)
        if thickness == 0:  # cover edge cases
            thickness = 1
        pygame.draw.rect(self.screen, "black", (self.screen.get_width()/3, 20, self.screen.get_width()/3, self.screen.get_height() - 40), thickness)



        # name title
        name_txt = self.font.render("Název kvízu", True, (0, 0, 0))
        self.screen.blit(name_txt, (self.screen.get_width()/3 + thickness + self.padding * 2, 20 + thickness + self.padding * 2))

        # name input square
        name_rec = pygame.rect.Rect(self.screen.get_width()/3 + thickness + self.padding, 20 + thickness + self.padding + 50, self.screen.get_width()/3 - thickness * 2 - self.padding * 2, 50)
        if self.input_active == 1 and self.input_capture.active:
            pygame.draw.rect(self.screen, (150, 150, 150), name_rec, int(thickness/3) + 1)
        else:
            pygame.draw.rect(self.screen, (50, 50, 50), name_rec, int(thickness / 3) + 1)
        text = self.font.render(self.name, True, (0, 0, 0))
        self.screen.blit(text, (self.screen.get_width()/3 + thickness + self.padding * 2, 20 + thickness + self.padding * 2 + 50))



        # continent title
        cont_txt = self.font.render("Kontinent", True, (0, 0, 0))
        self.screen.blit(cont_txt, (self.screen.get_width()/3 + thickness + self.padding, 20 + thickness + self.padding + 100 + self.padding * 2))

        # continent selection
        cont_rec = pygame.rect.Rect(self.screen.get_width()/3 + thickness + self.padding, 20 + thickness + self.padding + 150 + self.padding * 2, self.screen.get_width()/3 - thickness * 2 - self.padding * 2, 50)
        if self.input_active == 2 and self.input_capture.active:
            pygame.draw.rect(self.screen, (150, 150, 150), cont_rec, int(thickness / 3) + 1)
        else:
            pygame.draw.rect(self.screen, (50, 50, 50), cont_rec, int(thickness / 3) + 1)
        text = self.font.render(self.continent, True, (0, 0, 0))
        self.screen.blit(text, (self.screen.get_width()/3 + thickness + self.padding * 2, 20 + thickness + self.padding + 150 + self.padding * 3))



        # objects title
        obj_txt = self.font.render("Pojmy", True, (0, 0, 0))
        self.screen.blit(obj_txt, (self.screen.get_width()/3 + thickness + self.padding, 20 + thickness + self.padding + 200 + self.padding * 2))

        # objects selector
        obj_rec = pygame.rect.Rect(self.screen.get_width()/3 + thickness + self.padding, 20 + thickness + self.padding + 250 + self.padding * 2, self.screen.get_width()/3 - thickness * 2 - self.padding * 2, 50)
        if self.input_active == 3 and self.input_capture.active:
            pygame.draw.rect(self.screen, (150, 150, 150), obj_rec, int(thickness/3) + 1)
        else:
            pygame.draw.rect(self.screen, (50, 50, 50), obj_rec, int(thickness / 3) + 1)

        text = self.font.render(self.object_text, True, (0, 0, 0))
        self.screen.blit(text, (self.screen.get_width()/3 + thickness + self.padding * 2, 20 + thickness + self.padding + 250 + self.padding * 3))

        # my objects list
        if len(self.my_objects):
            i = 0
            for country in self.my_objects:
                text = self.object_font.render(country, True, (0, 0, 0))
                self.screen.blit(text, (self.screen.get_width()/3 + thickness + self.padding, 20 + thickness + self.padding + 300 + self.padding * 3 + i * 40))
                i += 1

        # objects shower
        if self.object_text:
            i = 0
            for country in self.objects:
                if self.object_text.lower() in country.lower():
                    text_rec = pygame.rect.Rect(0, i * 40, self.screen.get_width()/3, 40)
                    if text_rec.collidepoint(pygame.mouse.get_pos()):
                        pygame.draw.rect(self.screen, (100, 180, 100), text_rec)
                        if pygame.mouse.get_pressed()[0]:
                            self.change_input_goal(3)
                            self.my_objects.append(country)
                    text = self.object_font.render(country, True, (0, 0, 0))
                    self.screen.blit(text, (0, i * 40))
                    i += 1



        # export selection
        exp_rec = pygame.rect.Rect(self.screen.get_width() / 3 + thickness + self.padding, self.screen.get_height() - thickness - self.padding - 100, self.screen.get_width() / 3 - thickness * 2 - self.padding * 2, 70)
        if exp_rec.collidepoint(pygame.mouse.get_pos()):
            pygame.draw.rect(self.screen, (150, 150, 150), exp_rec, int(thickness / 3) + 1)
            if pygame.mouse.get_pressed()[0]:
                out = {"Continent": "Europe",
                       "items": [i for i in self.my_objects]}
                with open("maps/learning_sets/" + self.name + ".json", "w") as outfile:
                    outfile.write(json.dumps(out))
                    return False

        else:
            pygame.draw.rect(self.screen, (50, 50, 50), exp_rec, int(thickness / 3) + 1)

        # export title
        exp_txt = self.font.render("Uložit", True, (0, 0, 0))
        self.screen.blit(exp_txt, (exp_rec.centerx - exp_txt.get_width() / 2, exp_rec.centery - exp_txt.get_height() / 2))



        # mouse input handel ----------------------------------------------------------------------
        if pygame.mouse.get_pressed()[0]:
            if name_rec.collidepoint(pygame.mouse.get_pos()):
                self.change_input_goal(1)
            if cont_rec.collidepoint(pygame.mouse.get_pos()):
                self.change_input_goal(2)
            if obj_rec.collidepoint(pygame.mouse.get_pos()):
                self.change_input_goal(3)

        return True


class InputCapture:
    def __init__(self):
        self.active = False
        self.input_text = ""

    def activate(self):
        self.active = True
        self.input_text = ""

    def deactivate(self):
        self.active = False

    def get_text(self):
        return self.input_text

    def handle_event(self, event):
        if not self.active:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.key == pygame.K_RETURN:
                self.deactivate()  # Optional: stop capturing on Enter
            else:
                char = event.unicode
                if char:
                    self.input_text += char
            print(self.input_text)


class QuizButton:
    def __init__(self, name, continent, item_l, height):
        self.name = name
        self.item_list = item_l
        self.continent = continent
        self.font = pygame.font.SysFont("monospace", 20)
        self.rect = pygame.Rect(0, 0, 10, height)  # Placeholder for the button rectangle
        self.text_padding = 7  # Padding for the text

    def draw(self, screen, y, w):

        # CHECK IF THE BUTTON IS HOVERED
        mouse_x, mouse_y = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_x, mouse_y):
            pygame.draw.rect(screen, (200, 40, 40), self.rect)
            if pygame.mouse.get_pressed()[0]:  # if the left mouse button is pressed
                # Here you can add the functionality for starting the quiz
                return False  # return False to indicate that the button was clicked
        else:
            pygame.draw.rect(screen, (255, 255, 255), self.rect)

        # Render the text

        name_surface = self.font.render(self.name, True, (0, 0, 0))
        info_surface = self.font.render(self.continent + "     počet: " + str(len(self.item_list)), True, (0, 0, 0))
        self.rect.y = y
        self.rect.width = w
        screen.blit(name_surface, (10, y + self.text_padding/2))
        screen.blit(info_surface, (10, y + name_surface.get_height() + self.text_padding))
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)
        return True


class NewButton:
    def __init__(self):
        self.text = "Nový kvíz"
        self.font = pygame.font.SysFont("monospace", 20)
        self.text_surface = self.font.render(self.text, True, (0, 0, 0))
        self.height = 50
        self.rect = pygame.Rect(0, 0, 10, self.height)

    def draw(self, screen, w):
        self.rect.y = screen.get_height() - self.height
        self.rect.width = w
        # determine if the mouse is hovering over the button
        mouse_x, mouse_y = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_x, mouse_y):
            self.text_surface = self.font.render(self.text, True, (255, 255, 255))
            pygame.draw.rect(screen, (200, 40, 40), self.rect)
            if pygame.mouse.get_pressed()[0]:  # if the left mouse button is pressed
                # Here you can add the functionality for creating a new quiz
                return False  # return False to indicate that the button was clicked
        else:
            self.text_surface = self.font.render(self.text, True, (0, 0, 0))
            pygame.draw.rect(screen, (255, 255, 255), self.rect)

        screen.blit(self.text_surface, (w/2 - self.text_surface.get_width()/2, screen.get_height() - self.text_surface.get_height() - self.height/2 + self.text_surface.get_height()/2))
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)
        return True
