import pytest
import numpy as np

def test_placeholder_logic():
    data = np.array([1, 2, 3])
    result = data * 2
    np.testing.assert_array_equal(result, np.array([2, 4, 6]))
