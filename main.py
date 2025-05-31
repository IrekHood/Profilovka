import pygame
import sys
import json
from loop_managers import *
# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 800, 600

# Create the screen
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Setup")

# Colors
WHITE = (255, 255, 255)

# Clock for controlling the frame rate
clock = pygame.time.Clock()

# Load stuff
map_data = json.load(open("maps/World.json", "r"))
scale = 1  # Scale factor for the map
position = (0, 1000)  # Position of the map on the canvas
mouse_pos = None  # Mouse position
MAX_SCALE = 10  # Maximum scale factor
MIN_SCALE = 0.1  # Minimum scale factor
SCALE_STEP = 1.4  # Scale step for zooming in and out

items = json.load(open("maps/learning_sets/mistopis evropa septima.json", "r"))
items = items["items"]


# Main game loop
def main():
    global scale, position, mouse_pos

    # settup managers
    Quiz_M = None
    Menu_M = MenuLoopManager(screen)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

            if event.type == pygame.MOUSEWHEEL:
                if event.y > 0 and not scale * SCALE_STEP > MAX_SCALE:  # Zoom in
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    position = (
                        mouse_x - (mouse_x - position[0]) * SCALE_STEP,
                        mouse_y - (mouse_y - position[1]) * SCALE_STEP,
                    )
                    scale *= SCALE_STEP
                elif event.y < 0 and not scale / SCALE_STEP < MIN_SCALE:  # Zoom out
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    position = (
                        mouse_x - (mouse_x - position[0]) / SCALE_STEP,
                        mouse_y - (mouse_y - position[1]) / SCALE_STEP,
                    )
                    scale /= SCALE_STEP


        for i in pygame.mouse.get_pressed():
            if i == 1:
                if mouse_pos is None:
                    mouse_pos = pygame.mouse.get_pos()
                else:
                    diff = (pygame.mouse.get_pos()[0] - mouse_pos[0], pygame.mouse.get_pos()[1] - mouse_pos[1])
                    position = (position[0] + diff[0], position[1] + diff[1])
                    mouse_pos = pygame.mouse.get_pos()
        for i in pygame.mouse.get_just_released():
            if i == 1:
                mouse_pos = None

        # Fill the screen with white
        screen.fill(WHITE)

        # manage screen
        if Quiz_M:
            Quiz_M.update(scale, position)

        if Menu_M:
            Menu_M.update()

        # Update the display
        pygame.display.flip()

        # Cap the frame rate to 60 FPS
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()