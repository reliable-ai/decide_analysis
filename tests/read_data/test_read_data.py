from src.read_data.read_data import read_data


def test_read_data():
    df = read_data(1000)

    rows, cols = df.shape

    assert rows == 1000
    assert cols > 0
