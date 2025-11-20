from .funs1 import *
#################################################################################################################
#Adiciones de Jorge
#################################################################################################################
import calendar
from datetime import datetime
import pytz
from math import tan,acos
from numpy import deg2rad,rad2deg

#Determinar la hora de salida y puesta de sol
def calc_sunrs(dec,lat): #Grados
    #Esta funcion falla sobre los circulos polares, donde el sol puede no pasar por el horizonte en ningun momento del dia
    #H=rad2deg(acos(tan(deg2rad(dec))*tan(deg2rad(lat))))/360*24
    try:
        H=rad2deg(acos(tan(deg2rad(dec))*tan(deg2rad(lat))))/360*24
    except:
        H=999
    
    sunr=H
    suns=24-H
    return sunr,suns

#Determinar la fecha juliana del inicio del MY
def MY2julian(MY):
    jday_vals = [-16336.044076, -15649.093471, -14962.0892946, -14275.0960023, -13588.1458658, -12901.1772635, -12214.2082215, -11527.2637345, -10840.2842249, -10153.2828749, -9466.3114025, -8779.3356111, -8092.3607738, -7405.4236452, -6718.4615347, -6031.4574604, -5344.4876509, -4657.5318339, -3970.5474528, -3283.5848372, -2596.6329362, -1909.6426682, -1222.6617049, -535.7040268, 151.2736522, 838.2369682, 1525.1834712, 2212.1799182, 2899.1848518, 3586.1403058, 4273.1024234, 4960.0765368, 5647.0207838, 6333.986502, 7020.9875066, 7707.9629132, 8394.9318782, 9081.9102062, 9768.8526533, 10455.8028354, 11142.8050514, 11829.7873254, 12516.7417734, 13203.725449, 13890.6991502, 14577.6484912, 15264.6324865, 15951.6217969, 16638.5798914, 17325.5517216, 18012.5209097, 18699.4628887, 19386.4443201, 20073.4534421, 20760.4152811, 21447.3696661, 22134.3466251, 22821.2966642, 23508.2529432, 24195.2539572, 24882.2400506, 25569.2081296, 26256.1902459, 26943.1429481, 27630.0847446, 28317.0793316, 29004.0710936, 29691.0238241, 30377.9991486, 31064.9784277, 31751.9249377, 32438.896907, 33125.8902412, 33812.8520242, 34499.8183442, 35186.7944595, 35873.740573, 36560.7112423, 37247.7247318]

    year_vals = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79]

    return jday_vals[int(MY-1)]

#Determinar con una cierta precision la fecha terrestre correspondiente a un MY,Ls
def MYLs2julian(MY,Ls,umbral=0.0001):
    j1=MY2julian(int(MY))
    j2=MY2julian(int(MY)+1)
    
    
    #Determinar el Ls
    D=(j2-j1)/2
    j=j1+D
    while D>umbral:
        resLs=Mars_Ls(j)
        D=D/2
        if resLs>Ls:
            j=j-D
        else:
            j=j+D
    return j

#Determinar la fecha j2000 mas cercana al momento en que es la LTST que se pide en el Ls y ubicacion que se pide
def MYLsLTST2julian(MY,Ls,LTST,lon):
    sdr=1.02749125 #Solar Day Ratio, copiado de Allison et al. 2000
    
    j=MYLs2julian(MY,Ls,umbral=0.0001) ####umbral=0.1
    LTST2=Local_True_Solar_Time(lon,j)
    
    diff=LTST2-LTST
    j=j-diff/24*sdr
    #Ver si es mas cercano el anterior o el siguiente, y retornar el que tenga el Ls mas cercano
    j1=j
    Ls1=Mars_Ls(j1)
    j2=j+sdr
    Ls2=Mars_Ls(j2)
    if abs(Ls1-Ls)<abs(Ls2-Ls):
        return j1
    else:
        return j2

#Conversion de objeto datetime a j2000 terrestrial time
def dt2j2000_ott(dt):
    mil=dt2mills(dt)
    jdut = julian(mil)
    jday_tt = julian_tt(jdut)
    j2000_ott = j2000_offset_tt(jday_tt)
    return j2000_ott


def j2000_ott2dt(j2000_ott):
    jday_tt=tt_j2000_offset(j2000_ott)
    #print jday_tt
    jdut=tt_julian(jday_tt)
    #print jdut
    timestamp=(jdut-2440587.5)*86400
    #print timestamp
    return datetime.fromtimestamp(timestamp,pytz.UTC)

#A: PEQUEÑA MODIFICACIÓN REALIZADA PARA TRABAJAR CON MILISEGUNDOS
# =============================================================================
# =============================================================================
def dt2mills(dt):
    milliseconds=int(dt.microsecond/1000)
    return calendar.timegm(dt.timetuple())*1000 + milliseconds
# =============================================================================
# ============================================================================= 

   
#Funciones opuestas a las equivalentes del otro archivo
def tt_j2000_offset(j2000_ott):
    return (j2000_ott + j2000_epoch())

def tt_julian(jdtt):
    jday_utc=jdtt - utc_to_tt_offset(jdtt)/86400.
    return jday_utc
