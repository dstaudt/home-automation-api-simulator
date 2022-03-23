import os

with open('device_ids.log','w') as file: pass

from app import app

if __name__ == "__main__":
    app.run()