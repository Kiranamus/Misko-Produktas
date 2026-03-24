import pyogrio
from app.config import GDB_VMT, GDB_NATURA

def show(path):
    print(f"\nGDB: {path}")
    layers = pyogrio.list_layers(path)
    print(layers)

if __name__ == "__main__":
    show(GDB_VMT)
    show(GDB_NATURA)