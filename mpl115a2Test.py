# mpl115a2 class by ThreeSixes (https://github.com/ThreeSixes/py-mpl115a2)

from mpl115a2 import mpl115a2
from pprint import pprint

# Set up our magnetometer
baroSens = mpl115a2()


btData = baroSens.getPressTemp()

print("Barometric pressure (kPa): " + str(btData[0]))
print("Temperature (C):           " + str(btData[1]))