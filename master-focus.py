
CATALOG = "UCAC3.txt" # filename for catalog of RA and dec for mag 5-8 stars

OBS_LAT = 42.5704 # north latitude in degrees
OBS_LON = -88.5563 # east latitude in degrees

FOC_NAME = "ASCOM.FocusLynx.Focuser"
FOC_GUESS = 6000 # best guess for focuser value
EXP_COUNT = 4 # number of exposures per focuser value to average over



import autofocuser as afoc

# parse command line arguments
parser = argparse.ArgumentParser(description="V curve")
parser.add_argument("-r", "--raw", action="store_true",
                    help="print raw data as it is collected")
parser.add_argument("-p", "--plot", action="store_true",
                    help="plot the curve using matplotlib")
parser.add_argument("-i", "--image", action="store_true",
                    help="export v-curves to disk")
args = parser.parse_args()

# initialize
autofoc = afoc.AutoFocuser(FOC_NAME, FOC_GUESS, EXP_COUNT,
                           args.raw, args.image)
starlist = afoc.Catalog(CATALOG)
if starlist.checkHash():
  quit("Catalog hash table was poorly constructed")

# construct a grid of points in the sky to iterate through
skyGrid = []
for az in range(0, 360, 60):
  for alt in range(40, 90, 10):
    skyGrid.append( (alt, az) )

print "Altitude (deg),Azimuth (deg),Optimal Focuser Step"
for altAz in skyGrid:
  goto = afoc.AAtoRD(altAz[0], altAz[1], OBS_LAT, OBS_LON)
  autofoc.focusAtPoint(starlist.findNearestStar(goto))
  print "%d,%d,%d" % (autofoc.scope.Altitude, autofoc.scope.Azimuth,
                      autofoc.optimalFocus)
