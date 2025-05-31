import json
import os

import pygame

from main import screen


class MenuLoopManager:
    def __init__(self, screen):
        self.screen = screen
        self.maps = [QuizButton(i, json.load(open(f"maps/learning_sets/{i}", 'r'))["Continent"], len(json.load(open(f"maps/learning_sets/{i}", 'r'))["items"])) for i in os.listdir("maps/learning_sets")]
        self.active = True

    def update(self):
        y = 0
        for button in self.maps:
            y += button.draw(self.screen, y)

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
                    pygame.draw.polygon(screen, (255, 0, 0), scaled_polygon)
                pygame.draw.aalines(screen, (0, 0, 0), False, scaled_polygon)


class QuizButton:
    def __init__(self, name, continent, item_l):
        self.name = name
        self.item_l = item_l
        self.continent = continent
        self.font = pygame.font.SysFont("monospace", 20)

    def draw(self, screen, y):
        name_surface = self.font.render(self.name, True, (0, 0, 0))
        items_surface = self.font.render("počet: "+ str(self.item_l), True, (0, 0, 0))
        continents_surface = self.font.render(self.continent, True, (0, 0, 0))
        screen.blit(name_surface, (0, y))
        screen.blit(items_surface, (0, y + name_surface.get_height()))
        screen.blit(continents_surface, (0, y + name_surface.get_height() + items_surface.get_height()))
        pygame.draw.rect(screen, (0, 0, 0), (0, y, name_surface.get_width(), name_surface.get_height() + items_surface.get_height() + continents_surface.get_height()), 2)
        return name_surface.get_height() + items_surface.get_height() + continents_surface.get_height()
