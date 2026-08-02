import pygame
from pygame.locals import *

try:
    from .wall import Wall
    from .bat import Bat, ControlScheme
    from .ball import Ball
    from .score import Score
except ImportError:  # Allow running this file directly from the pong directory.
    from games.pong.wall import Wall
    from games.pong.bat import Bat, ControlScheme
    from games.pong.ball import Ball
    from games.pong.score import Score


class PongGame:
    def __init__(self, size):
        self.size = size
        self.background = pygame.Surface(size)  # make a background surface
        self.background = self.background.convert()
        self.background.fill((0, 0, 0))

        font = pygame.font.Font(None, 24)

        self.score = Score(font)

        self.walls = [Wall((5, 5), (size[0] - 10, 10)),
                      Wall((5, size[1] - 10), (size[0] - 10, size[1] - 5))]

        self.bats = []

        control_scheme_1 = ControlScheme()
        control_scheme_1.up = K_w
        control_scheme_1.down = K_s

        control_scheme_2 = ControlScheme()
        control_scheme_2.up = K_UP
        control_scheme_2.down = K_DOWN

        self.bats.append(Bat((5, int(size[1]/2)), control_scheme_1, self.size))
        self.bats.append(Bat((size[0] - 10, int(size[1]/2)), control_scheme_2, self.size))

        self.ball = Ball((int(size[0]/2), int(size[1]/2)))

    def process_event(self, event):
        for bat in self.bats:
            bat.process_event(event)

    def update(self, time_delta):
        for bat in self.bats:
            bat.update(time_delta)

        self.ball.update(time_delta, self.bats, self.walls)

        if self.ball.position[0] < 0:
            self.ball.reset()
            self.score.increase_player_2_score()
        elif self.ball.position[0] > self.size[0]:
            self.ball.reset()
            self.score.increase_player_1_score()

    def draw(self, surface):
        surface.blit(self.background, (0, 0))

        for wall in self.walls:
            wall.render(surface)

        for bat in self.bats:
            bat.render(surface)

        self.ball.render(surface)
        self.score.render(surface, self.size)


def main():
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    clock = pygame.time.Clock()
    game = PongGame((640, 480))

    running = True
    while running:
        time_delta = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            else:
                game.process_event(event)

        game.update(time_delta)
        game.draw(screen)
        pygame.display.flip()

    pygame.quit()


if __name__ == '__main__':
    main()
