##################################
#Clases marstime, climarstime, climarstimedelta
#Para construir un sistema equivalente al estandar datetime
##################################

from datetime import datetime
from numpy import rad2deg,deg2rad
from .funs1 import *
from .funs2 import *

class marstime:
    def __init__(self,dt,lon=None,lat=None): #longitud (este) y latitud en grados
        self.dt=dt #datetime
        self.j2000_ott=dt2j2000_ott(self.dt)
        
        #Parametros de la fecha marciana
        self.MY=Mars_Year(self.j2000_ott)
        self.Ls=Mars_Ls  (self.j2000_ott)
        self.MCT=Coordinated_Mars_Time (self.j2000_ott)
        
        self.MSD=Mars_Solar_Date(self.j2000_ott)
        
        #Parametros del sol
        self.compute_solar_params()
        
        #Parametros asociados a una posicion areografica
        self.set_lonlat((lon,lat))
    
    def set_lon(self,lon):
        if lon!=None:
            self.compute_longitude_params(lon)
        else:
            self.lon=None
            self.lonp=False
    def set_lat(self,lat):
        if self.lonp and lat!=None:
            self.compute_latitude_params(lat)
        else:
            self.lat=None
            self.latp=False
    def set_lonlat(self,lonlat):
        lon,lat=lonlat
        self.set_lon(lon)
        self.set_lat(lat)
        
    def compute_solar_params(self):
        self.sun_lon=west_to_east(subsolar_longitude(self.j2000_ott))
        self.sun_dec=solar_declination (self.Ls)
        self.sun_dist=heliocentric_distance(self.j2000_ott)

    def compute_longitude_params(self,lon):
        self.lon=lon
        self.LMST=Local_Mean_Solar_Time(east_to_west(self.lon), self.j2000_ott)
        self.LTST=Local_True_Solar_Time(east_to_west(self.lon), self.j2000_ott)
        self.lonp=True

    def compute_latitude_params(self,lat):
        self.lat=lat
        self.sun_alt=solar_elevation(self.lon, self.lat, self.j2000_ott)
        self.sun_az=solar_azimuth(self.lon, self.lat, self.j2000_ott)
        #print self.sun_dec,self.lat
        self.sunr,self.suns=calc_sunrs(self.sun_dec,self.lat)
        self.latp=True
            
    #Funciones asociadas: operaciones: marstimedelta,formateo de fecha a string, conversion a string
    def __str__(self):
        if not self.lonp:
            return 'MY '+str(int(self.MY))+' Ls '+str(round(self.Ls,1))+' MCT: '+str(round(self.MCT,2))
        else:
            return 'MY '+str(int(self.MY))+' Ls '+str(round(self.Ls,1))+' LTST(lon'+str(round(self.lon,0))+'E): '+str(round(self.LTST,3))
    
    def __sub__(self,other):
        return self.dt-other.dt
                        

#Clase de tiempo climatico, implica que lo mas importante es el Ls y el LTST
#Si se fija un MY y una longitud, el Ls se reajusta para que coincida
class climarstime:
    def __init__(self,MY=None,Ls=None,LTST=None,lon=None,lat=None,fitLs=False): #longitud (este) y latitud en radianes
        #Fijar parametros temporales
        self.MY=MY
        self.Ls=Ls
        self.LTST=LTST
        
        #ubicacion
        self.lon=lon
        self.lat=lat
        
        #Cuestiones de coherencia entre variables: Si se fija MY, Ls, LTST, y lon, Ls puede tener un valor realista
        self.fitLs=fitLs #Si debe ajustarse el Ls para lograr coherencia
        self.fitedLs=False
        self.check_fixLs()#Ajustar el Ls si procede
    
    #Devuelve True cuando estan fijados MY,Ls,LTST, y lon, de forma que para que sea coherente hay que hacer un reajuste en el Ls
    def fitableLs(self):
        if not (None in [self.MY,self.Ls,self.LTST,self.lon]):
            return True
        else:
            return False
    
    def check_fixLs(self):
        if self.fitLs and self.fitableLs(): #Si hay que ajustar el Ls
            self.fit_Ls()
            
    #Ajuste del Ls para que se corresponda con un tiempo y ubicacion real
    #Asume que todo esta en orden para poder hacerlo, eso implica que no debe ser llamado externamente
    #En su lugar se debe llamar a check_fitLs()
    def fit_Ls(self):
            j=MYLsLTST2julian(self.MY,self.Ls,self.LTST,self.lon)
            self.dt=j2000_ott2dt(j)
            self.marstime=marstime(self.dt,lon=self.lon,lat=self.lat)
            self.Ls=self.marstime.Ls
    
    #Seteo de variables temporales internas
    def set_MY(self,MY):
        self.MY=MY
        self.check_fixLs()
    def set_Ls(self,Ls):
        self.Ls=Ls
        self.check_fixLs()
    def set_LTST(self,LTST):
        self.LTST=LTST
        self.check_fixLs()
    def set_lon(self,lon):
        self.lon=lon
        self.check_fixLs()
    def set_lat(self,lat):
        self.lat=lat
        self.check_fixLs()
    
    #Diferencia
    def __sub__(self,other):
        return climarstimedelta.fromDeltas(self,other)
            
class climarstimedelta:        
    def __init__(self,MY,Ls,Hdiff,typ='fixlon',lon=None):
        self.MY=MY
        self.Ls=Ls
        
        self.fixlon=False
        self.LTST=None
        self.planetary=False
        self.MCT=None
        
        if typ=='fixlon':
            self.fixlon=True
            self.LTST=Hdiff
            self.lon=lon
        else:
            self.planetary=True
            self.MCT=Hdiff
    
    @classmethod
    def fromDeltas(self,climarstime1,climarstime2):
        if climarstime1.MY!=None and climarstime2.MY!=None:
            MY=climarstime1.MY-climarstime2.MY
        else:
            MY=None
            
        Ls=climarstime1.Ls-climarstime2.Ls
        
        if climarstime1.lon==climarstime2.lon:
            typ='fixlon'
            Hdiff=climarstime1.LTST-climarstime2.LTST
            lon=climarstime1.lon
        else:
            typ='planetary'
            Hdiff=MCT=climarstime1.MCT-climarstime2.MCT
            lon=None
            
        return climarstimedelta(MY,Ls,Hdiff,typ,lon)
        
        
            
            
            

######################################################################
#NOTA. El problema para definir esto reside en dos aspectos diferenciados:
#   1. No hay un calendario marciano suficientemente claro
#   2  Mi interes es estudiar el clima, y entonces los saltos de tiempos que interesan no son claros, dependen de la epoca del ano, etc. porque la LTST no varia igual de un dia a otro.
#Puede servir como inspiracion el sistema del MCD: se puede fijar (anyo), Ls, y hora local, que es la que luego predomina. Podria ser interesante a efectos del clima definir una clase de fecha marciana dentro del anyo, sin entrar al anyo concreto.
          
#Otro punto a tener en cuenta es la necesidad de poder dar la hora local para una cierta ubicacion en funcion de la de otra, para ello es importante el uso de una hora universla, sea marciana o con base en UTC. Esto sirve mas que nada para hacer graficas espaciales, se puede consultar el MCD usando fechas terrestres o se pueden usar fechas marcianas con un sistema asi    

#Esta clase busca ser analoga a datetime, el problema es que el calendario marciano no esta establecido con la precision adecuada, hay una inconexion entre el Ls y los soles, y el Ls no es lineal con el tiempo. Estas diferencias implican entre otras cosas que la clase no se puede basar en el objeto timedelta de forma sencilla (entre otras cosas porque el Ls no es lineal)
#La clase tiene varios usos potenciales
#   *Sustraer entre si objetos marstime
#   *Construir objetos marstime a partir de otros
#La cuestion es que a la hora de construir nuevos objetos marstime, es posible que queramos un Ls identico, o una LTST identica y un Ls cercano, y ahi es donde surgen las dificultades
#La solucion es que la forma de hacer las operaciones dependa de si hay un dH definido o no. Si no hay uno definido, se entiende que las operaciones en Ls son precisas, si no, se entiende que las operaciones deben ser precisas en hora local (es decir, de forma global, en longitud subsolar), y entonces el dLs se adapta
#########################################################################
    
        
        
        

        
