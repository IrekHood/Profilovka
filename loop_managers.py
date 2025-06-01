import json
import os
import re
import pygame


class MenuLoopManager:
    def __init__(self, screen):
        self.button_height = 70
        self.screen = screen
        self.maps = [QuizButton(i.replace(".json", ""), json.load(open(f"maps/learning_sets/{i}", 'r'))["Continent"], len(json.load(open(f"maps/learning_sets/{i}", 'r'))["items"]), self.button_height) for i in os.listdir("maps/learning_sets")]
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
            if not button.draw(self.screen, y, self.items_width):
                self.active = False

                return 2

            y += self.button_height
        
        # draw the new quiz button
        if not self.new_b.draw(self.screen, self.items_width):
            self.active = False
            return 1

        return 0  # return 0 to indicate that the menu is still active

    def __bool__(self):
        return self.active


class QuizLoopManager:
    def __init__(self, screen, map, quiz_info):
        self.screen = screen
        self.map_data = map
        self.items = quiz_info
        self.active = True

    def __bool__(self):
        return self.active

    def update(self, scale, position):

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
                scaled_polygon = [(x * 10 * scale + position[0], -y * 10 * scale + position[1]) for x, y in polygons]

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


class QuizButton:
    def __init__(self, name, continent, item_l, height):
        self.name = name
        self.item_l = item_l
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
        info_surface = self.font.render(self.continent + "     počet: "+ str(self.item_l), True, (0, 0, 0))
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