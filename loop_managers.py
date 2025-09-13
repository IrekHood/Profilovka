import json
import os
import random
from collections import defaultdict  # co to dela??

import pygame


def circle_polygon_collision(circle_center, circle_radius, polygon_points):
    """
    Check if a circle intersects a polygon.

    Args:
        circle_center (tuple): (x, y) of circle center in screen coords
        circle_radius (float): circle radius
        polygon_points (list): list of tuples of (x, y) coordinates

    Returns:
        bool
    """
    cx, cy = circle_center

    # --- 2. Check if circle center is inside polygon (ray-casting) ---
    inside = False
    n = len(polygon_points)
    for i in range(n):
        x1, y1 = polygon_points[i]
        x2, y2 = polygon_points[(i + 1) % n]
        if ((y1 > cy) != (y2 > cy)) and \
                (cx < (x2 - x1) * (cy - y1) / (y2 - y1 + 1e-12) + x1):
            inside = not inside
    if inside:
        return True

    # --- 3. Check distance to polygon edges ---
    for i in range(n):
        x1, y1 = polygon_points[i]
        x2, y2 = polygon_points[(i + 1) % n]

        # Closest point on line segment to circle center
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:  # Degenerate edge
            dist_sq = (cx - x1) ** 2 + (cy - y1) ** 2
        else:
            t = max(0, min(1, ((cx - x1) * dx + (cy - y1) * dy) / (dx * dx + dy * dy)))
            closest_x = x1 + t * dx
            closest_y = y1 + t * dy
            dist_sq = (cx - closest_x) ** 2 + (cy - closest_y) ** 2

        if dist_sq <= circle_radius ** 2:
            return True

    return False


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
    def __init__(self, screen, world_map_h, world_map_m, world_map_s, quiz_info):
        self.screen = screen
        self.screen_offset = [0, 0]
        self.draw_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()))
        self.map_data = [world_map_s, world_map_m, world_map_h]
        self.map_index = 0
        self.items = quiz_info
        self.active = True
        self.position = [1500, 0]
        self.scale = 7
        self.MAX_SCALE = 300  # Maximum scale factor
        self.MIN_SCALE = 5  # Minimum scale factor
        self.SCALE_STEP = 1.4  # Scale step for zooming in and out
        self.mouse_pos = None
        self.original_map_size = [400, 400]  # 0, 0 is in the middle of the map
        self.mode = 1
        # for mode 1 and on
        self.font = pygame.font.SysFont("Arial", 30)
        self.tested_place = None
        self.looked_at_polygons = []
        self.previous_polygons = []
        self.previous_name = None
        self.highlight_until = pygame.time.get_ticks() + 1000  # example wil expire after 1s
        self.clicked_color = (50, 200, 50)
        self.clicked = False
        # for mode 2
        self.input_capture = InputCapture()
        self.input_capture.activate()  # delete after mode switching implemented
        self.text_surface = self.font.render(self.input_capture.get_text(), True, (0, 0, 0))
        self.background_color = (150, 150, 170)
        # for mode 3
        self.highlight_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        self.highlight_surface.set_alpha(100)
        self.tested_places = [None, None, None, None, None, None, None, None, None, None]
        self.answered_places = [None, None, None, None, None, None, None, None, None, None]
        self.button_begin_point = 100
        self.second_row_difference = 100
        self.selected_place = None
        self.outlines_colors = ((200, 200, 200), (255, 200, 200), (200, 220, 255), (200, 255, 200))
        self.selected_colors = (
    (220, 20, 60),    # crimson red
    (34, 139, 34),    # forest green
    (70, 130, 180),   # steel blue
    (218, 165, 32),   # goldenrod
    (139, 69, 19),    # saddle brown
    (128, 0, 128),    # purple
    (105, 105, 105),  # dim gray
    (210, 105, 30),   # chocolate
    (0, 128, 128),    # teal
    (176, 196, 222),  # light steel blue
)



    def __bool__(self):
        return self.active

    def input(self, event):

        # scale changes
        if event.type == pygame.MOUSEWHEEL and pygame.rect.Rect(self.screen_offset, self.draw_surface.size).collidepoint(pygame.mouse.get_pos()):
            mouse_x, mouse_y = pygame.mouse.get_pos()[0] - self.screen_offset[0], pygame.mouse.get_pos()[1] - self.screen_offset[1]
            if event.y > 0 and not self.scale * self.SCALE_STEP > self.MAX_SCALE:  # Zoom in
                self.position = [
                    mouse_x - (mouse_x - self.position[0]) * self.SCALE_STEP,
                    mouse_y - (mouse_y - self.position[1]) * self.SCALE_STEP,
                ]
                self.scale *= self.SCALE_STEP
            elif event.y < 0 and not self.scale / self.SCALE_STEP < self.MIN_SCALE:  # Zoom out
                self.position = [
                    mouse_x - (mouse_x - self.position[0]) / self.SCALE_STEP,
                    mouse_y - (mouse_y - self.position[1]) / self.SCALE_STEP,
                ]
                self.scale /= self.SCALE_STEP

        self.clamp_position()  # to not go out of bounds

        # moving the map
        if pygame.mouse.get_pressed()[2] and pygame.rect.Rect(self.screen_offset, self.draw_surface.size).collidepoint(pygame.mouse.get_pos()):
            if self.mouse_pos is None:
                self.mouse_pos = pygame.mouse.get_pos()
            else:
                diff = (pygame.mouse.get_pos()[0] - self.mouse_pos[0], pygame.mouse.get_pos()[1] - self.mouse_pos[1])
                self.position = [self.position[0] + diff[0], self.position[1] + diff[1]]
                self.mouse_pos = pygame.mouse.get_pos()

        if not pygame.mouse.get_pressed()[2]:
            self.mouse_pos = None

        self.clamp_position()  # to not go out of bounds

        # handle text input
        self.input_capture.handle_event(event)

        # temporary mode switch     !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_m:
                if self.mode == 1: self.mode = 2
                elif self.mode == 2: self.mode = 3
                elif self.mode == 3: self.mode = 1
                self.switch_modes(self.mode)
            if event.key == pygame.K_q:
                self.map_index += 1
                if self.map_index > 2:
                    self.map_index = 0
        if event.type == pygame.WINDOWSIZECHANGED:
            self.draw_surface = pygame.Surface((event.x, event.y))
            self.highlight_surface = pygame.Surface((event.x, event.y), pygame.SRCALPHA)
            self.highlight_surface.set_alpha(100)

    def update(self, screen):

        # clear the draw surface
        self.draw_surface.fill((255, 255, 255))
        self.highlight_surface.fill((0, 0, 0, 0))

        # change polygon qualyty based on zoom
        if self.scale < 10:
            self.map_index = 0
        elif self.scale < 60:
            self.map_index = 1
        elif self.mode != 3:
            self.map_index = 2


        self.looked_at_polygons = []
        self.previous_polygons = []
        for scaled_polygon, name in self.get_visible_polygons():
            pygame.draw.aalines(self.draw_surface, (0, 0, 0), False, scaled_polygon)

            # get all clickable polygons of targeted place
            if name == self.tested_place:
                self.looked_at_polygons.append(scaled_polygon)
            if name == self.previous_name:
                self.previous_polygons.append(scaled_polygon)

        if self.mode == 1:  # tests you with a random place

            # highlight clicked place
            if self.previous_polygons and self.highlight_until > pygame.time.get_ticks():
                for polygon in self.previous_polygons:
                    pygame.draw.polygon(self.draw_surface, self.clicked_color, polygon)

            # draw name of the tested place
            if self.tested_place is None:
                self.tested_place = random.choice(self.items)
            text_surface = self.font.render(self.tested_place, True, (0, 0, 0), (255, 255, 255))
            self.draw_surface.blit(text_surface, (self.draw_surface.get_width()/2 - text_surface.get_width()/2, 0))

            # check if the tested place is pressed
            if pygame.mouse.get_pressed()[0] and not self.clicked:
                clicked = False
                self.clicked = True
                for i in self.looked_at_polygons:
                    if circle_polygon_collision(pygame.mouse.get_pos(), 10, i):
                        clicked = True

                self.highlight_until = pygame.time.get_ticks() + 1000
                self.previous_name = self.tested_place
                self.tested_place = None

                if clicked:
                    self.clicked_color = (50, 200, 50)
                else:
                    self.clicked_color = (200, 60, 60)

            # reset mouse pressing
            if not pygame.mouse.get_pressed()[0]:
                self.clicked = False

        if self.mode == 2:  # tests you on the name of the place
            if self.tested_place is None:
                self.tested_place = random.choice(self.items)

            # highlight the tested place
            for polygon in self.looked_at_polygons:
                pygame.draw.polygon(self.draw_surface, (50, 70, 150), polygon)

            # draw the text box
            if self.text_surface.get_width() < 150:
                pygame.draw.rect(self.draw_surface, self.background_color, (self.draw_surface.get_width()/2 - 75, 0, 150, self.text_surface.get_height()))
            else:
                pygame.draw.rect(self.draw_surface, self.background_color, (self.draw_surface.get_width()/2 - self.text_surface.get_width()/2, 0, self.text_surface.get_width(), self.text_surface.get_height()))

            # draw text
            self.text_surface = self.font.render(self.input_capture.get_text(), True, (0, 0, 0))
            self.draw_surface.blit(self.text_surface, (self.draw_surface.get_width()/2 - self.text_surface.get_width()/2, 0))

            # check result after enter is pressed
            if pygame.key.get_pressed()[pygame.K_RETURN] and not self.clicked:
                self.clicked = True
                text = self.input_capture.get_text()
                self.input_capture.activate()

                if text.lower() == self.tested_place.lower():
                    self.tested_place = None
                    self.background_color = (50, 200, 50)
                    self.highlight_until = pygame.time.get_ticks() + 1000
                else:
                    self.tested_place = None
                    self.background_color = (200, 60, 60)
                    self.highlight_until = pygame.time.get_ticks() + 1000

            if self.highlight_until < pygame.time.get_ticks():
                self.background_color = (150, 150, 170)

            if not pygame.key.get_pressed()[pygame.K_RETURN]:
                self.clicked = False

        if self.mode == 3:  # quiz simulation
            screen.fill((160, 160, 170))

            # Build lookup: name -> list of polygons for drawing
            visible_polygons = defaultdict(list)
            for polygon, name in self.get_visible_polygons():
                visible_polygons[name].append(polygon)

            # first 5 questions - find the place
            for i in range(5):

                text = self.font.render(self.tested_places[i], True, (0, 0, 0))
                if self.selected_place == i:
                    color = self.outlines_colors[2]
                else:
                    color = self.outlines_colors[0]
                pygame.draw.rect(screen, (120, 100, 100), ((screen.get_width() - 380, self.button_begin_point + 60 * i), (300, 50)))

                screen.blit(text, (screen.get_width() - 350, self.button_begin_point + 10 + 60 * i))

                if pygame.rect.Rect((screen.get_width() - 380, self.button_begin_point + 60 * i), (300, 50)).collidepoint(pygame.mouse.get_pos()):
                    if pygame.mouse.get_pressed()[0]:
                        self.selected_place = i
                    else:
                        color = self.outlines_colors[1]

                if self.answered_places[i]:
                    color = self.outlines_colors[3]

                pygame.draw.rect(screen, color, ((screen.get_width() - 380, self.button_begin_point + 60 * i), (300, 50)), 4)
            # select place for correct button
            if self.selected_place is not None and self.selected_place < 5 and pygame.mouse.get_pressed()[0] and pygame.mouse.get_pos()[0] < (screen.get_width() - 400) and pygame.mouse.get_pos()[1] > 100:
                for scaled_polygon, name in self.get_visible_polygons():
                    pos = list(pygame.mouse.get_pos())
                    pos[0] -= self.screen_offset[0]
                    pos[1] -= self.screen_offset[1]
                    if circle_polygon_collision(pos, 5, scaled_polygon):
                        self.answered_places[self.selected_place] = name

            # Draw selected places with color
            for i, place in enumerate(self.answered_places):
                if i > 4:
                    break
                for polygon in visible_polygons.get(place, []):
                    pygame.draw.polygon(self.highlight_surface, self.selected_colors[i], polygon)

            for i in range(5, 10):

                text = self.font.render(self.tested_places[i], True, (0, 0, 0))
                if self.selected_place == i:
                    color = self.outlines_colors[2]
                else:
                    color = self.outlines_colors[0]
                pygame.draw.rect(screen, (120, 100, 100), ((screen.get_width() - 380, self.button_begin_point + 60 * i + self.second_row_difference), (300, 50)))

                screen.blit(text, (screen.get_width() - 350, self.button_begin_point + 10 + 60 * i + self.second_row_difference))

                if pygame.rect.Rect((screen.get_width() - 380, self.button_begin_point + 60 * i + self.second_row_difference), (300, 50)).collidepoint(pygame.mouse.get_pos()):
                    if pygame.mouse.get_pressed()[0]:
                        self.selected_place = i
                    else:
                        color = self.outlines_colors[1]

                if self.answered_places[i]:
                    color = self.outlines_colors[3]

                pygame.draw.rect(screen, color, ((screen.get_width() - 380, self.button_begin_point + 60 * i + self.second_row_difference), (300, 50)), 4)

            for i, place in enumerate(self.tested_places):
                if i < 5:
                    continue
                for polygon in visible_polygons.get(place, []):
                    pygame.draw.polygon(self.highlight_surface, self.selected_colors[i], polygon)

        self.draw_surface.blit(self.highlight_surface)
        screen.blit(self.draw_surface, self.screen_offset)  # draws the map onto the display surface




    def get_visible_polygons(self):
        """
        Yield (scaled_polygon, is_selected) for all visible polygons.
        Uses precomputed bounding boxes for fast rejection.
        """
        screen_w, screen_h = self.screen.get_size()

        for name, data in self.map_data[self.map_index]["polygons"].items():
            for poly in data["geometry"]:
                points = poly["points"]
                min_x, min_y, max_x, max_y = poly["bbox"]

                # Scale + translate bbox
                scaled_min_x = min_x * self.scale + self.position[0]
                scaled_max_x = max_x * self.scale + self.position[0]
                scaled_min_y = -max_y * self.scale + self.position[1]  # note: Y flipped
                scaled_max_y = -min_y * self.scale + self.position[1]

                # Quick reject: check if bbox overlaps screen
                if scaled_max_x < 0 or scaled_min_x > screen_w or scaled_max_y < 0 or scaled_min_y > screen_h:
                    continue

                # Too small? (bounding box dimensions after scaling)
                if (scaled_max_x - scaled_min_x) < 2 or (scaled_max_y - scaled_min_y) < 2:
                    continue

                # Only scale full polygon if visible
                scaled_polygon = [
                    (x * self.scale + self.position[0], -y * self.scale + self.position[1])
                    for x, y in points
                ]

                yield scaled_polygon, name

    def clamp_position(self):
        """Clamp self.position so the map (centered at pos) stays inside screen."""
        map_width = self.original_map_size[0] * self.scale
        map_height = self.original_map_size[1] * self.scale
        screen_width, screen_height = self.screen.get_size()

        # Calculate allowed ranges for the map center
        min_x = screen_width - map_width/2
        max_x = map_width/2
        min_y = screen_height - map_height/2
        max_y = map_height/2

        # Clamp position (map center)
        self.position[0] = max(min_x, min(self.position[0], max_x))
        self.position[1] = max(min_y, min(self.position[1], max_y))

    def switch_modes(self, mode):
        if mode == 1:
            self.mode = 1
            self.screen_offset = [0, 0]
        if mode == 2:
            self.mode = 2
            self.input_capture.activate()
            self.screen_offset = [0, 0]
        if mode == 3:
            self.mode = 3
            self.screen_offset = [-400, 100]
            for i in range(10):
                self.tested_places[i] = random.choice(self.items)


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
