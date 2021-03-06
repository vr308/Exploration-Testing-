#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Mon Dec  4 20:08:29 2017

@author: vr308

The main difference between Ridge and ARD is in the specification of individual variances for the weight prior
The sklearn implementation assumes gamma priors over the hyperparameters and infers both precision of weights and 
precision of the noise variance through maximization over the marginal likelihood.  

"""
from sklearn import linear_model
import matplotlib.pylab as plt
import numpy as np


def distSquared(x,y):
    nx = np.size(x, 0)
    ny = np.size(y, 0)
    D2 =  (np.multiply(x, x).sum(1)  * np.ones((1, ny)) ) + ( np.ones((nx, 1)) * np.multiply(y, y).sum(1).T  ) - 2*x*y.T
    return D2


def gaussian_kernel_matrix(x,y):
    
    return np.matrix(np.exp(-distSquared(x,y)/(bw**2)))

if __name__ == "__main__":
    
    #Define some training data

    N = 100
    u = np.sort(np.random.uniform(-10,10,N))
    x = np.matrix(u).T
    y_true = np.matrix(5*np.sin(u) + 0.5*u + -0.2*np.square((u-5))).T
    
    noiseToSignal = 0.2
    noise = np.std(y_true, ddof=1) * noiseToSignal
    y_noise = np.array(y_true + noise*np.random.randn(N,1))
    
    #Design Matrix
    
    bw = 1.4 # basis hyperparameter
    design_matrix = gaussian_kernel_matrix(x,x)
    #plt.plot(x,design_matrix)

    # Ridge example

    base_model_ridge = linear_model.BayesianRidge(n_iter=10,verbose=True, compute_score=True)
    fitted_model_ridge = base_model_ridge.fit(design_matrix,y_noise)
    
    # ARD example
    
    base_model_ard = linear_model.ARDRegression(compute_score=True, verbose=True)
    fitted_model_ard = base_model_ard.fit(design_matrix, y_noise)
    
    x_test = np.matrix(np.sort(np.random.uniform(-10,10,50))).T
    design_matrix_test = np.matrix(np.exp(-distSquared(x_test,x)/(bw**2)))
    
    y_pred_ridge = fitted_model_ridge.predict(design_matrix_test)
    y_pred_ard = fitted_model_ard.predict(design_matrix_test)
    y_test_true = np.matrix(5*np.sin(x_test) + 0.5*x_test + -0.2*np.square((x_test-5))).T
    
    sd1_weights_ridge = np.array(np.sqrt(np.matrix(fitted_model_ridge.sigma_).diagonal()))[0]
    sd1_weights_ard = np.array(np.sqrt(np.matrix(fitted_model_ridge.sigma_).diagonal()))[0]
    
    rmse_ridge = np.sqrt(np.sum(np.square(y_test_true - y_pred_ridge)))
    rmse_ard = np.sqrt(np.sum(np.square(y_test_true - y_pred_ard)))
    
    # Plot the predictions
    
    x_line = np.matrix(np.linspace(-10,+10,500)).T
    y_line_ridge = fitted_model_ridge.predict(gaussian_kernel_matrix(x_line, x))
    y_line_ard = fitted_model_ard.predict(gaussian_kernel_matrix(x_line,x))
    
    plt.figure()
    plt.subplot(211)
    plt.plot(x,y_true, 'b')
    #plt.plot(x,y_noise, 'ko',markersize=2)
    plt.plot(x_test, y_pred_ridge, 'ro', markersize=1, label = 'RMSE: ' + np.str(np.round(rmse_ridge, 2)))
    plt.plot(x_line,y_line_ridge)
    #plt.vlines(x_test, ymin= y_test_true, ymax=y_pred_ridge)
    plt.legend(loc=2)
    plt.title('Predictions under Ridge', fontsize='small')
    plt.subplot(212)
    plt.plot(x, y_true, 'b')
    plt.plot(x_test, y_pred_ard, 'go', markersize=1, label = 'RMSE: ' + np.str(np.round(rmse_ard, 2)))
    #plt.vlines(x_test, ymin=y_test_true, ymax=y_pred_ard)
    plt.plot(x_line,y_line_ard)
    plt.legend(loc=2)
    plt.title('Predictions under ARD', fontsize='small')
    
    # Plot the weights (coef_) with the variances
    
    plt.figure()
    plt.subplot(211)
    plt.errorbar(x=np.arange(100), y=fitted_model_ridge.coef_,yerr=sd1_weights_ridge,fmt='o',color='r',ecolor='b', label = 'Ridge',markersize=2)
    plt.hlines(y=0, xmin=0, xmax=100)
    plt.legend(loc=1)
    plt.subplot(212)
    plt.errorbar(x=np.arange(100),y=fitted_model_ard.coef_, yerr=sd1_weights_ard, fmt='o', color='r', ecolor='g', label='ARD',markersize=2)
    plt.legend(loc=1)
    plt.hlines(y=0, xmin=0,xmax=100)
    plt.suptitle('Weights under Ridge and ARD', fontsize='small')
    
    # Cross-checking ridge/ARD regression
    
    noise_variance = np.var(y_noise)
    beta = 1/noise_variance
    #beta = fitted_model_ridge.alpha_
    #alpha = fitted_model_ard.lambda_
    
    # Weight prior 
        
    mu_w_prior = np.zeros(100)
    sigma_w_prior = np.matrix(np.identity(100))
    
    # Convergence loop to optimize alpha (weight precision) and beta (noise precision)
    
    # ? missing part which makes the simple results different from the python answer
    
    # Weight posterior
    
    sigma_w_posterior = np.linalg.inv(np.linalg.inv(sigma_w_prior) + np.multiply(beta,np.dot(design_matrix.T, design_matrix)))
    mu_w = sigma_w_posterior.dot(beta*np.dot(design_matrix.T, y_noise))
        
    # Predictive distribution
    
    design_matrix_test = gaussian_kernel_matrix(x_line,x)
    y_pred_mean = design_matrix_test.dot(mu_w)
    y_pred_variance = 1.0/beta + np.matmul(design_matrix_test.T, sigma_w_posterior)    
    
    plt.figure()
    plt.plot(x,y_true, 'b')
    plt.plot(x_line, y_line_ridge)
    plt.plot(x_line, y_pred_mean)
    
    
    


    