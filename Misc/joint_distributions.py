#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: vidhi

Specifying exotic joint distributions as a test bed for sampler testing 

"""

import numpy as np
import scipy.stats as st
import matplotlib.pylab as plt
import scipy as sp
from matplotlib import cm
import seaborn as sns
plt.style.use("ggplot")

# Bivariate normals

x_ = np.linspace(-5,5, 1000)
density_1 = lambda x_ : 0.4*st.norm.pdf(x_, 2, 1) + 0.6*st.norm.pdf(x_, -1, 1)
density_2 = lambda x_ : st.norm.pdf(x_,4,0.3)  

joint_density = lambda x1_, x2_ : density_1(x1_)*density_2(x2_)

# Check that this joint density construction is a valid one

sp.integrate.dblquad(joint_density, -5, +5, lambda x: -5, lambda x: +5)

X1, X2 = np.meshgrid(x_,x_)
Y = joint_density(X1,X2)
plt.figure()
plt.contourf(X1,X2,Y, cmap=cm.get_cmap('jet'),alpha=0.5)
plt.ylim(2.5,5)
plt.xlim(-6, 6)

# Testing samples from seaborn construction 

k=np.random.choice([1,2], size=1000, p = [0.4,0.6])

x1 = []

for i in k:
      if i == 1:
            x1.append(st.norm.rvs(2,1))
      elif i == 2:
            x1.append(st.norm.rvs(-1,1))

x2 = np.random.normal(4, 0.3, 1000)

plt.hist(x1, bins=100, normed=True)
plt.plot(x_, density_1(x_))

sns.jointplot(x1, x2, kind='kde')

#---------------------------------------------------------------------

# Donut / Ring distribution

#---------------------------------------------------------------------

y1 = np.random.uniform(-1,1, 100)
y2 = np.random.uniform(-1,1, 100)

x1 = np.sqrt(1 - y1**2)
x2 = -np.sqrt(1 - y2**2)

y = np.concatenate((y1,y2))
x = np.concatenate((x1, x2)) + np.random.normal(0,0.1, 200)

plt.plot(x, y, 'bo')
plt.ylim(-2,2)
plt.xlim(-2,2)

sns.jointplot(x,y, kind='kde')


#----------------------------------------------------------------------------
# Horseshoe shaped distribution 

# It is obtained by applying a simple transformation to a bi-variate Gaussian
#----------------------------------------------------------------------------

mean = [0,0]
cov = np.array(([1, 0.95], [0.95, 1]))
x_ = np.random.multivariate_normal(mean, cov, size=1000)

def b_transformation(x_):
      
      column_1 = x_[:,0]
      column_2 = x_[:,1] - np.square(x_[:,0]) -1 
      return np.asarray((column_1, column_2)).T.reshape(1000,2)
      
y_ = b_transformation(x_)     

# The transformed samples do indeed look like they have come from a banana shaped dist.
  
sns.jointplot(y_[:,0], y_[:,1], kind='kde')

# Joint density of the banana shaped posterior

x1_ = np.linspace(-3, 4, 1000)
x2_ = np.linspace(-10, 2, 1000)
X1, X2 = np.meshgrid(x1_, x2_)

normalization_const = (1/(2*np.pi*np.sqrt(0.0975)))

joint_density = lambda x1_, x2_ : np.exp((-1/(2*0.0975))*((x1_)**2 + (x2_ + x1_**2 + 1)**2 - (2*0.95*(x1_)*(x2_ + x1_**2 + 1))))

plt.contourf(X1, X2, joint_density(X1, X2), cmap=cm.get_cmap('jet'),alpha=0.5)

# Note: Haven't figured out the normalisation constant properly 

sp.integrate.dblquad(joint_density, -3, 4, lambda x: -10, lambda x: 2)

#----------------------------------------------------------------------------
# Mixture of bi-variate normals
#----------------------------------------------------------------------------

mean1 = [0,2]
cov1 = [[1, 0.8], [0.8,1]]

mean2 = [3,4]
cov2 = [[1, -0.4], [-0.4,1]]

x1_ = np.linspace(-5, 5, 1000)
x2_ = np.linspace(-8, 8, 1000)

X1, X2 = np.meshgrid(x1_, x2_)

points = np.vstack([X1.ravel(), X2.ravel()]).T

p1 = points[:,0]
p2 = points[:,1]

Z1 = st.multivariate_normal.pdf(points.T, mean1, cov1) 
Z2 = st.multivariate_normal.pdf(points.T, mean2, cov2)

mixture = lambda points : 0.5*st.multivariate_normal.pdf(points, mean1, cov1) + 0.5*st.multivariate_normal.pdf(points, mean2, cov2)

def bivariate_mixture(p1,p2):
      
     return 0.5*st.multivariate_normal.pdf((p1,p2), mean1, cov1) + 0.5*st.multivariate_normal.pdf((p1,p2), mean2, cov2)
      
#plt.contourf(X1, X2, Z1.reshape(1000,1000))
#plt.contourf(X1, X2, Z2.reshape(1000,1000))

plt.contourf(X1, X2, mixture(points).reshape(1000,1000))

# Note: The convex combination does result in a mixture that integrates to 1

sp.integrate.dblquad(bivariate_mixture, -7, 7, lambda x: -5, lambda x: 10)

moment_1 = np.add([0,1], [1.5, 2])
moment_2 = np.multiply(0.5,cov1) + np.multiply(0.5,cov1) + 




