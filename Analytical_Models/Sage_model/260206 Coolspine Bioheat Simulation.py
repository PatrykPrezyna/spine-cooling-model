# -*- coding: utf-8 -*-
"""
Created on Thu Oct 24 14:13:44 2024

@author: Jack Hale
"""

import numpy as np
from scipy.optimize import root
import scipy as sp
import matplotlib.pyplot as plt

import pandas as pd


#####################
# Class definitions #
#####################

class catheter:
   def  __init__(self, Ti, To, Di, Do, v, p, Cp, u, k):
        self.Ti = Ti+273.15 # Temperature of saline inflow converted to k
        self.To = To+273.15 # Temperature of saline outflow converted to k
        self.Di = Di*0.0254 # Inner diameter of catheter converted to m
        self.Do = Do*0.0254 # Outer diameter of catheter converted to m
        self.r1 = self.Do/2
        self.p = p # Density of fluid through catheter, assumes given in kg/m^3
        self.m = calculate_m(v, p) # calculates the flow rate of the catheter assuming v is given in mL/min
        self.v = v # Captures the velocity of saline into the catheter object
        self.Cp = Cp # heat capacity of saline
        self.u = u # Dynamic viscocity of the saline
        self.k = k # Thermal Conductivity of Saline
        self.Pr = 4 # Prandlt number for the saline
        
        self.Q = calc_Q(self.m, Cp, self.To, self.Ti) # Calculate Heat Rate to raise temperature of saline
        self.Tc = lmtd(self.Ti, self.To) # Calculate log mean temperature difference of saline
        
        self.Red = reynolds_through_annulus(self.m, self.Do, self.Di, self.u) # assumes annular flow, inlet is central lumen with return annulus
        self.h_conv = calculate_h(self.Red, self.k, (self.Do-self.Di), self.Pr) # Attempts to calculate convection coefficient. Doesn't currently work
        
class body:
    def __init__(self, Tb, k, q_gen, pb, cb, wb):
        self.Tb = Tb+273.15 # Assumes body temperature is entered in C
        self.k = k # Assumes thermal conductivity entered in W/m*k
        self.q_gen = q_gen # Sets the heat generation within the body
        self.pb = pb # Density of the blood fluid
        self.Cb = cb # Specific heat capacity of the blood fluid
        self.wb = wb # Perfusion rate of the blood
        
    def operation(self, catheter, L):
        self.catheter = catheter # Catheter is inserted into the body
        self.L = L/100 # Sets how much of the catheter is inserted into the body. Assumes entered in cm. Converts to m.
        
        self.catheter_area = 2*np.pi*catheter.r1*self.L+ np.pi*catheter.r1**2
        self.flux = catheter.Q/(self.catheter_area)
        
    
    
    def known_Ts(self,r2 = 0.05,n=100):
        # Stores temperature distribution from catheter assuming catheter surface temperature is known
        x = np.linspace(self.catheter.r1, r2)
        temps = steady_bioheat_known_Ts(x, self.catheter.r1, self.pb, self.Cb, self.wb, self.k, self.Tb, self.q_gen, self.catheter.Tc)
        self.known_Ts_dist  = generate_df(x, temps)
        
    def known_Ts_at_r(self, r):
        # Returns temperature at r position assuming catheter surface temperature is known
        return steady_bioheat_known_Ts(r, self.catheter.r1, self.pb, self.Cb, self.wb, self.k, self.Tb, self.q_gen, self.catheter.Tc)
        
    def known_Q(self,r2 = 0.05,n=100):
        # Stores tempearture distribution from catheter assuming heat energy transfer is known
        x = np.linspace(self.catheter.r1, r2)
        temps = steady_bioheat_known_Q(x, self.catheter.r1, -self.flux, self.pb, self.Cb, self.wb, self.k, self.Tb, self.q_gen)
        self.known_Q_dist  = generate_df(x, temps)
    
    def known_Q_at_r(self, r):
        # Returns temperature at r position assuming heat energy transfer is known
        return steady_bioheat_known_Q(r, self.catheter.r1, -self.flux, self.pb, self.Cb, self.wb, self.k, self.Tb, self.q_gen)
        
    
    def known_h(self, r2 = 0.05, n=100):
        # Stores temperature distribution assuming heat convection coefficient is known
        x = np.linspace(self.catheter.r1, r2)
        temps = steady_bioheat_convection_boundary(x, self.catheter.r1, self.pb, self.Cb, self.wb, self.k, self.Tb, self.q_gen, self.catheter.Tc, self.catheter.h_conv)
        self.known_h_dist  = generate_df(x, temps)
        
    def known_h_at_r(self,r):
        # Returns temperature at r position assuming heat convection coefficient is known
        return steady_bioheat_convection_boundary(r, self.catheter.r1, self.pb, self.Cb, self.wb, self.k, self.Tb, self.q_gen, self.catheter.Tc, self.catheter.h_conv)
        
    def known_Ts_avg_temp(self, r1, r2, n=500):
        # Calculates average temperature between two radial positions assuming catheter surface temperature is known
        spine = np.linspace(r1, r2, n)
        temp = steady_bioheat_known_Ts(spine, self.catheter.r1, self.pb, self.Cb, self.wb, self.k, self.Tb, self.q_gen, self.catheter.Tc)
        return np.mean(temp)
    def known_Q_avg_temp(self, r1, r2, n=500):
        # Calculates average temperature between two radial positions assuming  heat energy transfer is known
        spine = np.linspace(r1, r2, n)
        temps = steady_bioheat_known_Q(spine, self.catheter.r1, -self.flux, self.pb, self.Cb, self.wb, self.k, self.Tb, self.q_gen)
        return np.mean(temps)
    def known_Q_vary_flow(self, r1, r2, v1, v2, n_r=500, n_v = 100):
        # sweeps saline flow rate to evaluate average spine temperature at different flow rates
        spine = np.linspace(r1, r2, n_r)
        speeds = np.linspace(v1, v2, n_v)
        m = calculate_m(speeds, self.catheter.p)
        Q = calc_Q(m, self.catheter.Cp, self.catheter.To, self.catheter.Ti)/self.catheter_area
        temps = np.zeros(n_v)
        for i, flux in enumerate(Q):
            temps[i] = np.mean(steady_bioheat_known_Q(spine, self.catheter.r1, -flux, self.pb, self.Cb, self.wb, self.k, self.Tb, self.q_gen))
        return pd.DataFrame({"Speed (mL/min}" : speeds, "Spine Temp (K)" : temps, "Spine Temp (C)" : temps-273.15})
        

#############
# Functions #
# ###########

def generate_df(distance, temps):
    return pd.DataFrame({"Distance" : distance*100, "Temperature" : temps-273.15})

def calculate_m(v, p):
    # Inputs density and velocity in kg/m^3 and mL/min and outputs mass flow rate kg/s
    return v*10**-6 * p / 60

def lmtd(Ti, To):
# Calculate log mean temperature difference
    if (Ti <= 0) or (To <= 0):
        #convert to kalvin if dealing with negative numbers. Or else it returns the same units
        Ti = Ti+273.15
        To = To+273.15
    return (To-Ti)/(np.log(To)-np.log(Ti))

def calc_Q(m, Cp, To, Ti):
    # Calculate total heat rate given mass flow rate, and input and output temps
    return m*Cp*(To-Ti)





def steady_bioheat_known_Ts(r,r1, pb, Cb, wb, k, Tb, Q_met, Ts):
    # Solves bioheat equations with known surface temperature of catheter as boundary condition
    B_s = pb*Cb*wb/k

    B= np.sqrt(B_s)
    T_inf = Tb +Q_met/(pb*Cb*wb)
    return T_inf + (Ts-T_inf)*(sp.special.kn(0, B*r )/sp.special.kn(0,B*r1) )


def steady_bioheat_known_Q(r, a, q_in, pb, Cb, wb, k, Tb, Q_met):
    # Solves bioheat equations with known heat flux at catheter boundary
    B_s = pb*Cb*wb/k
    S = Q_met/k
    B= np.sqrt(B_s)
    return Tb + S/B_s + (q_in/(k*B*sp.special.kn(1,B*a)))*sp.special.kn(0, B*r)


def reynolds_through_annulus(m, Do, Di, u):
    # m is mass flow rate kg/s
    # Do is outer diameter of epidural space
    # Di is inner diameter of epidural space (OD of spinal cord)
    # u is the dynamic viscocity
    
    Red = 4*m/(np.pi*(Do-Di)*u)
    return Red

def nusseult_number(Red, Pr):
    # Calcualted nusseult number for given fluid flow
    if (Pr>0.5) and (Pr<2000):
        if (Red>3000) and (Red<5*10**6):
            f = calculate_friction_factor(Red)
            Nud = ((f/8)*(Red-1000)*Pr)/(1+12.7*(f/8)**0.5*(Pr**(2/3)-1))
            return Nud
        else:
            print("Reynolds Number is outside of the permissible range for nusseult assumptions")
            print("Assuming laminar flow for Nusseult Calculation")
            return nusseult_number_laminar_pipe()
    else:
        print("Prandlt Number is outside of the permissible range for nusseult assumptions")
        return nusseult_number_laminar_pipe()
   
def nusseult_number_laminar_pipe():
    return 5

def calculate_friction_factor(Red):
    if (Red>3000) and (Red<5*10**6):
        f = (0.790*np.log(Red)-1.64)**-2
        return f
    else:
        print(f"Friction factor assumption doesn't work for Reynolds number {Red}")

def steady_bioheat_convection_boundary(r, a, pb, Cb, wb, k, Tb, Q_met, Ts, h_conv):
    # Solves bioheat equations with known heat flux at catheter boundary
    B_s = pb*Cb*wb/k
    S = Q_met/k
    B= np.sqrt(B_s)
    C = h_conv*(Ts-Tb-S/B_s)/(k*B*sp.special.kn(1,B*a)+h_conv*sp.special.kn(0,B*a))
    return Tb + S/B_s + C*sp.special.kn(0, B*r)

def calculate_h(Red, k, D, Pr):
    # Calculated convection heat transfer for flow over tube
    Nud = nusseult_number(Red, Pr)
    h = Nud*k/D
    return h


##############
# Simulation #
##############

# Establish initial test catheter
catheter = catheter(Ti = 0, # Input temp in C
                    To = 15, # Output temp in C
                    Di = 0.05, # Inner diameter in In.
                    Do = 0.081, # Outer diameter in In
                    v = 20, # velocity of saline in mL/min
                    p = 1000, # density of saline in kg/m^3
                    Cp = 3400,# Heat capacity of the saline
                    u = 0.001, # Dynamic Viscosity
                    k=0.6) # Thermal conductivity of saline

patient = body(Tb = 37, # Body temp in C
               k = 0.5, # Heat conductivity of tissue (estimate)
               q_gen = 700,# Heat generation in tissue (Estimate)
               cb=3600, # Specific heat capacity of the blood
               pb=1000, # Density of tissue fluid
               wb=0.005) # Perfusion rate of tissue fluid



patient.operation(catheter,L = 30) # Inserts catheter 30 cm into patient
# Calculates temperature distribution for all three bioheat equation boundary conditions for comparison
patient.known_Ts(r2 = 0.025, n=300)
patient.known_Q(r2 = 0.025, n=300)
patient.known_h(r2 = 0.025, n=300)


spine_position = (0.002, 0.035) # Approximate spine position from catheter. in meters
# Calculates average spine temperature for two different boundary conditions
Avg_Ts = patient.known_Ts_avg_temp(spine_position[0], spine_position[1])-273.15
Avg_Q = patient.known_Q_avg_temp(spine_position[0], spine_position[1])-273.15

# Sweeps flow rates in mL/min to evaluate temperature changes
test = patient.known_Q_vary_flow(spine_position[0], spine_position[1], 20, 100, n_v=30)

# Distances from catheter to evaluate in meters
distances = [0.005,0.0075, 0.01, 0.0125, 0.015, 0.0175, 0.02, 0.025]

# Generates arrays for easy comparison of the three bioheat solutions with different boundary conditions
Ts = np.zeros(len(distances))
Q = np.zeros(len(distances))
h = np.zeros(len(distances))
for i, r in enumerate(distances):
    Ts[i] = patient.known_Ts_at_r(r)-273.15
    Q[i] = patient.known_Q_at_r(r)-273.15
    h[i] = patient.known_h_at_r(r)-273.15

# Plots distance from catheter vs temperature for the different bioheat solutions
# Note, if not running in Spyder IDE may need line to save plots to files
plt.figure(6)
plt.plot(patient.known_Ts_dist['Distance'],patient.known_Ts_dist['Temperature'], label="Utilize Average Catheter Temp (1)")
plt.plot(patient.known_Q_dist['Distance'],patient.known_Q_dist['Temperature'],  label="Utilize Catheter Heat Energy (3)")

# Known convection coefficient solution doesn't align with expectations. Likely an issue with methods for calculation
plt.plot(patient.known_h_dist['Distance'],patient.known_h_dist['Temperature'],  label="Utilize Catheter Convention (2)")

plt.xlabel("Distance from Catheter (cm)")
plt.ylabel("Temperature (c)")
plt.title("Steady State Bioheat Equation")
plt.legend()

plt.show()


test.plot.scatter(0, 2)
plt.show()