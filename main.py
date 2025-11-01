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

def load_data(directory, changes=None, out=None):
    if out is None:
        out = {}
    if changes is None:
        changes = [True, True, True, True, True]
    if changes[0]:
        cities = json.load(open(f"maps/{directory}/cities.json", "r"))
        out["points"] = cities
    if changes[1]:
        custom_polygons = json.load(open(f"maps/{directory}/custom_polygons.json", "r"))
        out["new_polygons"] = custom_polygons
    if changes[2]:
        lakes = json.load(open(f"maps/{directory}/lakes.json", "r"))
        out["blue_polygons"] = lakes
    if changes[3]:
        polygons = json.load(open(f"maps/{directory}/polygons.json", "r"))
        out["polygons"] = polygons
    if changes[4]:
        rivers = json.load(open(f"maps/{directory}/rivers.json", "r"))
        out["lines"] = rivers
    return out



# Main game loop
async def main():

    # Load stuff
    map_data_h = load_data("High_quality")
    map_data_m = load_data("Medium_quality")
    map_data_s = load_data("Low_quality")

    # settup managers
    Quiz_M = None
    Menu_M = MenuLoopManager(screen)
    Creator_M = CreatorLoopManager(screen)
    Term_M = None

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and Menu_M:
                    running = False
            if Creator_M:
                Creator_M.input_capture.handle_event(event)
                Creator_M.input(event)
            if Quiz_M:
                Quiz_M.input(event)
            if Term_M:
                Term_M.input(event)

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

        if Term_M:
            out = Term_M.update(screen)
            if not out[0]:
                Creator_M.active = True
                Creator_M.objects = json.load(open("maps/terms.json", 'r'))
                Term_M.active = False
                # reload what is needed stuff
                map_data_h = load_data("High_quality", out[1], map_data_h)
                map_data_m = load_data("Medium_quality", out[1], map_data_m)
                map_data_s = load_data("Low_quality", out[1], map_data_s)

        if Creator_M:
            out = Creator_M.update()
            if not out[0]:
                if out[1]:
                    Creator_M.active = False
                    Term_M = Term_Creator_Manager(screen, map_data_h, map_data_m, map_data_s, None)
                else:
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
