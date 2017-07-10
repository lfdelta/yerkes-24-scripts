from win32com.client import Dispatch
import numpy as np

'''
id=Dispatch('ASCOM.Utilities.Chooser')
id.DeviceType='Focuser'
a=id.Choose(None)
print a
stop
'''

#cam=Dispatch('MaxIm.CCDCamera')
#cam.LinkEnabled=True
#tel=Dispatch("ASCOM.SiTechDll.Telescope")
#tel.Connected=True
foc=Dispatch('ASCOM.OptecTCF_S.Focuser')
foc.Connected=True

foc.Move(3000)
stop


#build targeting model
alt_inital=np.linspace(20,90,10,endpoint=False)
azi_inital=np.linspace(0,360,10,endpoint=False)

targets_azi=[]
targets_alt=[]

for i in azi_inital:
    for j in alt_inital:
        if i<70. or i>290:
            if j<50.:
                pass #do nothing because this is below the horizon limits on the 41"
            else:
                targets_azi.append(i)
                targets_alt.append(j)
        else:
            targets_azi.append(i)
            targets_alt.append(j)
            
for i in range(0,len(targets_azi)):
    print i,targets_alt[i],targets_azi[i]
            

