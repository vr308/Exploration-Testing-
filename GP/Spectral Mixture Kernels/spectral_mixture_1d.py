#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  6 17:59:53 2020

@author: vidhi.lalchand
"""

import math
import random
import numpy as np
import torch
import pymc3 as pm
import gpytorch
import pyro
from pyro.infer.mcmc import NUTS, MCMC
from matplotlib import pyplot as plt
from gpytorch.priors import LogNormalPrior, NormalPrior, UniformPrior

class SpectralMixtureGPModel(gpytorch.models.ExactGP):
    def __init__(self, train_x, train_y, likelihood):
        super(SpectralMixtureGPModel, self).__init__(train_x, train_y, likelihood)
        self.mean_module = gpytorch.means.ConstantMean()
        self.covar_module = gpytorch.kernels.SpectralMixtureKernel(num_mixtures=3)
        self.covar_module.initialize_from_data(train_x, train_y)

    def forward(self,x):
        mean_x = self.mean_module(x)
        covar_x = self.covar_module(x)
        return gpytorch.distributions.MultivariateNormal(mean_x, covar_x)

if __name__== "__main__":

    torch.manual_seed(4321)

    sm_kernel = gpytorch.kernels.SpectralMixtureKernel(num_mixtures=3, ard_num_dims=1)

    # True values

    means = np.array([0.4, 0.09, 0.05])
    scales = np.array([0.001, 0.0025, 0.01])
    weights = np.array([0.3,0.4,0.3])

    sm_kernel.mixture_means = means
    sm_kernel.mixture_scales = scales
    sm_kernel.mixture_weights = weights

    x = torch.linspace(-10,10,200)

    gp_prior = gpytorch.distributions.MultivariateNormal(mean=torch.tensor([0]*200).float(), covariance_matrix=sm_kernel(x,x), validate_args=True)

    # Select a true function from either a prior sample, sine function,
    true_func = torch.sin(2*x)/x
    true_func = gp_prior.sample(sample_shape=torch.Size([1])).reshape(len(x))

    # Set the number of training points and noise sd
    
    n_sizes = [10,15,20,40]
    n_noise_levels = [0.2, 0.5, 1, 2]
    
    for i in np.arange(len(n_sizes)):
        
        torch.manual_seed(4321)
    
        n_train = n_sizes[i]
        noise_sd = 0.2
    
        train_index = random.sample(list(np.arange(len(x))),n_train)
        train_x = x[train_index]
        train_f = true_func[train_index]
        train_y =  train_f + noise_sd*torch.randn(n_train)
        test_x = x
        
        #Plotting training set
        # if(i == 0):
        #     plt.figure(figsize=(8,3))
        #     plt.suptitle('Fixed Noise Experiments - noise_sd: ' + str(noise_sd), fontsize='x-small')
        #     #plt.suptitle('Fixed Training size - n_size: ' + str(n_train))
        #     plt.tight_layout()
        # plt.subplot(1,4,i+1)
        # plt.plot(x, true_func, color='k')
        # plt.plot(train_x, train_y, 'bo', markersize=2)
        # plt.xticks(fontsize='x-small')
        # plt.yticks(fontsize='x-small')
        # plt.title('n_train: ' + str(n_train), fontsize='x-small')
        
       
        # Model Set-up
    
        likelihood = gpytorch.likelihoods.GaussianLikelihood()
        model_ml = SpectralMixtureGPModel(train_x, train_y, likelihood)
    
        # Find optimal model hyperparameters
        
        model_ml.train()
        likelihood.train()
    
        # Use the adam optimizer
        optimizer = torch.optim.Adam(model_ml.parameters(), lr=0.1)
    
        # "Loss" for GPs - the marginal log likelihood
        mll_ml = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model_ml)
    
        training_iter = 150
    
        loss_trace = []
        for j in range(training_iter):
            optimizer.zero_grad()
            output = model_ml(train_x)
            loss = -mll_ml(output, train_y)
            loss_trace.append(loss)
            loss.backward()
            print('Iter %d/%d - Loss: %.3f' % (j + 1, training_iter, loss.item()))
            optimizer.step()
    
        # Get into evaluation (predictive posterior) mode
        model_ml.eval()
        likelihood.eval()
    
        with torch.no_grad(), gpytorch.settings.fast_pred_var():
            # Make predictions
            observed_pred = likelihood(model_ml(test_x))
            
        mse = torch.mean((test_x - observed_pred.mean.numpy())**2)
        tll = -torch.distributions.MultivariateNormal(observed_pred.mean, observed_pred.covariance_matrix).log_prob(true_func)
    
        # Initialize plot
        if(i == 0):
                 plt.figure(figsize=(8,3))
                 plt.suptitle('Fixed Noise Experiments - noise_sd: ' + str(noise_sd), fontsize='x-small')
            #     #plt.suptitle('Fixed Training size - n_size: ' + str(n_train))
                 plt.tight_layout()
        # Get upper and lower confidence bounds
        plt.subplot(1,4,i+1)
        lower, upper = observed_pred.confidence_region()
        plt.plot(train_x.numpy(), train_y.numpy(), 'ko', markersize=2)
        plt.plot(test_x.numpy(), observed_pred.mean.numpy(), 'r')
        plt.plot(test_x.numpy(), true_func, color='k')
        # Shade between the lower and upper confidence bounds
        plt.fill_between(test_x.numpy(), lower.numpy(), upper.numpy(), alpha=0.5, color='r')
        plt.ylim([-3, 3])
        plt.xticks(fontsize='x-small')
        plt.yticks(fontsize='x-small')
        if (i == 4):
            plt.legend(['Posterior mean', 'True', '95% CI'], fontsize='x-small')
        plt.title('n_train: ' + str(n_train)  + '\n' +
                  'MSE: ' + str(np.round(mse.item(),3)) + '\n' + 
                  'NLPD: ' + str(np.round(tll.item(),3)), fontsize='x-small')

    # The trained hyperparameters

    mixture_weights = model_ml.covar_module.mixture_weights
    mixture_means = model_ml.covar_module.mixture_means
    mixture_scales = model_ml.covar_module.mixture_scales
  
    # HMC
    
    for i in np.arange(len(n_sizes)):
        
        torch.manual_seed(4321)
    
        n_train = n_sizes[i]
        noise_sd = 0.2
    
        train_index = random.sample(list(np.arange(len(x))),n_train)
        train_x = x[train_index]
        train_f = true_func[train_index]
        train_y =  train_f + noise_sd*torch.randn(n_train)
        test_x = x
 
        likelihood = gpytorch.likelihoods.GaussianLikelihood()
        model_hmc = SpectralMixtureGPModel(train_x, train_y, likelihood)
    
        # Registering priors for hypers
    
        model_hmc.covar_module.register_prior('weights_prior', LogNormalPrior(0,1), 'mixture_weights')
        model_hmc.covar_module.register_prior('means_prior', LogNormalPrior(0,1), 'mixture_means')
        model_hmc.covar_module.register_prior('scales_prior', LogNormalPrior(0,1), 'mixture_scales')
    
        mll_hmc = gpytorch.mlls.ExactMarginalLogLikelihood(likelihood, model_hmc)

        def pyro_model(x, y):
            model_hmc.pyro_sample_from_prior()
            output = model_hmc(x)
            loss = mll_hmc.pyro_factor(output, y)
            return y
    
        nuts_kernel = NUTS(pyro_model, adapt_step_size=True)
        mcmc_run = MCMC(nuts_kernel, num_samples=200, warmup_steps=500)
        mcmc_run.run(train_x, train_y)
    
        model_hmc.pyro_load_from_samples(mcmc_run.get_samples())
        model_hmc.eval()
        #test_x = torch.linspace(0, 1, 101).unsqueeze(-1)
        #test_y = torch.sin(test_x * (2 * math.pi))
        #expanded_test_x = test_x.unsqueeze(0).repeat(200, 1, 1)
        output = model_hmc(expanded_test_x)

        with torch.no_grad():
            # Initialize plot
            f, ax = plt.subplots(1, 1, figsize=(4, 3))
    
            # Plot training data as black stars
            ax.plot(train_x.numpy(), train_y.numpy(), 'k*', zorder=10)
    
                # Plot predictive means as blue line
                ax.plot(test_x.numpy(), output.mean[i].detach().numpy(), 'b', linewidth=0.3, alpha=0.4)
    
            # Shade between the lower and upper confidence bounds
            ax.fill_between(test_x.numpy(), lower.numpy(), upper.numpy(), alpha=0.5)
            ax.set_ylim([-3, 3])
            ax.legend(['Observed Data', 'Sampled Means'])
    
