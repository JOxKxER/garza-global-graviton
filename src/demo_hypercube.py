import logging
import numpy as np
from src.core import transform_4d_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# 1. Generate 16 vertices of a 4D hypercube (±1, ±1, ±1, ±1)
vertices = np.array([
    [x, y, z, w]
    for x in (-1, 1)
    for y in (-1, 1)
    for z in (-1, 1)
    for w in (-1, 1)
], dtype=np.float64)

logging.info(f"Generated 4D Hypercube with {len(vertices)} vertices.")

# 2. Rotate by 45 degrees along the X-W plane
theta = np.pi / 4
rotated_vertices = transform_4d_dataset(vertices, theta=theta, plane="xw")

logging.info(f"Sample Original Vertex 0: {vertices[0]}")
logging.info(f"Sample Rotated  Vertex 0: {np.round(rotated_vertices[0], 3)}")
