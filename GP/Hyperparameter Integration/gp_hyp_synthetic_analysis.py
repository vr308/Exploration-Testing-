#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 19 19:48:56 2019

@author: vidhi

"""

import pymc3 as pm
import theano.tensor as tt
from sampled import sampled
import pandas as pd
import numpy as np
from matplotlib import cm
import matplotlib.pylab as plt
from theano.tensor.nlinalg import matrix_inverse
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as Ck, RationalQuadratic as RQ, Matern, ExpSineSquared as PER, WhiteKernel
from matplotlib.colors import LogNorm
import seaborn as sns
import scipy.stats as st
import warnings
warnings.filterwarnings("ignore")

#----------------------------Loading persisted data----------------------------

def load_datasets(path, n_train):
      
       n_test = 200 - n_train
       X = np.asarray(pd.read_csv(path + 'X_' + str(n_train) + '.csv', header=None)).reshape(n_train,1)
       y = np.asarray(pd.read_csv(path + 'y_' + str(n_train) + '.csv', header=None)).reshape(n_train,)
       X_star = np.asarray(pd.read_csv(path + 'X_star_' + str(n_train) + '.csv', header=None)).reshape(n_test,1)
       f_star = np.asarray(pd.read_csv(path + 'f_star_' + str(n_train) + '.csv', header=None)).reshape(n_test,)
       return X, y, X_star, f_star

#----------------------------GP Inference-------------------------------------
    
# Type II ML 
    
def get_ml_report(X, y, X_star, f_star):
      
          kernel = Ck(50, (1e-10, 1e3)) * RBF(2, length_scale_bounds=(0.5, 8)) + WhiteKernel(1.0, noise_level_bounds=(1e-1,100))
          
          gpr = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=20)
              
          # Fit to data 
          gpr.fit(X, y)        
          ml_deltas = np.round(np.exp(gpr.kernel_.theta), 3)
          post_mean, post_cov = gpr.predict(X_star, return_cov = True) # sklearn always predicts with noise
          post_std = np.sqrt(np.diag(post_cov) - ml_deltas[2])
          post_samples = np.random.multivariate_normal(post_mean, post_cov , 10)
          rmse_ = rmse(post_mean, f_star)
          lpd_ = log_predictive_density(f_star, post_mean, post_std)
          title = 'GPR' + '\n' + str(gpr.kernel_) + '\n' + 'RMSE: ' + str(rmse_) + '\n' + 'LPD: ' + str(lpd_)     
          ml_deltas_dict = {'ls': ml_deltas[1], 'noise_sd': np.sqrt(ml_deltas[2]), 'sig_sd': np.sqrt(ml_deltas[0]), 
                            'log_ls': np.log(ml_deltas[1]), 'log_n': np.log(np.sqrt(ml_deltas[2])), 'log_s': np.log(np.sqrt(ml_deltas[0]))}
          return post_mean, post_std, rmse_, lpd_, ml_deltas_dict, title

# Generative model for full Bayesian treatment

@sampled
def generative_model(X, y):
      
       # prior on lengthscale 
       log_ls = pm.Uniform('log_ls', lower=-5, upper=5)
       ls = pm.Deterministic('ls', tt.exp(log_ls))
       
        #prior on noise variance
       log_n = pm.Uniform('log_n', lower=-5, upper=5)
       noise_sd = pm.Deterministic('noise_sd', tt.exp(log_n))
         
       #prior on signal variance
       log_s = pm.Uniform('log_s', lower=-5, upper=5)
       sig_sd = pm.Deterministic('sig_sd', tt.exp(log_s))
       
       # Specify the covariance function.
       cov_func = pm.gp.cov.Constant(sig_sd**2)*pm.gp.cov.ExpQuad(1, ls=ls)
    
       gp = pm.gp.Marginal(cov_func=cov_func)
            
       # Marginal Likelihood
       y_ = gp.marginal_likelihood("y", X=X, y=y, noise=noise_sd)
                   
#--------------------Predictive performance metrics-------------------------
      
def rmse(post_mean, f_star):
    
    return np.round(np.sqrt(np.mean(np.square(post_mean - f_star))),3)

def log_predictive_density(f_star, post_mean, post_std):
      
      lppd_per_point = []
      for i in np.arange(len(f_star)):
            lppd_per_point.append(st.norm.pdf(f_star[i], post_mean[i], post_std[i]))
      #lppd_per_point.remove(0.0)
      return np.round(np.mean(np.log(lppd_per_point)),3)

def log_predictive_mixture_density(f_star, list_means, list_cov):
      
      components = []
      for i in np.arange(len(list_means)):
            components.append(st.multivariate_normal.pdf(f_star, list_means[i].eval(), list_cov[i].eval(), allow_singular=True))
      return np.round(np.sum(np.log(np.mean(components))),3)


#-------------Plotting---------------------------------------

def plot_noisy_data(X, y, X_star, f_star, title):

    plt.figure()
    plt.plot(X_star, f_star, "dodgerblue", lw=3, label="True f")
    plt.plot(X, y, 'ok', ms=3, alpha=0.5, label="Data")
    plt.xlabel("X") 
    plt.ylabel("The true f(x)") 
    plt.legend()
    plt.title(title, fontsize='x-small')
    

def plot_gp(X_star, f_star, X, y, post_mean, post_std, post_samples, title):
    
    plt.figure()
    if post_samples != []:
          plt.plot(X_star, post_samples.T, color='grey', alpha=0.2)
    plt.plot(X_star, f_star, "dodgerblue", lw=1.4, label="True f",alpha=0.7);
    plt.plot(X, y, 'ok', ms=3, alpha=0.5)
    plt.plot(X_star, post_mean, color='r', lw=2, label='Posterior mean')
    plt.fill_between(np.ravel(X_star), post_mean - 1.96*post_std, 
                     post_mean + 1.96*post_std, alpha=0.2, color='g',
                     label='95% CR')
    plt.legend(fontsize='x-small')
    plt.title(title, fontsize='x-small')
    
def plot_gp_ml_II_joint(X, y, X_star, pred_mean, pred_std, title):
      
      plt.figure(figsize=(20,5))
      
      for i in [0,1,2,3]:
            plt.subplot(1,4,i+1)
            plt.plot(X_star[i], pred_mean[i], color='r')
            plt.plot(X_star[i], f_star[i], 'k', linestyle='dashed')
            plt.plot(X[i], y[i], 'ko', markersize=2)
            plt.fill_between(X_star[i].ravel(), pred_mean[i] -1.96*pred_std[i], pred_mean[i] + 1.96*pred_std[i], color='r', alpha=0.3)
            plt.title(title[i], fontsize='small')
            plt.ylim(-25, 25)
      plt.tight_layout()
      plt.suptitle('Type II ML')      

def plot_hyp_convergence(tracks, n_train, true_hyp):
      
      plt.figure(figsize=(10,6))
      
      plt.subplot(131)
      plt.axhline(true_hyp[0], color='r', label=r'$\sigma_{f}^{2}$')
      plt.plot(n_train, tracks['sig_sd_track'], 'ro-')

      plt.subplot(132)
      plt.axhline(true_hyp[1], color='b', label=r'$\gamma$')
      plt.plot(n_train, tracks['ls_track'], 'bo-')

      
      plt.subplot(133)
      plt.plot(n_train, tracks['noise_sd_track'], 'go-')
      plt.axhline(true_hyp[2], color='g', label=r'$\sigma_{n}^{2}$')

      
#  PairGrid plot  - bivariate relationships
      
def pair_grid_plot(trace_df, ml_deltas, true_hyp_dict, color, title, varnames):

      g = sns.PairGrid(trace_df, vars=varnames, diag_sharey=False)
      g = g.map_lower(plot_bi_kde, ml_deltas=ml_deltas,true_hyp_dict=true_hyp_dict, color=color)
      g = g.map_diag(plot_hist, color=color)
      g = g.map_upper(plot_scatter, ml_deltas=ml_deltas, color=color)
      
      g.axes[0,0].axvline(ml_deltas[g.x_vars[0]], color='r')
      g.axes[1,1].axvline(ml_deltas[g.x_vars[1]], color='r')
      g.axes[2,2].axvline(ml_deltas[g.x_vars[2]], color='r')
      
      plt.suptitle(title, fontsize='small')

def plot_bi_kde(x,y, ml_deltas,true_hyp_dict, color, label):
      
      sns.kdeplot(x, y, n_levels=20, color=color, shade=True, shade_lowest=False)
      plt.scatter(ml_deltas[x.name], ml_deltas[y.name], marker='x', color='r')
      plt.axvline(true_hyp_dict[x.name], color='k', alpha=0.5)
      plt.axhline(true_hyp_dict[y.name], color='k', alpha=0.5)
      
def plot_hist(x, color, label):
      
      sns.distplot(x, bins=100, color=color, kde=True)

def plot_scatter(x, y, ml_deltas, color, label):
      
      plt.scatter(x, y, c=color, s=0.5, alpha=0.7)
      plt.scatter(ml_deltas[x.name], ml_deltas[y.name], marker='x', color='r')
      
      
def plot_autocorrelation(trace_hmc, varnames, title):
      
      pm.autocorrplot(trace_hmc, varnames=varnames)
      plt.suptitle(title, fontsize='small')
      

# Marginal

def plot_simple_traceplot(trace, varnames, ml_deltas, log, title):
      
      traces = pm.traceplot(trace, varnames=varnames, lines=ml_deltas, combined=True)
      
      for i in np.arange(3):
           
            delta = ml_deltas.get(str(varnames[i]))
            traces[i][0].axvline(x=delta, color='r',alpha=0.5, label='ML ' + str(np.round(delta, 2)))
            traces[i][0].hist(trace[varnames[i]], bins=100, density=True, color='b', alpha=0.3)
            traces[i][1].axhline(y=delta, color='r', alpha=0.5) 
            traces[i][0].legend(fontsize='x-small')
            if log:
                 traces[i][0].axes.set_xscale('log')
      plt.suptitle(title, fontsize='small')


def traceplot_compare(model, trace_hmc, trace_mf, trace_fr, varnames, deltas):

      traces = pm.traceplot(trace_hmc, varnames, lines=deltas, combined=True)
      
      rv_mapping = {'sig_sd': model.log_s_interval__, 'ls': model.log_ls_interval__, 'noise_sd': model.log_n_interval__}

      means_mf = mf.approx.bij.rmap(mf.approx.mean.eval())  
      std_mf = mf.approx.bij.rmap(mf.approx.std.eval())  
      
      means_fr = fr.approx.bij.rmap(fr.approx.mean.eval())  
      std_fr = fr.approx.bij.rmap(fr.approx.std.eval())  
      
      for i in np.arange(3):
            
            delta = deltas.get(str(varnames[i]))
            xmax = max(max(trace_hmc[varnames[i]]), delta)
            xmin = min(min(trace_hmc[varnames[i]]), delta)
            range_i = np.linspace(xmin, xmax, 1000)  
            traces[i][0].axvline(x=delta, color='r',alpha=0.5, label='ML ' + str(np.round(delta, 2)))
            traces[i][0].hist(trace_hmc[varnames[i]], bins=100, density=True, color='b', alpha=0.3)
            traces[i][1].axhline(y=delta, color='r', alpha=0.5)
            traces[i][0].plot(range_i, get_implicit_variational_posterior(rv_mapping.get(varnames[i]), means_fr, std_fr, range_i), color='green')
            traces[i][0].plot(range_i, get_implicit_variational_posterior(rv_mapping.get(varnames[i]), means_mf, std_mf, range_i), color='coral')
            #traces_part1[i][0].axes.set_ylim(0, 0.005)
            traces[i][0].legend(fontsize='x-small')
            
# Variational approximation
            
def get_implicit_variational_posterior(var, means, std, x):
      
      sigmoid = lambda x : 1 / (1 + np.exp(-x))

      eps = lambda x : var.distribution.transform_used.forward_val(np.log(x))
      backward_theta = lambda x: var.distribution.transform_used.backward(x).eval()   
      width = (var.distribution.transform_used.b -  var.distribution.transform_used.a).eval()
      total_jacobian = lambda x: x*(width)*sigmoid(eps(x))*(1-sigmoid(eps(x)))
      pdf = lambda x: st.norm.pdf(eps(x), means[var.name], std[var.name])/total_jacobian(x)
      return pdf(x)

      
#-----------------Trace post-processing & analysis ------------------------------------

def get_trace_means(trace, varnames):
      
      trace_means = []
      for i in varnames:
            trace_means.append(trace[i].mean())
      return trace_means

def get_trace_sd(trace, varnames):
      
      trace_sd = []
      for i in varnames:
            trace_sd.append(trace[i].std())
      return trace_sd



def trace_report(mf, fr, trace_hmc, trace_mf, trace_fr, varnames, ml_deltas, true_hyp):
      
      hyp_mean_mf = np.round(get_trace_means(trace_mf, varnames),3)
      hyp_sd_mf = np.round(get_trace_sd(trace_mf, varnames),3)
      
      hyp_mean_fr = np.round(get_trace_means(trace_fr, varnames),3)
      hyp_sd_fr = np.round(get_trace_sd(trace_fr, varnames),3)
      
      means_mf = mf.approx.bij.rmap(mf.approx.mean.eval())  
      std_mf = mf.approx.bij.rmap(mf.approx.std.eval())  
      
      means_fr = fr.approx.bij.rmap(fr.approx.mean.eval())  
      std_fr = fr.approx.bij.rmap(fr.approx.std.eval())  

      traces = pm.traceplot(trace_hmc, varnames=varnames, lines=ml_deltas, combined=True, bw=1)
      
      l_int = np.linspace(min(trace_fr['ls'])-1, max(trace_fr['ls'])+1, 1000)
      n_int = np.linspace(min(trace_fr['noise_sd'])-1, max(trace_fr['noise_sd'])+1, 1000)
      s_int = np.linspace(min(trace_fr['sig_sd'])-1, max(trace_fr['sig_sd'])+1, 1000)
      
      mf_rv = [mf.approx.model.log_s_interval__, mf.approx.model.log_ls_interval__, mf.approx.model.log_n_interval__]
      fr_rv = [fr.approx.model.log_s_interval__, fr.approx.model.log_ls_interval__, fr.approx.model.log_n_interval__]
      
      ranges = [s_int, l_int, n_int]
      
      for i, j in [(0,0), (1,0), (2,0)]:
            
            traces[i][j].axvline(x=hyp_mean_mf[i], color='coral', alpha=0.5, label='MF ' + str(hyp_mean_mf[i]))
            traces[i][j].axvline(x=hyp_mean_fr[i], color='g', alpha=0.5, label='FR ' + str(hyp_mean_fr[i]))
            traces[i][j].axvline(x=ml_deltas[varnames[i]], color='r', alpha=0.5, label='ML ' + str(ml_deltas[varnames[i]]))
            traces[i][j].axvline(x=true_hyp[i], color='k', linestyle='--', label='True ' + str(true_hyp[i]))
            #traces[i][j].axes.set_xscale('log')
            
            traces[i][j].hist(trace_hmc[varnames[i]], bins=100, normed=True, color='b', alpha=0.3)
            #traces[i][j].hist(trace_mf[varnames[i]], bins=100, normed=True, color='coral', alpha=0.3)
            #traces[i][j].hist(trace_fr[varnames[i]], bins=100, normed=True, color='g', alpha=0.3)

            traces[i][j].plot(ranges[i], get_implicit_variational_posterior(mf_rv[i], means_mf, std_mf, ranges[i]), color='coral')
            traces[i][j].plot(ranges[i], get_implicit_variational_posterior(fr_rv[i], means_fr, std_fr, ranges[i]), color='g')
            traces[i][j].legend(fontsize='x-small')
            
      
if __name__ == "__main__":

      # Loading data
      
      uni_path = '/home/vidhi/Desktop/Workspace/CoreML/GP/Hyperparameter Integration/Data/1d/'
      home_path = '/home/vidhi/Desktop/Workspace/CoreML/GP/Hyperparameter Integration/Data/1d/'

      # Edit here to change generative model
      
      input_dist =  'Unif'
      snr = 2
      n_train = [5, 10, 20, 40]
      suffix = input_dist + '/' + 'SNR_' + str(snr) + '/'
      true_hyp = [np.round(np.sqrt(100),3), 5, np.round(np.sqrt(50),3)]

      data_path = uni_path + suffix
      results_path = '/home/vidhi/Desktop/Workspace/CoreML/GP/Hyperparameter Integration/Results/1d/' + suffix 
      
      true_hyp_dict = {'sig_sd': true_hyp[0], 'ls': true_hyp[1] , 'noise_sd': true_hyp[2], 'log_s': np.log(true_hyp[0]),  'log_ls':np.log(true_hyp[1]) , 'log_n':np.log(true_hyp[2])}
      varnames = ['sig_sd', 'ls', 'noise_sd']
      log_varnames = ['log_s', 'log_ls', 'log_n']
      
      #----------------------------------------------------
      # Joint Analysis
      #----------------------------------------------------
      
      # Type II ML
      
      X_5, y_5, X_star_5, f_star_5 = load_datasets(data_path, 5)
      X_10, y_10, X_star_10, f_star_10 = load_datasets(data_path, 10)
      X_20, y_20, X_star_20, f_star_20 = load_datasets(data_path, 20)
      X_40, y_40, X_star_40, f_star_40 = load_datasets(data_path, 40)
      
      X = [X_5, X_10, X_20, X_40]
      y = [y_5, y_10, y_20, y_40]
      X_star = [X_star_5, X_star_10, X_star_20, X_star_40]
      f_star = [f_star_5, f_star_10, f_star_20, f_star_40] 
      
      # Collecting ML stats for 1 generative model
      
      pp_mean_ml_5, pp_std_ml_5, rmse_ml_5, lpd_ml_5, ml_deltas_dict_5, title_5 =  get_ml_report(X_5, y_5, X_star_5, f_star_5)
      pp_mean_ml_10, pp_std_ml_10, rmse_ml_10, lpd_ml_10, ml_deltas_dict_10, title_10 =  get_ml_report(X_10, y_10, X_star_10, f_star_10)
      pp_mean_ml_20, pp_std_ml_20, rmse_ml_20, lpd_ml_20, ml_deltas_dict_20, title_20 =  get_ml_report(X_20, y_20, X_star_20, f_star_20)
      pp_mean_ml_40, pp_std_ml_40, rmse_ml_40, lpd_ml_40, ml_deltas_dict_40, title_40 =  get_ml_report(X_40, y_40, X_star_40, f_star_40)
     

      # Collecting means and stds in a list for plotting

      title = [ title_5, title_10, title_20, title_40]
      pred_mean = [pp_mean_ml_5, pp_mean_ml_10, pp_mean_ml_20, pp_mean_ml_40] 
      pred_std = [pp_std_ml_5, pp_std_ml_10, pp_std_ml_20, pp_std_ml_40]
      rmse_track = [rmse_ml_5, rmse_ml_10, rmse_ml_20, rmse_ml_40]
      lpd_track = [-lpd_ml_5, -lpd_ml_10, -lpd_ml_20, -lpd_ml_40]
      
      # Collecting hyp tracks for plotting
      
      sig_sd_track = [ml_deltas_dict_5['sig_sd'], ml_deltas_dict_10['sig_sd'], ml_deltas_dict_20['sig_sd'], ml_deltas_dict_40['sig_sd']]
      noise_sd_track = [ml_deltas_dict_5['noise_sd'], ml_deltas_dict_10['noise_sd'], ml_deltas_dict_20['noise_sd'], ml_deltas_dict_40['noise_sd']]
      ls_track = [ml_deltas_dict_5['ls'], ml_deltas_dict_10['ls'], ml_deltas_dict_20['ls'], ml_deltas_dict_40['ls']]
      
      tracks = {}
      tracks.update({'sig_sd_track': sig_sd_track})
      tracks.update({'noise_sd_track': noise_sd_track})
      tracks.update({'ls_track': ls_track})
            
      # Convergence to hyp 
      
       plot_hyp_convergence(tracks, n_train, true_hyp)

      # ML Report
      
       plot_gp_ml_II_joint(X, y, X_star, pred_mean, pred_std, title)
      

      #-----------------------------Full Bayesian HMC--------------------------------------- 
            
      # Generating traces with NUTS
      
      with generative_model(X=X_5, y=y_5): trace_hmc_5 = pm.sample(draws=1000, tune=2000)
      with generative_model(X=X_10, y=y_10): trace_hmc_10 = pm.sample(draws=1000, tune=2000)
      with generative_model(X=X_20, y=y_20): trace_hmc_20 = pm.sample(draws=1000, tune=2000)
      with generative_model(X=X_40, y=y_40): trace_hmc_40 = pm.sample(draws=1000, tune=2000)

      trace_hmc_5_df = pm.trace_to_dataframe(trace_hmc_5)
      trace_hmc_10_df = pm.trace_to_dataframe(trace_hmc_10)
      trace_hmc_20_df = pm.trace_to_dataframe(trace_hmc_20)
      trace_hmc_40_df = pm.trace_to_dataframe(trace_hmc_40)

      # Traceplot Marginals
       
       title_b_5 = input_dist +  ',  SNR: ' + str(snr) + ', N: ' + str(5)
       title_b_10 =  input_dist +  ',  SNR: ' + str(snr) + ', N: ' + str(10)
       title_b_20 = input_dist +  ',  SNR: ' + str(snr) + ', N: ' + str(20)
       title_b_40 = input_dist +  ',  SNR: ' + str(snr) + ', N: ' + str(40)
       
       plot_simple_traceplot(trace_hmc_5, varnames, ml_deltas_dict_5, log=True, title = title_b_5)
       plot_simple_traceplot(trace_hmc_10, varnames, ml_deltas_dict_10, log=True, title = title_b_10)
       plot_simple_traceplot(trace_hmc_20, varnames, ml_deltas_dict_20, log=True, title = title_b_20)
       plot_simple_traceplot(trace_hmc_40, varnames, ml_deltas_dict_40, log=True, title = title_b_40)
       
       # Autocorrelation plots
       
       plot_autocorrelation(trace_hmc_5, varnames, title_b_5)
       plot_autocorrelation(trace_hmc_10, varnames, title_b_10)
       plot_autocorrelation(trace_hmc_20, varnames, title_b_20)
       plot_autocorrelation(trace_hmc_40, varnames, title_b_40)
       
       # Sampler stats
       
       summary_df_5 = pm.summary(trace_hmc_5)
       summary_df_10 = pm.summary(trace_hmc_10) 
       summary_df_20 = pm.summary(trace_hmc_20)
       summary_df_40 = pm.summary(trace_hmc_40)
       
       summary_df_5.to_csv(results_path + 'summary_hmc_5.csv', sep=',')
       summary_df_10.to_csv(results_path + 'summary_hmc_10.csv', sep=',')
       summary_df_20.to_csv(results_path + 'summary_hmc_20.csv', sep=',')
       summary_df_40.to_csv(results_path + 'summary_hmc_40.csv', sep=',')

       # Pair-Grid report
      
       pair_grid_plot(trace_hmc_5_df, ml_deltas_dict_5,  true_hyp_dict, 'b', title_b_5, varnames)
       pair_grid_plot(trace_hmc_10_df, ml_deltas_dict_10, true_hyp_dict, 'b', title_b_10, varnames)
       pair_grid_plot(trace_hmc_20_df, ml_deltas_dict_20, true_hyp_dict, 'b', title_b_20, varnames)
       pair_grid_plot(trace_hmc_40_df, ml_deltas_dict_40, true_hyp_dict, 'b', title_b_40, varnames)
       
       pair_grid_plot(trace_hmc_5_df, ml_deltas_dict_5, true_hyp_dict, 'b', title_b_5, log_varnames)
       pair_grid_plot(trace_hmc_10_df, ml_deltas_dict_10,true_hyp_dict, 'b', title_b_10, log_varnames)
       pair_grid_plot(trace_hmc_20_df, ml_deltas_dict_20, true_hyp_dict, 'b', title_b_20, log_varnames)
       pair_grid_plot(trace_hmc_40_df, ml_deltas_dict_40, true_hyp_dict, 'b', title_b_40, log_varnames)

       # Persist traces
       
      with generative_model(X=X_5, y=y_5): trace_hmc_5 = pm.save_trace(trace_hmc_5, directory = results_path + 'traces_hmc/x_5/')
      with generative_model(X=X_10, y=y_10): trace_hmc_10 = pm.save_trace(trace_hmc_10, directory = results_path + 'traces_hmc/x_10/')
      with generative_model(X=X_20, y=y_20): trace_hmc_20 = pm.save_trace(trace_hmc_20, directory = results_path + 'traces_hmc/x_20/')
      with generative_model(X=X_40, y=y_40): trace_hmc_40 = pm.save_trace(trace_hmc_40, directory = results_path + 'traces_hmc/x_40/')
       
       # Predictions
       
       
            
            

            
            
            l = {'log_ls', 'log_n', 'log_s'}
            {key: ml_deltas_dict_5[key] for key in ml_deltas_dict_5.keys() & l}
            
            mf = pm.ADVI(start = )
            fr = pm.FullRankADVI(start = )
      
            tracker_mf = pm.callbacks.Tracker(
            mean = mf.approx.mean.eval,    
            std = mf.approx.std.eval)
            
            tracker_fr = pm.callbacks.Tracker(
            mean = fr.approx.mean.eval,    
            std = fr.approx.std.eval)
      
            mf.fit(callbacks=[tracker_mf], n=25000)
            fr.fit(callbacks=[tracker_fr], n=25000)
            
            trace_mf_10 = mf.approx.sample(2000)
            trace_fr_10 = fr.approx.sample(2000)
          

      trace_mf_10_df = pm.trace_to_dataframe(trace_mf_10)
      trace_fr_10_df = pm.trace_to_dataframe(trace_fr_10)
      
      
      with generative_model(X=X_10, y=y_10):
            
            
            mf = pm.ADVI(start=)
            fr = pm.FullRankADVI()
      
            tracker_mf = pm.callbacks.Tracker(
            mean = mf.approx.mean.eval,    
            std = mf.approx.std.eval)
            
            tracker_fr = pm.callbacks.Tracker(
            mean = fr.approx.mean.eval,    
            std = fr.approx.std.eval)
      
            mf.fit(callbacks=[tracker_mf], n=25000)
            fr.fit(callbacks=[tracker_fr], n=25000)
            
            trace_mf_10 = mf.approx.sample(2000)
            trace_fr_10 = fr.approx.sample(2000)
          

      trace_mf_10_df = pm.trace_to_dataframe(trace_mf_10)
      trace_fr_10_df = pm.trace_to_dataframe(trace_fr_10)
      
      
      
      fig = plt.figure(figsize=(16, 9))
      mu_ax = fig.add_subplot(221)
      std_ax = fig.add_subplot(222)
      hist_ax = fig.add_subplot(212)
      mu_ax.plot(tracker_mf['mean'])
      mu_ax.set_title('Mean track')
      std_ax.plot(tracker_mf['std'])
      std_ax.set_title('Std track')
      hist_ax.plot(mf.hist)
      hist_ax.set_title('Negative ELBO track');
      fig.suptitle(title)

      
      
        with generative_model(X=X_20, y=y_20):
                        
            mf = pm.ADVI()
            fr = pm.FullRankADVI()
      
            tracker_mf = pm.callbacks.Tracker(
            mean = mf.approx.mean.eval,    
            std = mf.approx.std.eval)
            
            tracker_fr = pm.callbacks.Tracker(
            mean = fr.approx.mean.eval,    
            std = fr.approx.std.eval)
      
            mf.fit(n=30000, callbacks=[tracker_mf])
            fr.fit(n=30000, callbacks=[tracker_fr])
            
            trace_mf_20 = mf.approx.sample(4000)
            trace_fr_20 = fr.approx.sample(4000)
          

      trace_hmc_20_df = pm.trace_to_dataframe(trace_hmc_20)
      trace_mf_20_df = pm.trace_to_dataframe(trace_mf_20)
      trace_fr_20_df = pm.trace_to_dataframe(trace_fr_20)
      
      
      # Check convergence of VI - Evolution of means of variational posterior
      # by converting tracker values 
      
      bij_mf = mf.approx.groups[0].bij
      mf_param = {param.name: bij_mf.rmap(param.eval())
	 for param in mf.approx.params}

      bij_fr = fr.approx.groups[0].bij
      fr_param = {param.name: bij_fr.rmap(param.eval())
      	 for param in fr.approx.params}
      
      
      
      # Pair Grid report
      
      pair_grid_plot(trace_hmc_10_df, ml_deltas_dict_10, 'b')
      pair_grid_plot(trace_mf_10_df, ml_deltas_dict_10, 'coral')
      pair_grid_plot(trace_fr_10_df, ml_deltas_dict_10, 'g')

      # Marginal Posterior report
      
      trace_report(trace_hmc_10, trace_mf_10, trace_fr_10)
      
      
      # Autocorrelation report
      
      
      # Predictive distribution 



      



pp_mean_hmc_10, pp_std_hmc_10, means_10, std_10, sq_10 = get_posterior_predictive_gp_trace(trace_hmc_10, 10, X_star_10, path, 10)
pp_mean_hmc_20, pp_std_hmc_20, means_20, std_20, sq_20 = get_posterior_predictive_gp_trace(trace_hmc_20, 10, X_star_20, path, 20)
pp_mean_hmc_40, pp_std_hmc_40, means_40, std_40, sq_40 = get_posterior_predictive_gp_trace(trace_hmc_40, 10, X_star_40, path, 40)
pp_mean_hmc_60, pp_std_hmc_60, means_60, std_60, sq_60 = get_posterior_predictive_gp_trace(trace_hmc_60, 10, X_star_60, path, 60)


plt.figure(figsize=(20,5))
plt.plot(X_star_10, np.mean(pp_mean_hmc_10['f_pred'], axis=0), 'b', alpha=0.4)
plt.plot(X_star_20, np.mean(pp_mean_hmc_20['f_pred'], axis=0), 'b', alpha=0.4)
plt.plot(X_star_40, np.mean(pp_mean_hmc_40['f_pred'], axis=0), 'b', alpha=0.4)
plt.plot(X_star_60, np.mean(pp_mean_hmc_60['f_pred'], axis=0), 'b', alpha=0.4)

plt.plot(X_star_10, f_star_10, 'k', linestyle='dashed')

plt.plot(X_star_10, pp_mean_hmc_10['f_pred'].T, 'b', alpha=0.4)





# Handling HMC traces for N_train
      
      
# Handling HMC traces for SNR
      

# Hamdling HMC traces for Unif / NUnif