import sys
import asyncio
from loop_managers import *
# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 1920, 1080


# Create the screen
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Pygame Setup")

# Colors
WHITE = (255, 255, 255)

# Clock for controlling the frame rate
clock = pygame.time.Clock()

# Load stuff
map_data_h = json.load(open("maps/World_h.json", "r"))
map_data_m = json.load(open("maps/World_m.json", "r"))
map_data_s = json.load(open("maps/World_s.json", "r"))

# Main game loop
async def main():

    # settup managers
    Quiz_M = None
    Menu_M = MenuLoopManager(screen)
    Creator_M = CreatorLoopManager(screen)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
            if Creator_M:
                Creator_M.input_capture.handle_event(event)
            if Quiz_M:
                Quiz_M.input(event)

        # Fill the screen with white
        screen.fill(WHITE)

        # manage screen
        if Quiz_M:
            Quiz_M.update(screen)
            if not Quiz_M:
                Menu_M = MenuLoopManager(screen)

        if Menu_M:
            v = Menu_M.update(event.y if event.type == pygame.MOUSEWHEEL else 0)
            if v[0] == 1:  # if new quiz button was pressed
                Creator_M.active = True
                Menu_M.active = False 
            elif v[0] == 2:  # if quiz button was pressed
                Quiz_M = QuizLoopManager(screen, map_data_h, map_data_m, map_data_s, v[1])
                Menu_M.active = False

        if Creator_M:
            if not Creator_M.update():
                Creator_M.active = False
                Menu_M = MenuLoopManager(screen)

        # Update the display
        pygame.display.flip()

        # Cap the frame rate to 60 FPS
        clock.tick(60)

        # asyncio
        await asyncio.sleep(0)

    pygame.quit()
    sys.exit()


asyncio.run(main())
