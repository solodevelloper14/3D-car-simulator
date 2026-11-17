from svgpathtools import svg2paths
import matplotlib.pyplot as plt
import json

SCALE = 5
N = 750

paths, attrs = svg2paths('ring.svg')
path = paths[0]
L = path.length()

dots = []
for i in range(N):
    p = path.point(path.ilength(i / N * L))
    dots.append((p.real, -p.imag))
x0, z0 = dots[0]
dots = [((x - x0) * SCALE, (z - z0) * SCALE) for x, z in dots]
json.dump(dots, open('track.json', 'w'))
print(path.isclosed(), L * SCALE)

plt.plot(*zip(*dots))
plt.axis('equal')
plt.show()