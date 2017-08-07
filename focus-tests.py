
CATALOG = "UCAC3.txt"
OBS_LAT = 42.5704
OBS_LON = -88.5563
SCOPE_NAME = "ASCOM.SiTechDll.Telescope"
FOC_NAME = "ASCOM.FocusLynx.Focuser"
FOC_GUESS = 6000
EXP_COUNT = 4

import autofocuser as af
import time

afoc = af.AutoFocuser(SCOPE_NAME, FOC_NAME, FOC_GUESS, EXP_COUNT, False, False)

# potential replacements
def t1():
  print "\nTEST 1: POTENTIAL REPLACEMENTS"
  print "getUTC: %s\nASCOM:  %s\n" % (af.getUTC(), afoc.scope.UTCDate)
  #print "getLST: %s\nASCOM:  %s\n" % (af.getLST(OBS_LON), afoc.scope.SiderealTime)
  print "OBS_LAT: %f\nASCOM:   %f\n" % (OBS_LAT, afoc.scope.SiteLatitude)
  print "OBS_LON: %f\nASCOM:   %f\n" % (OBS_LON, afoc.scope.SiteLongitude)
  print "Temp: %f" % afoc.focuser.Temperature

# skygrid coordinate order
def t2():
  print "\nTEST 2: SKYGRID COORDINATE ORDER"
  skyGrid = []
  for az in range(0, 360, 60):
    for alt in range(40, 90, 10):
      skyGrid.append( (alt, az) )
  for coord in skyGrid:
    print coord

# single autofocus, raw and image
def t3(goto=None):
  print "\nTEST 3: SINGLE AUTOFOCUS, RAW AND IMAGE"
  print "PARAMETER:", goto
  afoc.raw = afoc.imgOut = True
  afoc.focusAtPoint(goto)
  afoc.report()
  afoc.raw = afoc.imgOut = False

# setupField from various initial exposures
def t4():
  print "\nTEST 4: SETUPFIELD FROM VARIOUS INITIAL EXPOSURES"
  for dt in [0.1, 0.5, 1.0, 3.0]:
    for i in range(3):
      print "%.1f SECOND" % dt
      afoc.expTime = dt
      afoc.setupField()
      print "FINAL EXPTIME: %.3f\n" % afoc.expTime
  
# time for single focusAtPoint
def t5():
  print "\nTEST 5: TIME FOR SINGLE FOCUSATPOINT"
  t0 = time.time()
  afoc.focusAtPoint()
  print "Single focus: %.3fs" % (time.time() - t0)

# AAtoRD confirmation
def t6():
  print "\nTEST 6: AATORD CONFIRMATION"
  print "AAtoRD: %s\nASCOM: %s" % (af.AAtoRD(afoc.scope.Altitude,
                                             afoc.scope.Azimuth,
                                             afoc.scope.SiteLatitude,
                                             afoc.scope.SiteLongitude),
                                   af.Coordinate(afoc.scope.RightAscension*15,
                                                 afoc.scope.Declination))
