"""Original vector production line: input, current memory, output."""
import math
import pygame
from engine import display
from ui import mix, panel, robot, text

TYPE_COLORS = {'int': 'mint', 'float': 'blue', 'string': 'accent', 'bool': 'danger'}


def background(surface, colors, tick):
    surface.fill(colors['bg'])
    for index in range(55):
        x, y = (index * 193 + 47) % 1440, (index * index * 71 + 13) % 900
        pygame.draw.circle(surface, colors['grid'], (x, y), 1 + (index % 7 == 0))


def icon(size=256):
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surface, '#142438', (size // 2, size // 2), size // 2 - 3)
    pygame.draw.line(surface, '#65dfc5', (size * .15, size * .52), (size * .85, size * .52), max(2, size // 24))
    for index, color in enumerate(('#65dfc5', '#8bbfff', '#ffd078')):
        rect = pygame.Rect(size * (.12 + index * .29), size * .35, size * .18, size * .32)
        panel(surface, rect, color, radius=max(2, size // 32))
    return surface


def conveyor(surface, rect, colors, tick, frame=None, progress=1, language='Python'):
    panel(surface, rect, colors['panel'], colors['border'], 18)
    centers = [rect.x + rect.width * ratio for ratio in (.14, .50, .86)]
    top = rect.y + 14
    width = rect.width * .25
    for index, (name, subtitle, color) in enumerate([('INGRESSI', 'un dato alla volta', 'accent'), ('MEMORIA', 'il valore attuale', 'mint'), ('USCITE', 'una traccia che resta', 'blue')]):
        box = pygame.Rect(centers[index] - width / 2, top, width, 55)
        panel(surface, box, colors['card'], colors[color], 9)
        text(surface, name, (centers[index], top + 17), 15, colors[color], True, 'center')
        text(surface, subtitle, (centers[index], top + 39), 12, colors['muted'], anchor='center')
        if index < 2:
            x = (centers[index] + centers[index + 1]) / 2
            pygame.draw.polygon(surface, colors['border'], [(x - 8, top + 20), (x + 6, top + 28), (x - 8, top + 36)])
    y = rect.bottom - 18
    pygame.draw.line(surface, colors['border'], (rect.x + 25, y), (rect.right - 25, y), 4)
    for i in range(22):
        x = rect.x + 28 + ((i * (rect.width - 56) / 22 + tick * 12) % (rect.width - 56))
        pygame.draw.circle(surface, colors['muted'], (round(x), y + 2), 2)
    start, end = centers[0], centers[1]
    if frame and not frame.target:
        start, end = centers[1], centers[2]
    elif frame and frame.before is not None:
        start, end = centers[1] - 55, centers[1] + 55
    t = max(0, min(1, progress))
    x = start + (end - start) * (t * t * (3 - 2 * t))
    robot(surface, (x, y - 17), .57, tick=tick)
    if frame and frame.after:
        item = frame.after
        label = display(item, language)
        if len(label) > 14:
            label = label[:11] + '…'
        left = x - 177 if x + 177 > rect.right - 10 else x + 27
        panel(surface, pygame.Rect(left, y - 41, 150, 33), colors['bg'], colors[TYPE_COLORS[item.kind]], 7)
        text(surface, label, (left + 9, y - 33), 16, colors[TYPE_COLORS[item.kind]], True)
