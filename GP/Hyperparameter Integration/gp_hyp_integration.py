#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Dec  4 16:40:22 2018

@author: vr308
"""
import pymc3 as pm
import theano.tensor as tt
import pandas as pd
import numpy as np
from matplotlib import cm
import matplotlib.pyplot as plt
from pymc3.gp.util import plot_gp_dist
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as Ck, WhiteKernel
from matplotlib.colors import LogNorm


# set the seed
np.random.seed(12564)

# Setting up a GP model 
n = 20 # The number of data points
X = np.sort(np.linspace(0, 10, n))[:, None] # The inputs to the GP, they must be arranged as a column vector
X_star = np.linspace(0,10,1000)[:,None]

# Define the true covariance function and its parameters
l_true = 1.0
sig_var_true = 2.0
noise_var_true = 0.5
cov_func = sig_var_true**2 * pm.gp.cov.ExpQuad(1, l_true)
cov_func_noise = sig_var_true**2 * pm.gp.cov.ExpQuad(1, l_true) + pm.gp.cov.WhiteNoise(sigma=0.1)

# A mean function that is zero everywhere
mean_func = pm.gp.mean.Zero()

# The latent function values are one sample from a multivariate normal
f_true = np.random.multivariate_normal(mean_func(X).eval(),
                                       cov_func(X).eval() + 1e-8*np.eye(n), 1).flatten()
y = f_true + np.random.normal(loc=0,scale=np.sqrt(noise_var_true), size=n)

## Plot the data and the unobserved latent function
fig = plt.figure(figsize=(12,5)); ax = fig.gca()
ax.plot(X, f_true, "dodgerblue", lw=3, label="True f");
ax.plot(X, y, 'ok', ms=3, alpha=0.5, label="Data");
ax.set_xlabel("X"); ax.set_ylabel("The true f(x)"); plt.legend();

# Using sklearn -----------------------------------------------------------------

# Instansiate a Gaussian Process model

kernel = Ck(4, (1e-10, 1e2)) * RBF(1.5, length_scale_bounds=(0.8, 3)) + WhiteKernel(10, noise_level_bounds=(1,50))
gpr = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=10)
gpr.fit(X, y)   

y_pred_test, sigma = gpr.predict(X_star, return_cov = True)

sample=np.random.multivariate_normal(y_pred_test.flatten(), sigma)
post_samples = gpr.sample_y(X_star, n_samples=1)


#PLotting
fig = plt.figure(figsize=(12,5)); ax = fig.gca()
plt.plot(X, f_true, 'dodgerblue', label='True')
plt.plot(X, y, 'ok', ms=3, alpha=0.5, label="Observed data")
plt.plot(X_star, y_pred_test, 'r-', label=u'Prediction')
plot_gp_dist(ax, post_samples.T, X_star)
plot_gp_dist(ax, pred_samples["y_pred"], X_star);
plt.fill_between(np.ravel(X_star), np.ravel(y_pred_test) - 1.96*sigma, np.ravel(y_pred_test) + 1.96*sigma, alpha=0.2, color='k')
plt.title('GPR ' + '\n' + str(gpr.kernel_) + '\n' + 'Method: Type II ML', fontsize='small')
plt.legend(fontsize='small')

signal_var = np.sqrt(gpr.kernel_.k1.k1.constant_value)
lengthscale = gpr.kernel_.k1.k2.length_scale
noise_var = gpr.kernel_.k2.noise_level

# Plot the LML surface (2-way plots)

plt.figure(figsize=(15,6))
plt.subplot(131)
l_log = np.logspace(-2, 3, 100)
noise_log  = np.logspace(-2, 2, 100)
l_log_mesh, noise_log_mesh = np.meshgrid(l_log, noise_log)
LML = [[gpr.log_marginal_likelihood(np.log([signal_var, l_log_mesh[i, j], noise_log_mesh[i, j]]))
        for i in range(l_log_mesh.shape[0])] for j in range(l_log_mesh.shape[1])]
LML = np.array(LML).T

vmin, vmax = (-LML).min(), (-LML).max()
#vmax = 50
level = np.around(np.logspace(np.log10(vmin), np.log10(vmax), 100), decimals=1)
plt.contourf(l_log_mesh, noise_log_mesh, -LML,
            levels=level, norm=LogNorm(vmin=vmin, vmax=vmax), cmap=cm.get_cmap('jet'))
plt.plot(lengthscale, noise_var, 'rx')
plt.xscale("log")
plt.yscale("log")
plt.xlabel("Length-scale")
plt.ylabel("Noise-level")

plt.subplot(132)
l_log = np.logspace(-2, 3, 100)
signal_log  = np.logspace(-3, 5, 100)
l_log_mesh, signal_log_mesh = np.meshgrid(l_log, signal_log)
LML = [[gpr.log_marginal_likelihood(np.log([signal_log_mesh[i,j], l_log_mesh[i, j], noise_var]))
        for i in range(l_log_mesh.shape[0])] for j in range(l_log_mesh.shape[1])]
LML = np.array(LML).T

vmin, vmax = (-LML).min(), (-LML).max()
#vmax = 50
level = np.around(np.logspace(np.log10(vmin), np.log10(vmax), 100), decimals=1)
plt.contourf(l_log_mesh, signal_log_mesh, -LML,
            levels=level, norm=LogNorm(vmin=vmin, vmax=vmax), cmap=cm.get_cmap('jet'))
plt.plot(lengthscale, signal_var, 'rx')
#plt.colorbar()
plt.xscale("log")
plt.yscale("log")
plt.xlabel("Length-scale")
plt.ylabel("Signal-Var")

plt.subplot(133)
noise_log = np.logspace(-2, 3, 100)
signal_log  = np.logspace(-3, 5, 100)
noise_log_mesh, signal_log_mesh = np.meshgrid(noise_log, signal_log)
LML = [[gpr.log_marginal_likelihood(np.log([signal_log_mesh[i,j], lengthscale, noise_log_mesh[i,j]]))
        for i in range(l_log_mesh.shape[0])] for j in range(l_log_mesh.shape[1])]
LML = np.array(LML).T

vmin, vmax = (-LML).min(), (-LML).max()
#vmax = 50
level = np.around(np.logspace(np.log10(vmin), np.log10(vmax), 100), decimals=1)
plt.contourf(noise_log_mesh, signal_log_mesh, -LML,
            levels=level, norm=LogNorm(vmin=vmin, vmax=vmax), cmap=cm.get_cmap('jet'))
plt.plot(noise_var, signal_var, 'rx')
#plt.colorbar()
plt.xscale("log")
plt.yscale("log")
plt.xlabel("Noise-level")
plt.ylabel("Signal-Var")

plt.suptitle('LML Surface ' + '\n' + str(gpr.kernel_), fontsize='small')

# Type II ML / Plug-in approach (Flat prior on hyp and find MAP -> same as type 2 ML)

with pm.Model() as marginal_gp_model:

   # prior on lengthscale 
   l = pm.Uniform('lengthscale', 0, 5)
   
   #prior on signal variance
   log_n = pm.Uniform('log_n', lower=-10, upper=5)
   sig_var = pm.Deterministic('sig_var', tt.exp(log_n))
   
   #prior on noise variance
   log_sig = pm.Uniform('log_sig', lower=-10, upper=5)
   noise_var = pm.Deterministic('noise_var', tt.exp(log_sig))
   
   # covariance functions for the function f and the noise
   f_cov = n*pm.gp.cov.ExpQuad(1, l)
   
   gp = pm.gp.Marginal(cov_func=f_cov)
   y_obs = gp.marginal_likelihood("y", X=X, y=y, noise=noise_var)
   #y_obs = pm.gp('y_obs', cov_func=f_cov, sigma=sigma, observed={'X':X, 'Y':y})
   mp = pm.find_MAP()
   
with marginal_gp_model:
   y_pred = gp.conditional("y_pred", X_star, pred_noise=False)
   
with marginal_gp_model:
   pred_samples = pm.sample_ppc([mp], vars=[y_pred], samples=50)
   

map_df = pd.DataFrame({"Parameter": ["lengthscale", "sig_var", "noise_var"],
              "MAP": [float(mp["lengthscale"]), float(mp["sig_var"]), float(mp["noise_var"])],
              "True value": [l_true, sig_var_true, noise_var_true ]})
   
#Plotting
fig = plt.figure(figsize=(12,5)); ax = fig.gca()

# plot the samples from the gp posterior with samples and shading
plot_gp_dist(ax, pred_samples["y_pred"], X_star);

# plot the data and the true latent function
plt.plot(X, f_true, "dodgerblue", lw=3, label="True f");
plt.plot(X, y, 'ok', ms=3, alpha=0.5, label="Observed data");

# axis labels and title
plt.xlabel("X")
plt.ylim([-4,8])
plt.title("Posterior distribution over $f(x)$ w. Type II ML")
plt.legend()
plt.text(5, 6, str(map_df))

# HMC Sampling approach 

with pm.Model() as hmc_gp_model:
    
   # prior on lengthscale 
   l = pm.Gamma('lengthscale', alpha=2, beta=1)
         
   #prior on signal variance
   #sig_var = pm.HalfCauchy('sig_var', beta=5)
   sig_var = pm.Gamma('sig_var', alpha=2, beta=1)
   
   #prior on noise variance
   noise_var = pm.HalfCauchy('noise_var', beta=5)
   
   # covariance functions for the function f and the noise
   f_cov = n*pm.gp.cov.ExpQuad(1, l)
   
   gp = pm.gp.Marginal(cov_func=f_cov)
   y_obs = gp.marginal_likelihood("y", X=X, y=y, noise=noise_var)
  
   trace = pm.sample(500)  
   
with hmc_gp_model:
   y_pred = gp.conditional("y_pred", X_star, pred_noise=False)
   
with hmc_gp_model:
   pred_samples = pm.sample_ppc(trace, vars=[y_pred], samples=50)
   

#Plotting
fig = plt.figure(figsize=(12,5)); ax = fig.gca()

# plot the samples from the gp posterior with samples and shading
plot_gp_dist(ax, pred_samples["y_pred"], X_star);

# plot the data and the true latent function
plt.plot(X, f_true, "dodgerblue", lw=3, label="True f");
plt.plot(X, y, 'ok', ms=3, alpha=0.5, label="Observed data");

# axis labels and title
plt.xlabel("X")
plt.ylim([-4,8])
plt.title("Posterior distribution over $f(x)$ w. HMC sampling for " + r'$\{l, \sigma^{2}_{f}, \sigma^{2}_{n}\}$')
plt.legend()

# Posterior Marginals -> with True and MAP Est. + Priors shown + Combine sampling chains

type2_ml = {'lengthscale' : mp['lengthscale'], 'sig_var': mp['sig_var'], 'noise_var': mp['noise_var']}
priors = [l.distribution, sig_var.distribution, noise_var.distribution]

pm.traceplot(trace, varnames=['lengthscale', 'sig_var', 'noise_var'], combined=True, bw=2, lines=type2_ml, priors=priors)

# VI approach 

Xu_init = 10*np.random.rand(20)

with pm.Model() as vfe_gp_model:
    
   # prior on lengthscale 
   l = pm.Gamma('lengthscale', alpha=2, beta=1)
         
   #prior on signal variance
   #sig_var = pm.HalfCauchy('sig_var', beta=5)
   sig_var = pm.Gamma('sig_var', alpha=2, beta=1)
   
   #prior on noise variance
   noise_var = pm.HalfCauchy('noise_var', beta=3)
   
   # Flat prior for inducing points 
   Xu = pm.Flat("Xu", shape=20, testval=Xu_init)
   
   # covariance functions for the function f and the noise
   f_cov = n*pm.gp.cov.ExpQuad(1, l)
   
   gp = pm.gp.MarginalSparse(cov_func=f_cov, approx="VFE")
   y_obs = gp.marginal_likelihood("y", X=X, Xu= Xu[:,None], y=y, noise=noise_var)
  
   trace = pm.sample(500)  
   
with vfe_gp_model:
   y_pred = gp.conditional("y_pred", X_star, pred_noise=False)
   
with vfe_gp_model:
   pred_samples = pm.sample_ppc(trace, vars=[y_pred], samples=50)
   
# Plotting
   












      
      
      