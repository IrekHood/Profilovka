import json
import os
import random
from collections import defaultdict  # co to dela??

import pygame
from typing import List, Tuple

Point = Tuple[float, float]
Polygon = List[Point]

def clip_polygon_to_screen(polygon: Polygon, screen_width: float, screen_height: float) -> Polygon:
    """
    Clips a polygon to the rectangle [0, screen_width] x [0, screen_height]
    using the Sutherland–Hodgman polygon clipping algorithm.
    Automatically removes crossing lines across the screen edges.
    """
    def inside(p: Point, edge: str) -> bool:
        x, y = p
        if edge == "left": return x >= 0
        if edge == "right": return x <= screen_width
        if edge == "bottom": return y >= 0
        if edge == "top": return y <= screen_height
        return True

    def intersect(p1: Point, p2: Point, edge: str) -> Point:
        x1, y1 = p1
        x2, y2 = p2
        if x1 == x2 and y1 == y2:
            return p1

        if edge == "left":
            x, y = 0, y1 + (y2 - y1) * (0 - x1) / (x2 - x1)
        elif edge == "right":
            x, y = screen_width, y1 + (y2 - y1) * (screen_width - x1) / (x2 - x1)
        elif edge == "bottom":
            x, y = x1 + (x2 - x1) * (0 - y1) / (y2 - y1), 0
        elif edge == "top":
            x, y = x1 + (x2 - x1) * (screen_height - y1) / (y2 - y1), screen_height
        return (x, y)

    def clip_edge(polygon: Polygon, edge: str) -> Polygon:
        clipped = []
        if not polygon:
            return clipped

        prev_point = polygon[-1]
        for curr_point in polygon:
            prev_inside = inside(prev_point, edge)
            curr_inside = inside(curr_point, edge)

            if curr_inside:
                if not prev_inside:
                    clipped.append(intersect(prev_point, curr_point, edge))
                clipped.append(curr_point)
            elif prev_inside:
                clipped.append(intersect(prev_point, curr_point, edge))

            prev_point = curr_point
        return clipped

    # Clip polygon against all 4 screen edges
    clipped_poly = polygon[:]
    for edge in ["left", "right", "bottom", "top"]:
        clipped_poly = clip_edge(clipped_poly, edge)
        if not clipped_poly:
            break

    return clipped_poly

def box_overlap_percent(boxA, boxB, relative_to="A"):
    """
    Calculate how much of one box overlaps another, as a percentage.

    Parameters:
        boxA, boxB: tuples (x1, y1, x2, y2)
            Each box is defined by top-left (x1, y1) and bottom-right (x2, y2).
        relative_to: str, optional
            "A" (default) — overlap as % of boxA area
            "B" — overlap as % of boxB area
            "union" — overlap as % of union area

    Returns:
        float: Overlap percentage (0–100)
    """

    # Ensure coordinates are ordered correctly
    x1A, y1A = sorted([boxA[0], boxA[2]]), sorted([boxA[1], boxA[3]])
    x1B, y1B = sorted([boxB[0], boxB[2]]), sorted([boxB[1], boxB[3]])

    # Compute overlap bounds
    x_left = max(x1A[0], x1B[0])
    y_top = max(y1A[0], y1B[0])
    x_right = min(x1A[1], x1B[1])
    y_bottom = min(y1A[1], y1B[1])

    # Check for no overlap
    if x_right <= x_left or y_bottom <= y_top:
        return 0.0

    # Areas
    areaA = (x1A[1] - x1A[0]) * (y1A[1] - y1A[0])
    areaB = (x1B[1] - x1B[0]) * (y1B[1] - y1B[0])
    intersection = (x_right - x_left) * (y_bottom - y_top)
    union = areaA + areaB - intersection

    if relative_to == "B":
        base = areaB
    elif relative_to == "union":
        base = union
    else:
        base = areaA

    return 100.0 * intersection / base


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


def circle_polyline_collision(circle_center, circle_radius, line_points):
    """
    Check if a circle intersects a polyline (open multipoint line).

    Args:
        circle_center (tuple): (x, y) of circle center in screen coords
        circle_radius (float): circle radius
        line_points (list): list of tuples of (x, y) coordinates defining the line

    Returns:
        bool
    """
    cx, cy = circle_center
    n = len(line_points)

    if n < 2:
        return False  # Need at least two points to form a line segment

    # Check distance to each line segment
    for i in range(n - 1):
        x1, y1 = line_points[i]
        x2, y2 = line_points[i + 1]

        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:  # Degenerate segment (single point)
            dist_sq = (cx - x1) ** 2 + (cy - y1) ** 2
        else:
            # Projection factor clamped to [0,1]
            t = max(0, min(1, ((cx - x1) * dx + (cy - y1) * dy) / (dx * dx + dy * dy)))
            closest_x = x1 + t * dx
            closest_y = y1 + t * dy
            dist_sq = (cx - closest_x) ** 2 + (cy - closest_y) ** 2

        if dist_sq <= circle_radius ** 2:
            return True

    return False


def circle_point_collision(circle_center, circle_radius, point_pos):
    dist_sqrt = (circle_center[0] - point_pos[0]) ** 2 + (circle_center[1] - point_pos[1]) ** 2

    if dist_sqrt <= circle_radius ** 2:
        return True
    return False

def preprocess_map_data(map_data):
    """
    Add precomputed bounding boxes to each polygon in map_data.
    Each polygon becomes a dict: {"points": [...], "bbox": (min_x, min_y, max_x, max_y)}
    """
    polygon = map_data["geometry"]
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    bbox = (min(xs), min(ys), max(xs), max(ys))
    map_data["geometry"] = [{"points": polygon, "bbox": bbox}]


class MenuLoopManager:
    def __init__(self, screen):
        self.button_height = 70
        self.screen = screen
        self.maps = [QuizButton(i.replace(".json", ""), json.load(open(f"maps/learning_sets/{i}", 'r'))["Continent"], json.load(open(f"maps/learning_sets/{i}", 'r'))["items"], self.button_height) for i in os.listdir("maps/learning_sets")]
        self.active = True
        self.new_b = NewButton()
        self.items_width = 300
        self.scroll_pos = 0
        self.ignore_first_click = True

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
            if not button.draw(self.screen, y, self.items_width) and self.ignore_first_click:  # false if the button was pressed
                self.active = False

                return 2, button.item_list

            y += self.button_height
        
        # draw the new quiz button
        if not self.new_b.draw(self.screen, self.items_width) and self.ignore_first_click:  # false if the button was pressed
            self.active = False
            return 1, None

        if not pygame.mouse.get_pressed()[0]:
            self.ignore_first_click = True

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
        self.mode_names = ["mód: klikni na", "mód: pojmenuj", "mód: kvíz"]
        self.mode_clicked = False
        # for mode 1 and on
        self.font = pygame.font.SysFont("Arial", 30)
        self.tested_place = None
        self.looked_at_polygons = []
        self.previous_term = None
        self.highlight_until = pygame.time.get_ticks() + 1000  # example wil expire after 1s
        self.clicked_color = (50, 200, 50)
        self.clicked = False
        # for mode 2
        self.input_capture = InputCapture()
        self.text_surface = self.font.render(self.input_capture.get_text(), True, (0, 0, 0))
        self.background_color = (150, 150, 170)
        # for mode 3
        self.answer_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        self.highlight_surface = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        self.highlight_surface.set_alpha(100)
        self.tested_places = [None, None, None, None, None, None, None, None, None, None]
        self.answered_places = [None, None, None, None, None, None, None, None, None, None]
        self.answer_text_surfaces = [None, None, None, None, None, [None, ""], [None, ""], [None, ""], [None, ""], [None, ""]]
        self.button_begin_point = 100
        self.second_row_difference = 100
        self.selected_place = None
        self.outlines_colors = ((200, 200, 200), (255, 200, 200), (200, 220, 255), (0, 0, 0))
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
        if event.type == pygame.MOUSEWHEEL and pygame.rect.Rect(self.screen_offset, (self.draw_surface.get_width(), self.draw_surface.get_height())).collidepoint(pygame.mouse.get_pos()):
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
            self.scaling = True

        self.clamp_position()  # to not go out of bounds

        # moving the map
        if pygame.mouse.get_pressed()[2] and pygame.rect.Rect(self.screen_offset, (self.draw_surface.get_width(), self.draw_surface.get_height())).collidepoint(pygame.mouse.get_pos()):
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

        if event.type == pygame.WINDOWSIZECHANGED:
            self.draw_surface = pygame.Surface((event.x, event.y))
            self.highlight_surface = pygame.Surface((event.x, event.y), pygame.SRCALPHA)
            self.highlight_surface.set_alpha(100)

    def update(self, screen):

        # clear the draw surface
        self.draw_surface.fill((100, 100, 255))
        self.highlight_surface.fill((0, 0, 0, 0))

        # change polygon qualyty based on zoom
        if self.scale < 10:
            self.map_index = 0
        elif self.scale < 120:
            self.map_index = 1
        else:
            self.map_index = 2


        # draw all polygons
        for scaled_polygon, name in self.get_visible_polygons():
            pygame.draw.polygon(self.draw_surface, (100, 155, 100), scaled_polygon)
            pygame.draw.aalines(self.draw_surface, (0, 0, 0), False, scaled_polygon)

        # draw all lines
        for scaled_polygon, name in self.get_visible_lines():
            pygame.draw.aalines(self.draw_surface, (60, 60, 200), False, scaled_polygon)

        # draw all body's of water
        for scaled_polygon, name in self.get_visible_water_bodeys():
            pygame.draw.polygon(self.draw_surface, (60, 60, 220), scaled_polygon)

        # draw all cities/points
        for scaled_point, name, rank, capital in self.get_visible_points():
            if capital:
                pygame.draw.circle(self.draw_surface, (209, 49, 245), scaled_point, 2 + self.map_index * 1.5)
            else:
                pygame.draw.circle(self.draw_surface, (0, 0, 0), scaled_point, 1 + self.map_index/2)

        for scaled_polygon, name in self.get_visible_custom_polygons():
            pygame.draw.polygon(self.highlight_surface, (100, 100, 100), scaled_polygon)
            pygame.draw.aalines(self.draw_surface, (0, 0, 0), False, scaled_polygon)


        if self.mode == 1:  # tests you with a random place

            # highlight clicked place
            if self.previous_term and self.highlight_until > pygame.time.get_ticks():
                if self.previous_term[0] == "points":
                    pos = self.map_data[2][self.previous_term[0]][self.previous_term[1]]["geometry"]
                    pygame.draw.circle(self.draw_surface, self.clicked_color, self.scale_point(pos[0], pos[1]), 5)
                elif self.previous_term[0] == "lines":
                    lines = [i["points"] for i in self.map_data[2][self.previous_term[0]][self.previous_term[1]]["geometry"]]
                    for points in lines:
                        pygame.draw.lines(self.draw_surface, self.clicked_color, False, self.scale_points(points), 5)
                else:
                    lines = [i["points"] for i in self.map_data[2][self.previous_term[0]][self.previous_term[1]]["geometry"]]
                    for points in lines:
                        pygame.draw.polygon(self.draw_surface, self.clicked_color, self.scale_points(points))

            # draw name of the tested place
            if self.tested_place is None:
                key = random.choice(list(self.items.keys()))
                while not len(self.items[key]):
                    key = random.choice(list(self.items.keys()))
                self.tested_place = [key, random.choice(self.items[key])]
            text_surface = self.font.render(self.tested_place[1], True, (0, 0, 0), (255, 255, 255))
            self.draw_surface.blit(text_surface, (self.draw_surface.get_width()/2 - text_surface.get_width()/2, 0))

            # check if the tested place is pressed
            if pygame.mouse.get_pressed()[0] and not self.clicked:
                clicked = False
                self.clicked = True
                if self.tested_place[0] == "points":
                    pos = self.map_data[2][self.tested_place[0]][self.tested_place[1]]["geometry"]
                    if circle_point_collision(pygame.mouse.get_pos(), 10, self.scale_point(pos[0], pos[1])):
                        clicked = True
                elif self.tested_place[0] == "lines":
                    for i in self.map_data[2][self.tested_place[0]][self.tested_place[1]]["geometry"]:
                        if circle_polyline_collision(pygame.mouse.get_pos(), 10, self.scale_points(i["points"])):
                            clicked = True
                else:
                    for i in self.map_data[2][self.tested_place[0]][self.tested_place[1]]["geometry"]:
                        if circle_polygon_collision(pygame.mouse.get_pos(), 10, self.scale_points(i["points"])):
                            clicked = True

                self.highlight_until = pygame.time.get_ticks() + 1000
                self.previous_term = self.tested_place
                self.tested_place = None

                if clicked:
                    self.clicked_color = (50, 200, 50)
                else:
                    self.clicked_color = (200, 60, 60)

            # reset mouse pressing
            if not pygame.mouse.get_pressed()[0]:
                self.clicked = False

        if self.mode == 2:
            # tests you on the name of the place
            if self.tested_place is None:
                key = random.choice(list(self.items.keys()))
                while not len(self.items[key]):
                    key = random.choice(list(self.items.keys()))
                self.tested_place = [key, random.choice(self.items[key])]

            # highlight the tested place
            if self.tested_place:
                if self.tested_place[0] == "points":
                    pos = self.map_data[2][self.tested_place[0]][self.tested_place[1]]["geometry"]
                    pygame.draw.circle(self.draw_surface, (50, 70, 150), self.scale_point(pos[0], pos[1]), 5)
                elif self.tested_place[0] == "lines":
                    lines = [i["points"] for i in
                             self.map_data[2][self.tested_place[0]][self.tested_place[1]]["geometry"]]
                    for points in lines:
                        pygame.draw.lines(self.draw_surface, (50, 70, 150), False, self.scale_points(points), 5)
                else:
                    lines = [i["points"] for i in
                             self.map_data[2][self.tested_place[0]][self.tested_place[1]]["geometry"]]
                    for points in lines:
                        pygame.draw.polygon(self.draw_surface, (50, 70, 150), self.scale_points(points))

            # draw the text box
            if self.text_surface.get_width() < 150:
                pygame.draw.rect(self.draw_surface, self.background_color, (self.draw_surface.get_width()/2 - 75, 0, 150, self.text_surface.get_height()))
            else:
                pygame.draw.rect(self.draw_surface, self.background_color, (self.draw_surface.get_width()/2 - self.text_surface.get_width()/2, 0, self.text_surface.get_width(), self.text_surface.get_height()))

            # draw text
            self.text_surface = self.font.render(self.input_capture.get_text(), True, (0, 0, 0), self.background_color)
            self.draw_surface.blit(self.text_surface, (self.draw_surface.get_width()/2 - self.text_surface.get_width()/2, 0))

            # check result after enter is pressed
            if pygame.key.get_pressed()[pygame.K_RETURN] and not self.clicked:
                self.clicked = True
                text = self.input_capture.get_text()
                self.input_capture.activate()

                if text.lower() == self.tested_place[1].lower():
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

                if self.selected_place == i:
                    color = self.outlines_colors[2]
                else:
                    color = self.outlines_colors[0]
                pygame.draw.rect(screen, (120, 100, 100), ((screen.get_width() - 380, self.button_begin_point + 60 * i), (300, 50)))

                screen.blit(self.answer_text_surfaces[i], (screen.get_width() - 350, self.button_begin_point + 10 + 60 * i))

                if pygame.rect.Rect((screen.get_width() - 380, self.button_begin_point + 60 * i), (300, 50)).collidepoint(pygame.mouse.get_pos()):
                    if pygame.mouse.get_pressed()[0]:
                        self.selected_place = i
                    else:
                        color = self.outlines_colors[1]

                if self.answered_places[i]:
                    color = self.selected_colors[i]

                pygame.draw.rect(screen, color, ((screen.get_width() - 380, self.button_begin_point + 60 * i), (300, 50)), 4)

            # select place for correct button
            if self.selected_place is not None and self.selected_place < 5 and pygame.mouse.get_pressed()[0] and pygame.mouse.get_pos()[0] < (screen.get_width() - 400) and pygame.mouse.get_pos()[1] > 100:
                mouse_pos = list(pygame.mouse.get_pos())
                mouse_pos[0] -= self.screen_offset[0]
                mouse_pos[1] -= self.screen_offset[1]
                intersect_list = []
                for pos, name, _, _ in self.get_visible_points():
                    if circle_point_collision(mouse_pos, 10, pos):
                        intersect_list.append({"points": name})
                for line, name in self.get_visible_lines():
                    if circle_polyline_collision(mouse_pos, 10, line):
                        intersect_list.append({"lines": name})
                for pol, name in self.get_visible_water_bodeys():
                    if circle_polygon_collision(mouse_pos, 10, pol):
                        intersect_list.append({"blue_polygons": name})
                for pol, name in self.get_visible_custom_polygons():
                    if circle_polygon_collision(mouse_pos, 10, pol):
                        intersect_list.append({"new_polygons": name})
                for pol, name in self.get_visible_polygons():
                    if circle_polygon_collision(mouse_pos, 10, pol):
                        intersect_list.append({"polygons": name})
                if intersect_list:
                    item = intersect_list[0]
                    self.answered_places[self.selected_place] = [list(item.keys())[0], list(item.values())[0]]
                    # owerides the random stuff

                    # doesnt work fix
                    for i in intersect_list:
                        if i in self.tested_places:
                            self.answered_places[self.selected_place] = [list(i.keys())[0], list(i.values())[0]]
                            break


            # last 5 questions type the name of the selected state
            for i in range(5, 10):

                text = self.font.render(self.answered_places[i], True, (0, 0, 0))
                if self.answer_text_surfaces[i][1] != self.answered_places[i]:
                    self.answer_text_surfaces[i][0] = self.font.render(self.answered_places[i], True, (0, 0, 0))
                    self.answer_text_surfaces[i][1] = self.answered_places[i]
                if self.selected_place == i:
                    color = self.outlines_colors[3]
                else:
                    color = self.selected_colors[i]
                pygame.draw.rect(screen, (120, 100, 100), ((screen.get_width() - 380, self.button_begin_point + 60 * i + self.second_row_difference), (300, 50)))

                screen.blit(self.answer_text_surfaces[i][0], (screen.get_width() - 350, self.button_begin_point + 10 + 60 * i + self.second_row_difference))

                if pygame.rect.Rect((screen.get_width() - 380, self.button_begin_point + 60 * i + self.second_row_difference), (300, 50)).collidepoint(pygame.mouse.get_pos()):
                    if pygame.mouse.get_pressed()[0]:  # if the button has been pressed
                        self.selected_place = i
                        if self.answered_places[i] is not None:
                            self.input_capture.input_text = self.answered_places[i]
                        else:
                            self.input_capture.input_text = ""
                    else:
                        color = self.outlines_colors[1]

                pygame.draw.rect(screen, color, ((screen.get_width() - 380, self.button_begin_point + 60 * i + self.second_row_difference), (300, 50)), 4)

                if self.selected_place == i:
                    self.answered_places[self.selected_place] = self.input_capture.get_text()

            # highlight the tested places
            for i, place in enumerate(self.tested_places):
                if i < 5:
                    continue
                if place[0] == "points":
                    pos = self.map_data[2][place[0]][place[1]]["geometry"]
                    pygame.draw.circle(self.highlight_surface, self.selected_colors[i], self.scale_point(pos[0], pos[1]), 5)
                elif place[0] == "lines":
                    lines = [i["points"] for i in
                             self.map_data[2][place[0]][place[1]]["geometry"]]
                    for points in lines:
                            pygame.draw.lines(self.highlight_surface, self.selected_colors[i], False, self.scale_points(points), 4)
                else:
                    lines = [i["points"] for i in
                             self.map_data[2][place[0]][place[1]]["geometry"]]
                    for points in lines:
                        if len(points) > 2:
                            pygame.draw.polygon(self.highlight_surface, self.selected_colors[i], self.scale_points(points))
                if i == self.selected_place:
                    if place[0] == "points":
                        pos = self.map_data[2][place[0]][place[1]]["geometry"]
                        pygame.draw.circle(self.draw_surface, "black",
                                             self.scale_point(pos[0], pos[1]), 7)
                    else:
                        lines = [i["points"] for i in
                                 self.map_data[2][place[0]][place[1]]["geometry"]]
                        for points in lines:
                            pygame.draw.lines(self.draw_surface, "black", False,
                                              self.scale_points(points), 4)

            # Draw selected places with color !!!!!!!! for questions 1-5 for better draw order
            for i, place in enumerate(self.answered_places):
                if i > 4:
                    break
                if place:
                    if place[0] == "points":
                        pos = self.map_data[2][place[0]][place[1]]["geometry"]
                        pygame.draw.circle(self.highlight_surface, self.selected_colors[i], self.scale_point(pos[0], pos[1]), 5)
                    elif place[0] == "lines":
                        lines = [i["points"] for i in
                                 self.map_data[2][place[0]][place[1]]["geometry"]]
                        for points in lines:
                                pygame.draw.lines(self.highlight_surface, self.selected_colors[i], False, self.scale_points(points), 4)
                    else:
                        lines = [i["points"] for i in
                                 self.map_data[2][place[0]][place[1]]["geometry"]]
                        boxes = [i["bbox"] for i in
                                 self.map_data[2][place[0]][place[1]]["geometry"]]
                        for j, points in enumerate(lines):
                            if len(points) > 2:
                                overlap = box_overlap_percent(self.scale_bbox(boxes[j]), [self.screen_offset[0], self.screen_offset[1], self.screen.get_width() + self.screen_offset[0], self.screen.get_height() + self.screen_offset[1]])
                                if overlap < 10:
                                    points = clip_polygon_to_screen(self.scale_points(points), self.screen.get_width(), self.screen.get_height() + self.screen_offset[1])
                                else:
                                    points = self.scale_points(points)
                                if len(points) > 3:
                                    pygame.draw.polygon(self.highlight_surface, self.selected_colors[i], points)


            # the evaulate button
            eval_text = self.font.render("zkontrolovat", True, (0, 0, 0))
            pygame.draw.rect(screen, (120, 100, 100), ((10, 10), (195, 45)))
            pygame.draw.rect(screen, (0, 0, 0), ((10, 10), (195, 45)), 4)
            screen.blit(eval_text, (25, 15))
            if pygame.rect.Rect(((10, 10), (195, 45))).collidepoint(pygame.mouse.get_pos()):
                if pygame.mouse.get_pressed()[0] and not self.clicked:
                    self.clicked = True
                    pygame.draw.rect(screen, (100, 100, 200), ((10, 10), (195, 45)), 4)
                    self.answer_surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
                    for i in range(5):
                        if self.answered_places[i] is not None and self.answered_places[i][1].lower() == self.tested_places[i][1].lower():
                            pygame.draw.rect(self.answer_surface, (100, 250, 100), ((screen.get_width() - 60, self.button_begin_point + 60 * i), (50, 50)))
                        else:
                            pygame.draw.rect(self.answer_surface, (250, 100, 100), ((screen.get_width() - 60, self.button_begin_point + 60 * i), (50, 50)))

                    for i in range(5, 10):
                        if self.answered_places[i] is not None and self.answered_places[i].lower() == self.tested_places[i][1].lower():
                            pygame.draw.rect(self.answer_surface, (100, 250, 100), ((screen.get_width() - 60, self.button_begin_point + 60 * i + self.second_row_difference), (50, 50)))
                        else:
                            pygame.draw.rect(self.answer_surface, (250, 100, 100), ((screen.get_width() - 60, self.button_begin_point + 60 * i + self.second_row_difference), (50, 50)))

                else:
                    pygame.draw.rect(screen, (140, 140, 160), ((10, 10), (195, 45)), 4)
            else:
                pygame.draw.rect(screen, (0, 0, 0), ((10, 10), (195, 45)), 4)

            if self.clicked and not pygame.mouse.get_pressed()[0]:
                self.clicked = False


            # the reset button
            eval_text = self.font.render("znovu", True, (0, 0, 0))
            pygame.draw.rect(screen, (120, 100, 100), ((220, 10), (110, 45)))
            screen.blit(eval_text, (235, 15))
            if pygame.rect.Rect(((220, 10), (110, 45))).collidepoint(pygame.mouse.get_pos()):
                if pygame.mouse.get_pressed()[0] and not self.clicked:
                    self.clicked = True
                    pygame.draw.rect(screen, (100, 100, 200), ((220, 10), (110, 45)), 4)
                    self.switch_modes(3)
                    self.answered_places = [None, None, None, None, None, None, None, None, None, None]
                    self.answer_surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
                else:
                    pygame.draw.rect(screen, (140, 140, 160), ((220, 10), (110, 45)), 4)
            else:
                pygame.draw.rect(screen, (0, 0, 0), ((220, 10), (110, 45)), 4)

            if self.clicked and not pygame.mouse.get_pressed()[0]:
                self.clicked = False


        self.draw_surface.blit(self.highlight_surface, (0, 0))
        screen.blit(self.draw_surface, self.screen_offset)  # draws the map onto the display surface
        screen.blit(self.answer_surface, (0, 0))

        # the change modes button
        mode_text = self.font.render(self.mode_names[self.mode-1], True, (0, 0, 0))
        pygame.draw.rect(screen, (120, 100, 100), ((screen.get_width() - mode_text.get_width() - 40, screen.get_height() - 50), (mode_text.get_width() + 20, 45)))
        screen.blit(mode_text, (screen.get_width() - mode_text.get_width() - 40 + 10, screen.get_height() - 50 + 5))
        if pygame.rect.Rect(((screen.get_width() - mode_text.get_width() - 40, screen.get_height() - 50), (mode_text.get_width() + 20, 45))).collidepoint(pygame.mouse.get_pos()):
            if pygame.mouse.get_pressed()[0] and not self.mode_clicked:
                self.mode_clicked = True
                pygame.draw.rect(screen, (100, 100, 200), ((screen.get_width() - mode_text.get_width() - 40, screen.get_height() - 50), (mode_text.get_width() + 20, 45)), 4)
                if self.mode == 1:
                    self.mode = 2
                elif self.mode == 2:
                    self.mode = 3
                elif self.mode == 3:
                    self.mode = 1
                    self.answer_surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
                self.switch_modes(self.mode)
            else:
                pygame.draw.rect(screen, (140, 140, 160), ((screen.get_width() - mode_text.get_width() - 40, screen.get_height() - 50), (mode_text.get_width() + 20, 45)), 4)
        else:
            pygame.draw.rect(screen, (0, 0, 0), ((screen.get_width() - mode_text.get_width() - 40, screen.get_height() - 50), (mode_text.get_width() + 20, 45)), 4)


        # the back button
        back_text = self.font.render("zpět", True, (0, 0, 0))
        pygame.draw.rect(screen, (120, 100, 100), ((screen.get_width() - back_text.get_width() - 40, screen.get_height() - 100), (back_text.get_width() + 20, 45)))
        screen.blit(back_text, (screen.get_width() - back_text.get_width() - 30, screen.get_height() - 100 + 5))
        if pygame.rect.Rect(((screen.get_width() - back_text.get_width() - 40, screen.get_height() - 100), (back_text.get_width() + 20, 45))).collidepoint(pygame.mouse.get_pos()):
            if pygame.mouse.get_pressed()[0] and not self.mode_clicked:
                self.mode_clicked = True
                pygame.draw.rect(screen, (100, 100, 200), ((screen.get_width() - back_text.get_width() - 40, screen.get_height() - 100), (back_text.get_width() + 20, 45)), 4)
                self.active = False
            else:
                pygame.draw.rect(screen, (140, 140, 160), ((screen.get_width() - back_text.get_width() - 40, screen.get_height() - 100), (back_text.get_width() + 20, 45)), 4)
        else:
            pygame.draw.rect(screen, (0, 0, 0), ((screen.get_width() - back_text.get_width() - 40, screen.get_height() - 100), (back_text.get_width() + 20, 45)), 4)

        if self.mode_clicked and not pygame.mouse.get_pressed()[0]:
            self.mode_clicked = False

    def scale_point(self, x, y):
        """Scale and translate a single point to screen coordinates."""
        return (x * self.scale + self.position[0],
                -y * self.scale + self.position[1])  # note: Y flipped

    def scale_points(self, points):
        """Scale and translate a list of points (polygon/line)."""
        return [self.scale_point(x, y) for x, y in points]

    def scale_bbox(self, bbox):
        """Scale and translate a bounding box (min_x, min_y, max_x, max_y)."""
        min_x, min_y, max_x, max_y = bbox
        scaled_min_x = min_x * self.scale + self.position[0]
        scaled_max_x = max_x * self.scale + self.position[0]
        scaled_min_y = -max_y * self.scale + self.position[1]  # note: Y flipped
        scaled_max_y = -min_y * self.scale + self.position[1]
        return scaled_min_x, scaled_min_y, scaled_max_x, scaled_max_y

    def get_visible_polygons(self):
        screen_w, screen_h = self.screen.get_size()

        for name, data in self.map_data[self.map_index]["polygons"].items():
            for poly in data["geometry"]:
                scaled_min_x, scaled_min_y, scaled_max_x, scaled_max_y = self.scale_bbox(poly["bbox"])

                # Quick reject: check if bbox overlaps screen
                if scaled_max_x < 0 or scaled_min_x > screen_w or scaled_max_y < 0 or scaled_min_y > screen_h:
                    continue

                # Too small after scaling
                if (scaled_max_x - scaled_min_x) < 2 or (scaled_max_y - scaled_min_y) < 2:
                    continue


                scaled_polygon = self.scale_points(poly["points"])
                if len(scaled_polygon) > 30:
                    overlapp = box_overlap_percent([0, 0, screen_w, screen_h], [scaled_min_x, scaled_min_y, scaled_max_x, scaled_max_y], relative_to="B")
                    if overlapp < 10:
                        scaled_polygon = clip_polygon_to_screen(polygon=scaled_polygon, screen_width=screen_w, screen_height=screen_h)

                    if len(scaled_polygon) < 3:
                        continue

                yield scaled_polygon, name

    def get_visible_lines(self):
        screen_w, screen_h = self.screen.get_size()

        for name, data in self.map_data[self.map_index]["lines"].items():
            for line in data["geometry"]:
                scaled_min_x, scaled_min_y, scaled_max_x, scaled_max_y = self.scale_bbox(line["bbox"])

                if scaled_max_x < 0 or scaled_min_x > screen_w or scaled_max_y < 0 or scaled_min_y > screen_h:
                    continue

                scaled_line = self.scale_points(line["points"])
                yield scaled_line, name

    def get_visible_water_bodeys(self):
        screen_w, screen_h = self.screen.get_size()

        for name, data in self.map_data[self.map_index]["blue_polygons"].items():
            for poly in data["geometry"]:
                scaled_min_x, scaled_min_y, scaled_max_x, scaled_max_y = self.scale_bbox(poly["bbox"])

                if scaled_max_x < 0 or scaled_min_x > screen_w or scaled_max_y < 0 or scaled_min_y > screen_h:
                    continue

                if (scaled_max_x - scaled_min_x) < 2 or (scaled_max_y - scaled_min_y) < 2:
                    continue

                scaled_polygon = self.scale_points(poly["points"])
                yield scaled_polygon, name

    def get_visible_points(self):
        screen_w, screen_h = self.screen.get_size()

        for name, data in self.map_data[self.map_index]["points"].items():
            scaled_x, scaled_y = self.scale_point(*data["geometry"])

            if scaled_x < 0 or scaled_x > screen_w or scaled_y < 0 or scaled_y > screen_h:
                continue

            # reject if city has low importance
            if self.map_index == 0 and not data["capital"] and data["rank"] < 9:
                continue
            if self.map_index == 1 and not data["capital"] and data["rank"] < 8:
                continue


            yield (scaled_x, scaled_y), name, data["rank"], data["capital"]

        screen_w, screen_h = self.screen.get_size()

        for name, data in self.map_data[self.map_index]["points"].items():
            # Scale + translate bbox
            scaled_x = data["geometry"][0] * self.scale + self.position[0]
            scaled_y = -data["geometry"][1] * self.scale + self.position[1]  # note: Y flipped

            # Quick reject: check if bbox overlaps screen
            if scaled_x < 0 or scaled_x > screen_w or scaled_y < 0 or scaled_y > screen_h:
                continue


            yield (scaled_x, scaled_y), name, data["rank"], data["capital"]

    def get_visible_custom_polygons(self):
        screen_w, screen_h = self.screen.get_size()

        for name, data in self.map_data[self.map_index]["new_polygons"].items():
            for poly in data["geometry"]:
                scaled_min_x, scaled_min_y, scaled_max_x, scaled_max_y = self.scale_bbox(poly["bbox"])

                # Quick reject: check if bbox overlaps screen
                if scaled_max_x < 0 or scaled_min_x > screen_w or scaled_max_y < 0 or scaled_min_y > screen_h:
                    continue

                # Too small after scaling
                if (scaled_max_x - scaled_min_x) < 2 or (scaled_max_y - scaled_min_y) < 2:
                    continue

                scaled_polygon = self.scale_points(poly["points"])
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
        if mode == 3 and len(self.items["polygons"]) + len(self.items["lines"]) + len(self.items["blue_polygons"]) + len(self.items["points"]) < 10:
            self.switch_modes(1)
            pass
        if mode == 3 and len(self.items["polygons"]) + len(self.items["lines"]) + len(self.items["blue_polygons"]) + len(self.items["points"]) > 9:
            self.mode = 3
            self.screen_offset = [-400, 100]
            self.input_capture.activate()
            self.fill_quiz()

    def fill_quiz(self):
        i = 0
        while i < 10:
            key = random.choice(list(self.items.keys()))
            while not len(self.items[key]):
                key = random.choice(list(self.items.keys()))
            choice = [key, random.choice(self.items[key])]
            if choice not in self.tested_places:
                self.tested_places[i] = choice
                i += 1
        self.answer_text_surfaces = [self.font.render(self.tested_places[0][1], True, (0, 0, 0)), self.font.render(self.tested_places[1][1], True, (0, 0, 0)), self.font.render(self.tested_places[2][1], True, (0, 0, 0)), self.font.render(self.tested_places[3][1], True, (0, 0, 0)), self.font.render(self.tested_places[4][1], True, (0, 0, 0)), [None, ""], [None, ""], [None, ""], [None, ""], [None, ""]]


class CreatorLoopManager:
    def __init__(self, screen):
        self.screen = screen
        self.active = False
        self.name = ""
        self.max_name_length = 24
        self.continent = ""
        self.objects = json.load(open("maps/terms.json", 'r'))
        self.my_objects = {"polygons": [],
                           "blue_polygons": [],
                           "points": [],
                           "lines": [],
                           "new_polygons": []}
        self.object_text = ""
        self.input_capture = InputCapture()
        self.input_active = 0
        self.font = pygame.font.SysFont("monospace", 40)
        self.object_font = pygame.font.SysFont("monospace", 20)
        self.padding = 6
        self.clicked = False
        self.text_offset = 0

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

    def input(self, event):
        if event.type == pygame.MOUSEWHEEL:
            self.text_offset = min(0, self.text_offset + event.y * 3)


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
        cont_txt = self.font.render("Oblast", True, (0, 0, 0))
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

        # new term btton
        trm_txt = self.font.render("Nový pojem", True, (0, 0, 0))
        trm_rect = pygame.rect.Rect(self.screen.get_width()/3 + thickness + self.padding, 20 + thickness + self.padding + 310 + self.padding * 2, self.screen.get_width()/3 - thickness * 2 - self.padding * 2, 60)
        pygame.draw.rect(self.screen, (120, 100, 100), trm_rect)

        self.screen.blit(trm_txt, (self.screen.get_width()/2 - trm_txt.get_width()/2, 20 + thickness + self.padding + 320 + self.padding * 2))

        if trm_rect.collidepoint(pygame.mouse.get_pos()):
            if pygame.mouse.get_pressed()[0]:
                pygame.draw.rect(self.screen, (100, 100, 200), trm_rect, int(thickness/3) + 1)
                return False, True
            else:
                pygame.draw.rect(self.screen, (140, 140, 160), trm_rect, int(thickness/3) + 1)
        else:
            pygame.draw.rect(self.screen, (0, 0, 0), trm_rect, int(thickness/3) + 1)



        # my objects list
        if len(self.my_objects):
            i = 0
            for type in self.my_objects.keys():
                for term in self.my_objects[type]:
                    text_color = (0, 0, 0)
                    if pygame.rect.Rect(self.screen.get_width()/3 * 2 + thickness + self.padding, thickness + self.padding * 2 + i * 40 + self.text_offset, self.screen.get_width()/3, thickness + self.padding * 4).collidepoint(pygame.mouse.get_pos()):
                        pygame.draw.rect(self.screen, (150, 0, 0), (self.screen.get_width()/3 * 2 + thickness + self.padding, thickness + self.padding * 2 + i * 40 + self.text_offset, self.screen.get_width()/3,  thickness + self.padding * 4))
                        text_color = (255, 255, 255)
                        if pygame.mouse.get_pressed()[0] and not self.clicked:
                            self.clicked = True
                            self.my_objects[type].remove(term)
                    text = self.object_font.render(term, True, text_color)
                    self.screen.blit(text, (self.screen.get_width()/3 * 2 + thickness + self.padding, thickness + self.padding * 4 + i * 40 + self.text_offset))
                    i += 1

        if not pygame.mouse.get_pressed()[0]:
            self.clicked = False

        # objects shower
        if self.object_text:
            i = 0
            for type in self.objects.keys():
                for term in self.objects[type]:
                    if self.object_text.lower() in term.lower():
                        text_rec = pygame.rect.Rect(0, i * 40, self.screen.get_width()/3, 40)
                        if type == "polygons":
                            pygame.draw.rect(self.screen, (255, 204, 0), text_rec)
                        elif type == "lines":
                            pygame.draw.rect(self.screen, (51, 153, 255), text_rec)
                        elif type == "blue_polygons":
                            pygame.draw.rect(self.screen, (0, 51, 153), text_rec)
                        elif type == "points":
                            pygame.draw.rect(self.screen, (180, 100, 180), text_rec)
                        elif type == "new_polygons":
                            pygame.draw.rect(self.screen, (120, 120, 120), text_rec)

                        if text_rec.collidepoint(pygame.mouse.get_pos()):
                            pygame.draw.rect(self.screen, (100, 180, 100), text_rec)
                            if pygame.mouse.get_pressed()[0]:
                                self.change_input_goal(3)
                                self.my_objects[type].append(term)
                        text = self.object_font.render(term, True, (0, 0, 0))
                        self.screen.blit(text, (0, i * 40))
                        i += 1



        # export selection
        exp_rec = pygame.rect.Rect(self.screen.get_width() / 3 + thickness + self.padding, self.screen.get_height() - thickness - self.padding - 100, self.screen.get_width() / 3 - thickness * 2 - self.padding * 2, 70)
        if exp_rec.collidepoint(pygame.mouse.get_pos()):
            pygame.draw.rect(self.screen, (150, 150, 150), exp_rec, int(thickness / 3) + 1)
            if pygame.mouse.get_pressed()[0]:
                out = {"Continent": self.continent,
                       "items": self.my_objects}
                with open("maps/learning_sets/" + self.name + ".json", "w") as outfile:
                    outfile.write(json.dumps(out))
                    return False, False

        else:
            pygame.draw.rect(self.screen, (50, 50, 50), exp_rec, int(thickness / 3) + 1)

        # export title
        exp_txt = self.font.render("Uložit", True, (0, 0, 0))
        self.screen.blit(exp_txt, (exp_rec.centerx - exp_txt.get_width() / 2, exp_rec.centery - exp_txt.get_height() / 2))


        # exit button
        back_text = self.font.render("zahodit", True, (0, 0, 0))
        pygame.draw.rect(self.screen, (120, 100, 100), ((self.screen.get_width() - back_text.get_width() - 40, self.screen.get_height() - back_text.get_height() - 20), (back_text.get_width() + 20, 45)))
        self.screen.blit(back_text, (self.screen.get_width() - back_text.get_width() - 30, self.screen.get_height() - back_text.get_height() - 20 + 5))
        if pygame.rect.Rect(((self.screen.get_width() - back_text.get_width() - 40, self.screen.get_height() - back_text.get_height() - 20), (back_text.get_width() + 20, 45))).collidepoint(pygame.mouse.get_pos()):
            if pygame.mouse.get_pressed()[0]:
                pygame.draw.rect(self.screen, (100, 100, 200), ((self.screen.get_width() - back_text.get_width() - 40, self.screen.get_height() - back_text.get_height() - 20), (back_text.get_width() + 20, 45)), 4)
                self.my_objects = {"polygons": [],
                                   "blue_polygons": [],
                                   "points": [],
                                   "lines": [],
                                   "new_polygons": []}
                self.object_text = ""
                return False, False
            else:
                pygame.draw.rect(self.screen, (140, 140, 160), ((self.screen.get_width() - back_text.get_width() - 40, self.screen.get_height() - back_text.get_height() - 20), (back_text.get_width() + 20, 45)), 4)
        else:
            pygame.draw.rect(self.screen, (0, 0, 0), ((self.screen.get_width() - back_text.get_width() - 40, self.screen.get_height() - back_text.get_height() - 20), (back_text.get_width() + 20, 45)), 4)




        # mouse input handel ----------------------------------------------------------------------
        if pygame.mouse.get_pressed()[0]:
            if name_rec.collidepoint(pygame.mouse.get_pos()):
                self.change_input_goal(1)
            if cont_rec.collidepoint(pygame.mouse.get_pos()):
                self.change_input_goal(2)
            if obj_rec.collidepoint(pygame.mouse.get_pos()):
                self.change_input_goal(3)

        return True, False


class Term_Creator_Manager(QuizLoopManager):
    def __init__(self, screen, world_map_h, world_map_m, world_map_s, quiz_info):
        QuizLoopManager.__init__(self, screen, world_map_h, world_map_m, world_map_s, quiz_info)
        self.screen_offset = [0, 70]
        self.new_term = [[], False]
        self.term_name = ""
        self.input_capture.activate()
        self.enter_text = self.font.render("Potvrdit", True, (0, 0, 0))
        self.changes = [False, False, False, False, False]

    def update(self, screen):
        # clear the draw surface
        self.draw_surface.fill((100, 100, 255))
        self.highlight_surface.fill((0, 0, 0, 0))

        # change polygon qualyty based on zoom
        if self.scale < 10:
            self.map_index = 0
        elif self.scale < 60:
            self.map_index = 1
        else:
            self.map_index = 2

        # draw all polygons
        for scaled_polygon, name in self.get_visible_polygons():
            pygame.draw.polygon(self.draw_surface, (100, 155, 100), scaled_polygon)
            pygame.draw.aalines(self.draw_surface, (0, 0, 0), False, scaled_polygon)

        # draw all lines
        for scaled_polygon, name in self.get_visible_lines():
            pygame.draw.aalines(self.draw_surface, (60, 60, 200), False, scaled_polygon)

        # draw all body's of water
        for scaled_polygon, name in self.get_visible_water_bodeys():
            pygame.draw.polygon(self.draw_surface, (60, 60, 220), scaled_polygon)

        # draw all cities/points
        for scaled_point, name, rank, capital in self.get_visible_points():
            if capital:
                pygame.draw.circle(self.draw_surface, (209, 49, 245), scaled_point, 2 + self.map_index * 1.5)
            else:
                pygame.draw.circle(self.draw_surface, (0, 0, 0), scaled_point, 1 + self.map_index / 2)

        for scaled_polygon, name in self.get_visible_custom_polygons():
            pygame.draw.polygon(self.highlight_surface, (100, 100, 100), scaled_polygon)
            pygame.draw.aalines(self.draw_surface, (0, 0, 0), False, scaled_polygon)

        # creating a new term logic
        """
        works like this:
        [[...], False] - list of points + closed bool
        if only one point in list - draw point
        if two or more points in list - draw line ending in mouse
        if the bool is True draw a closed polygon, ignore mouse
        
        """

        # adding point logic
        if pygame.mouse.get_pressed()[0] and self.clicked and pygame.rect.Rect(self.screen_offset, self.draw_surface.get_size()).collidepoint(pygame.mouse.get_pos()):
            self.clicked = False
            pos = list(pygame.mouse.get_pos())
            pos[1] -= self.screen_offset[1]
            if self.new_term[0] and circle_point_collision(pos, 10, self.scale_point(self.new_term[0][0][0], self.new_term[0][0][1])):
                self.new_term[1] = True
            elif not self.new_term[1]:
                pos = self.unscale_point(pos)
                self.new_term[0].append(pos)
        # remove point logic
        if pygame.mouse.get_pressed()[1] and self.clicked and self.new_term[0]:
            self.clicked = False
            if self.new_term[1]:
                self.new_term[1] = False
            else:
                self.new_term[0].pop()

        if not pygame.mouse.get_pressed()[0] and not pygame.mouse.get_pressed()[1]:
            self.clicked = True

        # draw points logic
        if len(self.new_term[0]) == 1:
            pygame.draw.circle(self.draw_surface, (0, 255, 255), self.scale_point(self.new_term[0][0][0], self.new_term[0][0][1]), 5)
        if len(self.new_term[0]) > 1:
            mouse = list(pygame.mouse.get_pos())
            mouse[1] -= self.screen_offset[1]
            if self.new_term[1]:
                pygame.draw.polygon(self.draw_surface, (0, 255, 255), self.scale_points(self.new_term[0]))
            elif circle_point_collision(mouse, 10, self.scale_point(self.new_term[0][0][0], self.new_term[0][0][1])):
                pygame.draw.aalines(self.draw_surface, (0, 255, 255), True, self.scale_points(self.new_term[0]))
            else:
                line = self.new_term[0].copy()

                mouse = self.unscale_point(mouse)
                line.append(mouse)
                pygame.draw.aalines(self.draw_surface, (0, 255, 255), False, self.scale_points(line))


        # fill the screen
        ((160, 160, 170))


        # drawing text box
        self.term_name = self.input_capture.get_text()
        text = self.font.render(self.term_name, True, (0, 0, 0))
        screen.blit(text, (screen.get_width()/2 - text.get_width()/2, 10))

        # drawing enter button
        but_rect = pygame.rect.Rect(10, 10, self.enter_text.get_width() + 20, self.enter_text.get_height() + 10)
        pygame.draw.rect(screen, (120, 100, 100), but_rect)
        screen.blit(self.enter_text, (20, 15))
        if but_rect.collidepoint(pygame.mouse.get_pos()):
            if pygame.mouse.get_pressed()[0]:
                pygame.draw.rect(screen, (100, 100, 200), (10, 10, self.enter_text.get_width() + 20, self.enter_text.get_height() + 10), 4)
                self.save_term()
                self.new_term = [[], False]
                self.term_name = ""
                self.input_capture.activate()
            else:
                pygame.draw.rect(screen, (140, 140, 160),(10, 10, self.enter_text.get_width() + 20, self.enter_text.get_height() + 10), 4)
        else:
            pygame.draw.rect(screen, (0, 0, 0), (10, 10, self.enter_text.get_width() + 20, self.enter_text.get_height() + 10), 4)

        # exit button
        back_text = self.font.render("zpět", True, (0, 0, 0))
        pygame.draw.rect(self.screen, (120, 100, 100), ((self.screen.get_width() - back_text.get_width() - 40, 10), (back_text.get_width() + 20, 45)))
        self.screen.blit(back_text, (self.screen.get_width() - back_text.get_width() - 30, 15))
        if pygame.rect.Rect(((self.screen.get_width() - back_text.get_width() - 40, 10), (back_text.get_width() + 20, 45))).collidepoint(pygame.mouse.get_pos()):
            if pygame.mouse.get_pressed()[0]:
                pygame.draw.rect(self.screen, (100, 100, 200), ((self.screen.get_width() - back_text.get_width() - 40, 10), (back_text.get_width() + 20, 45)), 4)
                return False, self.changes
            else:
                pygame.draw.rect(self.screen, (140, 140, 160), ((self.screen.get_width() - back_text.get_width() - 40, 10), (back_text.get_width() + 20, 45)), 4)
        else:
            pygame.draw.rect(self.screen, (0, 0, 0), ((self.screen.get_width() - back_text.get_width() - 40, 10), (back_text.get_width() + 20, 45)), 4)





        screen.blit(self.draw_surface, self.screen_offset)

        return True, self.changes

    def unscale_point(self, point):
        return (point[0] - self.position[0]) / self.scale, -((point[1] - self.position[1]) / self.scale)

    def save_term(self):
        if len(self.new_term[0]) == 1:  # cities
            dict = {"geometry": tuple(self.new_term[0][0]),
                    "rank": 2,
                    "capital": False
                    }
            with open("maps/High_quality/cities.json", "r") as h:
                data_h = json.load(h)
            with open("maps/Medium_quality/cities.json", "r") as m:
                data_m = json.load(m)
            with open("maps/Low_quality/cities.json", "r") as s:
                data_s = json.load(s)
            with open("maps/terms.json", "r") as t:
                data_t = json.load(t)

            data_s[self.term_name] = dict
            data_m[self.term_name] = dict
            data_h[self.term_name] = dict
            data_t["points"].append(self.term_name)

            with open("maps/High_quality/cities.json", "w") as h:
                json.dump(data_h, h, indent=4)
            with open("maps/Medium_quality/cities.json", "w") as m:
                json.dump(data_m, m, indent=4)
            with open("maps/Low_quality/cities.json", "w") as s:
                json.dump(data_s, s, indent=4)

            with open("maps/terms.json", "w") as t:
                json.dump(data_t, t)
            self.changes[0] = True

        if len(self.new_term[0]) > 1 and self.new_term[1]: # polygons
            self.new_term[0].append(self.new_term[0][0])
            dict = {"geometry": tuple(self.new_term[0])}
            with open("maps/High_quality/custom_polygons.json", "r") as h:
                data_h = json.load(h)
            with open("maps/Medium_quality/custom_polygons.json", "r") as m:
                data_m = json.load(m)
            with open("maps/Low_quality/custom_polygons.json", "r") as s:
                data_s = json.load(s)
            with open("maps/terms.json", "r") as t:
                data_t = json.load(t)

            preprocess_map_data(dict)

            data_s[self.term_name] = dict
            data_m[self.term_name] = dict
            data_h[self.term_name] = dict
            data_t["new_polygons"].append(self.term_name)

            with open("maps/High_quality/custom_polygons.json", "w") as h:
                json.dump(data_h, h, indent=4)
            with open("maps/Medium_quality/custom_polygons.json", "w") as m:
                json.dump(data_m, m, indent=4)
            with open("maps/Low_quality/custom_polygons.json", "w") as s:
                json.dump(data_s, s, indent=4)

            with open("maps/terms.json", "w") as t:
                json.dump(data_t, t)

            self.changes[1] = True

        if len(self.new_term[0]) > 1 and not self.new_term[1]: # lines

            dict = {"geometry": tuple(self.new_term[0])}

            with open("maps/High_quality/lines.json", "r") as h:
                data_h = json.load(h)
            with open("maps/Medium_quality/lines.json", "r") as m:
                data_m = json.load(m)
            with open("maps/Low_quality/lines.json", "r") as s:
                data_s = json.load(s)
            with open("maps/terms.json", "r") as t:
                data_t = json.load(t)

            preprocess_map_data(dict)

            data_s[self.term_name] = dict
            data_m[self.term_name] = dict
            data_h[self.term_name] = dict
            data_t["lines"].append(self.term_name)

            with open("maps/High_quality/lines.json", "w") as h:
                json.dump(data_h, h, indent=4)
            with open("maps/Medium_quality/lines.json", "w") as m:
                json.dump(data_m, m, indent=4)
            with open("maps/Low_quality/lines.json", "w") as s:
                json.dump(data_s, s, indent=4)

            with open("maps/terms.json", "w") as t:
                json.dump(data_t, t)

            self.changes[4] = True

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
