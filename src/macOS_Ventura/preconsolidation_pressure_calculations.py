"""
Create the functions to:
1. obtain the data points lying on the compressibility curve
2. determine preconsolidation pressure objectively and 
3. plot accompanying graphs

Preconsolidation pressure is calculated objectively with three methods:
1. Casagrande Method 
2. Oikawa Method
3. Maximum Curvature Method (Gregory et al.) 

e = void ratio; p = stress; 1+e = specific volume

# code by Ang Wei Jian
# 16 Apr 2023
"""


# ### Imports
# Import libraries and write settings here.
import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline
from scipy.optimize import curve_fit



matplotlib.use('PDF')
# change the default interactive matplotlib backend to "non-interactive" PDF backend --> prevent memory leakage/overflow (results in segmentation fault i.e. exit code 11)
# http://datasideoflife.com/?p=1443
# https://matplotlib.org/stable/users/explain/backends.html


###--------------------------
# ### Select all Data Points along Compressibility Curve
# Obtain data points on the compressibility curve for the purpose of curve fitting
# Identify all unload-reload data points which do not lie on the sigmoidal compressibility curve
# Exclude these points for subsequent curve fitting of sigmoidal compressibility curve

def select_data_points_on_compressibility_curve(df, x='CONS_INCF', y='CONS_INCE'):
# to exclude all unload-reload data point for curve fitting
# identify key indices (i.e when unloading first takes place? when reloading ends?)
    
    hasFinalUnload = False
    stress = df[x].values
    void = df[y].values
    vol = 1 + void
    num_data = df.shape[0]

    idx_init_unload = [i for i in range(num_data-1) if (stress[i] > stress[i+1]) & (stress[i] > stress[i-1])]
        
    idx_end_reload = []
    for j in range(len(idx_init_unload)):
        idx_end_reload.append(next((i for i in range(num_data-1) if (stress[i] > stress[idx_init_unload[j]])), 'FINAL UNLOAD INCLUDED'))

    # check if the final unloading step is in the data
    if 'FINAL UNLOAD INCLUDED' in idx_end_reload:
        hasFinalUnload = True
        idx_end_reload.pop()

    num_unload = len(idx_init_unload)
    num_reload = len(idx_end_reload)

    # identify data which is not part of the compressibility curve (i.e. unload/reload data)
    # hence, identify data which is part of the compressibility curve

    idx_not_cc = []

    for j in range(num_reload):
        idx_not_cc = idx_not_cc + list(range(idx_init_unload[j] + 1, idx_end_reload[j]))

    #  ignore final unload data (if it is included)
    if hasFinalUnload:
        idx_not_cc = idx_not_cc + list(range(idx_init_unload[-1] + 1, num_data))

    idx_cc = [i for i in range(num_data) if i not in idx_not_cc]

    # filter out data which is part of the compressibility curve for subsequent curve fitting exercise
    stress_cc = stress[idx_cc]
    void_cc = void[idx_cc]

    idx_init_first_unload = idx_init_unload [0] 

    return stress_cc, void_cc, idx_init_first_unload



# ### Perform Casagrande Method and Plot Relevant Graph (if printer==True)

# plot e vs log(p)
# fit compressibility curve with cubic spline interpolation
# identify maximum curvature point (mcp) using curvature function k, and draw bisector line (based on the tangent of fitted compressibility curve at mcp)
# the equation of the virgin compression line = equation of the steepest tangent of fitted compressibility curve (i.e. most negative tangent)
# printer==True --> plot relevant graphs and save figures

def calculate_pc_Casagrande(df, title, folder_path_output, x='CONS_INCF', y='CONS_INCE', const='CONG_PRCP',
               label_x=r"Effective Vertical Stress, $\sigma_v'$  [kPa]",
               label_y='Void Ratio, e [-]', printer=True, troubleshoot_mode=False):
   

    stress = df[x].values
    void = df[y].values
    pc = df[const].values[0]

    # to fit sigmoidal compressibility curve for linear(e)-log(stress) scale (i.e. Casagrande Method) using cubic spline
    stress_cc, void_cc, idx_init_first_unload = select_data_points_on_compressibility_curve(df)
    stress_cc_log = np.log10(stress_cc)
    stress_fitted = np.logspace(np.log10(min(stress_cc)),np.log10(max(stress_cc)),1000)

    # interpolate data with a piecewise cubic polynomial 
    # which is twice continuously differentiable (important to calculate maximum curvature point)
    cs_ca = CubicSpline(x=stress_cc_log, y=void_cc)
    void_fitted_cs = cs_ca(np.log10(stress_fitted))


    ## Casagrande Method
    # 1.calculate the derivative
    # 1a. calcalate the second derivate d2ydx2
    # 1b. check for an inflexion point - if there's one, disregard all the data points beyond the first inflexion point
    # 2.obtain eqn of virgin compression line = tangent at point of steepest gradient (i.e. L1)
    # 3.identify maximum curvature point (mcp)
    # 4.obtain equation of bisector line (i.e. L2)
    # 5.find intersection of L1 and L2
    # 6.obtain equation of tangent at mcp (i.e. L3) --> for the purpose of plotting

    # 1.calculate the first derivative
    grad_cs = cs_ca(np.log10(stress_fitted), 1)

    # 1a. calcalate the second derivate d2ydx2
    grad2_cs = cs_ca(np.log10(stress_fitted), 2)

    # 1b. obtain all the inflexion points - if there's one, disregard all the data points beyond the first inflexion point
    # - find all the inflexion points (where d2ydx2 = 0 or d2yd2x change signs AND after first unload)
    idx_inflexion = [i for i in range(len(stress_fitted)-1) 
                     if (grad2_cs[i+1] * grad2_cs[i] < 0) and (stress_fitted[i] > stress[idx_init_first_unload])]

    hasInflexionPoint = len(idx_inflexion) > 0
    if hasInflexionPoint:
        idx_first_inflexion_point = idx_inflexion[0]  

    # 2.obtain eqn of virgin compression line = tangent at point of steepest gradient (i.e. L1)
    # since all gradients are negative, we are looking for the minimum gradient (i.e. most negative)
    # ignore data points beyond the first inflexion point
    if hasInflexionPoint:
        grad_cs = grad_cs[:idx_first_inflexion_point]
    idx_min_grad_cs = np.argmin(grad_cs)
    # known points on L1: x0 and y0
    x0_L1 = np.log10(stress_fitted)[idx_min_grad_cs]
    y0_L1 = void_fitted_cs[idx_min_grad_cs]
    # L1 = [gradient, y_intercept]
    # (y0 - y_intercept)/(x0 - 0) = grad
    L1 = [grad_cs[idx_min_grad_cs], y0_L1 - grad_cs[idx_min_grad_cs] * x0_L1]
    print(L1)

    # 3.identify maximum curvature point
    # # https://tutorial.math.lamar.edu/classes/calciii/curvature.aspx
    # calculate the first derivative
    grad_cs = cs_ca(np.log10(stress_fitted), 1)
    # calculate the second derivative
    grad2_cs = cs_ca(np.log10(stress_fitted), 2)
    # calculate the curvature
    k_cs = np.abs(grad2_cs)/((1+grad_cs**2)**(3/2))
    # ignore data points beyond the first inflexion point
    if hasInflexionPoint:
        k_cs_full = k_cs
        k_cs = k_cs[:idx_first_inflexion_point]
    idx_max_k_cs = np.argmax(k_cs)
    # x0_mcp and y0_mcp (i.e. coordinates of maximum curvature point mcp)
    x0_mcp = np.log10(stress_fitted)[idx_max_k_cs]
    y0_mcp = void_fitted_cs[idx_max_k_cs]
    mcp = [np.power(10,x0_mcp), y0_mcp]

    # 4.obtain equation of bisector line (L2) at mcp
    grad_mcp = grad_cs[idx_max_k_cs]
    grad_bs = 1/2 * grad_mcp
    # L2 = [gradient, y_intercept]
    # (y0 - y_intercept)/(x0 - 0) = grad
    L2 = [grad_bs, y0_mcp - grad_bs * x0_mcp]
    print(L2)

    # 5. find intersection of two lines (L1 = L2)
    # m1 * x1 + c1 = m2 * x2 + c2
    inter_x = np.power(10, (L2[1]-L1[1])/(L1[0]-L2[0]))
    inter_y = L1[0] * np.log10(inter_x) + L1[1]
    pc_ca = inter_x
    # err_ca = (pc_ca-pc)/pc*100
    # error calculated as below will penalise over-estimation of pc much more
    err_ca = (pc-pc_ca)/pc_ca*100

    # 6. obtain equation of tangent line at mcp (i.e. L3)
    # L3 = [gradient, y_intercept]
    # (y0 - y_intercept)/(x0 - 0) = grad
    L3 = [grad_mcp, y0_mcp - grad_mcp * x0_mcp]
    print(L3)

    ## plot the graph to illustrate Casagrande Method if printer is set to be True
    if printer==True: 

        if troubleshoot_mode:
            nrows=2
        else:
            nrows=1

        fig, ax = plt.subplots(nrows=nrows, figsize=(11.69, 8.27))   
        fig.suptitle(title, fontsize=16)

        if troubleshoot_mode:
            ax0=ax[0]
            ax1=ax[1]
        else:
            ax0=ax

        # plot intersection point (i.e. preconsolidation pressure obtained from Casagrande method)
        ax0.plot(stress, void, '-s', color='grey', markerfacecolor='none')
        ax0.plot(stress_fitted, void_fitted_cs, ':', color='grey')
        ax0.plot([pc_ca, pc_ca], [min(void_cc), max(void_cc)], '--b')

        # plot virgin compression line = tangent at point of steepest gradient (i.e. L1); truncated slightly after intersection point
        stress_fitted_L1 = [i for i in stress_fitted if i > 0.7 * pc_ca]
        ax0.plot(stress_fitted_L1, L1[0] * np.log10(stress_fitted_L1) + L1[1], ':r')

        # plot equation of bisector line at mcp (i.e. L2); truncated slightly after intersection point
        stress_fitted_L2 = [i for i in stress_fitted if (i > mcp[0]) & (i < 1.3 * pc_ca)]
        ax0.plot(stress_fitted_L2, L2[0] * np.log10(stress_fitted_L2) + L2[1], ':r')
        ax0.plot(mcp[0],mcp[1],'or')

        # lot equation of tangent line at mcp (i.e. L3)
        stress_fitted_L3 = [i for i in stress_fitted if (i > mcp[0]) & (i < 1.3 * pc_ca)]
        ax0.plot(stress_fitted_L3, L3[0] * np.log10(stress_fitted_L3) + L3[1], ':r')

        # plot equation of horizontal line (i.e. L4) at mcp 
        ax0.plot(stress_fitted_L3, np.zeros((len(stress_fitted_L3),1)) + y0_mcp, ':r')

        # plot recorded preconsolidation pressure pc
        ax0.plot([pc, pc],[min(void),max(void)],'--g')

        if troubleshoot_mode:
            # plot inflexion point and curvature
            ax1.plot(stress_fitted, grad2_cs, 'm', label='d2y/dx2')
            ax1.plot(stress_fitted, grad_cs, 'c', label='Gradient')
            ax1.set_xscale('log') 
            
            if hasInflexionPoint:
                ax1.plot(stress_fitted, k_cs_full, 'r', label='Curvature')
                ax1.plot([stress_fitted[idx_first_inflexion_point], stress_fitted[idx_first_inflexion_point]], [min(grad2_cs), max(grad2_cs)],':m')
                ax1.plot([max(stress_fitted),min(stress_fitted)], [0, 0],':m')
                ax0.plot(stress_fitted[idx_first_inflexion_point], void_fitted_cs[idx_first_inflexion_point],'om')
                ax0.plot([stress_fitted[idx_first_inflexion_point], stress_fitted[idx_first_inflexion_point]], [min(void),max(void)],':m')
            else:
                ax1.plot(stress_fitted, k_cs, 'r', label='Curvature')

            ax1.legend(loc="lower right")

        ax0.set_xscale('log')
        ax0.set_xlabel(label_x)
        ax0.set_ylabel(label_y)

        ax0.text(1, 0.99, f"recorded $\sigma_p'$ = {pc:.1f} kPa", 
             ha='right', va='top', transform=ax0.transAxes, color='g')
        ax0.text(1, 0.96, f"calculated $\sigma_p'$ = {pc_ca:.1f} kPa", 
             ha='right', va='top', transform=ax0.transAxes, color='b')
        ax0.text(1, 0.93, f"% difference from calculated value = {err_ca:.1f}%", 
             ha='right', va='top', transform=ax0.transAxes)

        fig.tight_layout()  # otherwise the right y-label is slightly clipped
        fig.savefig(os.path.join(folder_path_output, title + '.pdf'))

        # close figure 
        plt.close()

    return pc_ca, err_ca


###--------------------------
# ### Perform Oikawa Method and Plot Relevant Graph (if printer==True)

# plot log(1+e) vs log(p)
# specific volume, vol = 1 + e
# fit compressibility curve with cubic spline interpolation (cs)
# the equation of the recompression line = straight line connecting the first 2 data points
# the equation of the virgin compression line = equation of the steepest tangent of fitted compressibility curve (i.e. most negative tangent)
# printer==True --> plot relevant graphs and save figures

def calculate_pc_Oikawa(df, title, folder_path_output, x='CONS_INCF', y='CONS_INCE', const='CONG_PRCP',
               label_x=r"Effective Vertical Stress, $\sigma_v'$  [kPa]",
               label_y='Log (1 + Void Ratio, e) [-]', printer=True, troubleshoot_mode=False):

    stress = df[x].values
    void = df[y].values
    pc = df[const].values[0]

    # to fit sigmoidal compressibility curve for log(1+e)-log(stress) scale (i.e. Oikawa Method) using cubic spline
    stress_cc, void_cc, idx_init_first_unload = select_data_points_on_compressibility_curve(df)
    stress_cc_log = np.log10(stress_cc)
    stress_fitted = np.logspace(np.log10(min(stress_cc)),np.log10(max(stress_cc)),1000)
    
    vol = 1 + void
    vol_log = [np.log10(i) for i in vol]
    vol_cc = 1 + void_cc
    vol_cc_log = [np.log10(i) for i in vol_cc]

    # interpolate data with a piecewise cubic polynomial 
    # which is twice continuously differentiable (important to calculate maximum curvature point)
    # cs(sigmaCS,1) --> first derivative
    cs_oi = CubicSpline(x=stress_cc_log, y=vol_cc_log)
    vol_fitted_cs = cs_oi(np.log10(stress_fitted))


    ## Oikawa Method
    # 1.calculate the derivative
    # 1a. calcalate the second derivate d2ydx2
    # 1b. check for an inflexion point - if there's one, disregard all the data points beyond the first inflexion point
    # 2.obtain eqn of virgin compression line = tangent at point of steepest gradient (i.e. L1)
    # 3.obtain eqn of recompression line = straight line connecting the first two data points (i.e. L2)
    # 4.find intersection of L1 and L2

    # 1. calculate the derivative
    grad_cs = cs_oi(np.log10(stress_fitted), 1)

    # 1a. calcalate the second derivate d2ydx2
    grad2_cs = cs_oi(np.log10(stress_fitted), 2)

    # 1b. obtain all the inflexion points - if there's one, disregard all the data points beyond the first inflexion point
    # - find all the inflexion points (where d2ydx2 = 0 or d2yd2x change signs AND after first unload)
    idx_inflexion = [i for i in range(len(stress_fitted)-1) 
                 if (grad2_cs[i+1] * grad2_cs[i] < 0) and (stress_fitted[i] > stress[idx_init_first_unload])]

    hasInflexionPoint = len(idx_inflexion) > 0
    if hasInflexionPoint:
        idx_first_inflexion_point = idx_inflexion[0]  

    # 2. obtain eqn of virgin compression line = tangent at point of steepest gradient (L1)
    # since all gradients are negative, we are looking for the minimum gradient (i.e. most negative)
    # ignore data points beyond the first inflexion point
    if hasInflexionPoint:
        grad_cs_full = grad_cs
        grad_cs = grad_cs[:idx_first_inflexion_point]
    idx_min_grad_cs = np.argmin(grad_cs)
    # known points on L1: x0 and y0
    x0_L1 = np.log10(stress_fitted)[idx_min_grad_cs]
    y0_L1 = vol_fitted_cs[idx_min_grad_cs]
    # L1 = [gradient, y_intercept]
    # (y0 - y_intercept)/(x0 - 0) = grad
    L1 = [grad_cs[idx_min_grad_cs], y0_L1 - grad_cs[idx_min_grad_cs] * x0_L1]
    print(L1)

    # 3. obtain eqn of recompression line = straight line connecting the first two data points (i.e. L2)
    # known points on L2: x0, y0, x1, y1 (i.e. first and second data point in compressibility curve)
    x0_L2 = stress_cc_log[0]
    y0_L2 = vol_cc_log[0]
    x1_L2 = stress_cc_log[1]
    y1_L2 = vol_cc_log[1]
    grad_L2 = (y0_L2 - y1_L2) / (x0_L2 - x1_L2)
    # L2 = [gradient, y_intercept]
    # (y0 - y_intercept)/(x0 - 0) = grad
    L2 = [grad_L2, y0_L2 - grad_L2 * x0_L2]
    print(L2)

    # 4. find intersection of two lines (L1 = L2)
    # m1 * x1 + c1 = m2 * x2 + c2
    inter_x = np.power(10, (L2[1]-L1[1])/(L1[0]-L2[0]))
    inter_y = L1[0] * np.log10(inter_x) + L1[1]
    pc_oi = inter_x
    # err_oi = (pc_oi-pc)/pc*100
    # error calculated as below will penalise over-estimation of pc much more
    err_oi = (pc-pc_oi)/pc_oi*100


    ## plot the graph to illustrate Oikawa Method if printer is set to be True
    if printer==True: 

        if troubleshoot_mode:
            nrows=2
        else:
            nrows=1

        fig, ax = plt.subplots(nrows=nrows, figsize=(11.69, 8.27))   
        fig.suptitle(title, fontsize=16)

        if troubleshoot_mode:
            ax0=ax[0]
            ax1=ax[1]
        else:
            ax0=ax
        
        # plot intersction point (i.e. preconsolidation pressure obtained from Oikawa method)
        ax0.plot(stress, vol_log, '-s', color='grey', markerfacecolor='none')
        ax0.plot(stress_fitted, vol_fitted_cs, ':', color='grey')
        ax0.plot([pc_oi, pc_oi], [min(vol_cc_log), max(vol_cc_log)], '--b')

        # plot virgin compression line = tangent at point of steepest gradient (i.e. L1); truncated slightly after intersection point
        stress_fitted_L1 = [i for i in stress_fitted if i > 0.7 * pc_oi]
        ax0.plot(stress_fitted_L1, L1[0] * np.log10(stress_fitted_L1) + L1[1], ':r')

        # plot recompression line = tangent at point of gentlest gradient (i.e. L2); truncated slightly after intersection point
        stress_fitted_L2 = [i for i in stress_fitted if i < 1.3 * pc_oi]
        ax0.plot(stress_fitted_L2, L2[0] * np.log10(stress_fitted_L2) + L2[1], ':r')

        # plot recorded preconsolidation pressure pc
        ax0.plot([pc, pc],[min(vol_log),max(vol_log)],'--g')

        if troubleshoot_mode:
            # plot inflexion point and curvature
            ax1.plot(stress_fitted, grad2_cs, 'm', label='d2y/dx2')
            ax1.set_xscale('log') 
            
            if hasInflexionPoint:
                ax1.plot(stress_fitted, grad_cs_full, 'c', label='Gradient')
                ax1.plot([stress_fitted[idx_first_inflexion_point], stress_fitted[idx_first_inflexion_point]], [min(grad2_cs), max(grad2_cs)],':m')
                ax1.plot([max(stress_fitted),min(stress_fitted)], [0, 0],':m')
                ax0.plot(stress_fitted[idx_first_inflexion_point], vol_fitted_cs[idx_first_inflexion_point],'om')
                ax0.plot([stress_fitted[idx_first_inflexion_point], stress_fitted[idx_first_inflexion_point]], [min(vol_log), vol_fitted_cs[idx_first_inflexion_point]],':m')
            else: 
                ax1.plot(stress_fitted, grad_cs, 'c', label='Gradient')

            ax1.legend(loc="lower right")

        ax0.set_xscale('log')    
        ax0.set_xlabel(label_x)
        ax0.set_ylabel(label_y)

        ax0.text(1, 0.99, f"recorded $\sigma_p'$ = {pc:.1f} kPa", 
           ha='right', va='top', transform=ax0.transAxes, color='g')
        ax0.text(1, 0.96, f"calculated $\sigma_p'$ = {pc_oi:.1f} kPa", 
           ha='right', va='top', transform=ax0.transAxes, color='b')
        ax0.text(1, 0.93, f"% difference from calculated value = {err_oi:.1f}%", 
           ha='right', va='top', transform=ax0.transAxes)

        fig.tight_layout()  # otherwise the right y-label is slightly clipped
        fig.savefig(os.path.join(folder_path_output, title + '.pdf'))

        # close figure 
        plt.close()   

    return pc_oi, err_oi



# ### Perform Maximum Curvature Method (by Gregory et al.) and Plot Relevant Graph (if printer==True)

# https://www.sciencedirect.com/science/article/abs/pii/S0167198705001868?via%3Dihub
# plot e vs log(p)
# fit compressibility curve with Gompertz Function (gp)
# identify maximum curvature point (mcp) using curvature function k = preconsolidation pressure

def calculate_pc_MC(df, title, folder_path_output, x='CONS_INCF', y='CONS_INCE', const='CONG_PRCP',
               label_x=r"Effective Vertical Stress, $\sigma_v'$  [kPa]",
               label_y='Void Ratio, e [-]', printer=True, troubleshoot_mode=False):

    stress = df[x].values
    void = df[y].values
    pc = df[const].values[0]

    # to fit sigmoidal compressibility curve for linear(e)-log(stress) scale using Gompertz function (gp)
    # https://www.sciencedirect.com/science/article/abs/pii/S0167198705001868?via%3Dihub
    stress_cc, void_cc, _ = select_data_points_on_compressibility_curve(df)
    stress_cc_log = np.log10(stress_cc)
    stress_fitted = np.logspace(np.log10(min(stress_cc)),np.log10(max(stress_cc)),1000)

    # https://stackoverflow.com/questions/15831763/scipy-curvefit-runtimeerroroptimal-parameters-not-found-number-of-calls-to-fun

    gp_params, pcov = curve_fit(gp, stress_cc_log, void_cc, p0 = [1, 1, 1, 1], maxfev=5000) 
    # if the condition number is very big, it suggests unreliable covariance matrices and failed curve fitting --> try again with a different set of initial parameters. 
    if np.linalg.cond(pcov) > 10**10:
        gp_params, pcov = curve_fit(gp, stress_cc_log, void_cc, p0 = [2, 2, 2, 2], maxfev=5000)

    a, b, c, m = gp_params

    void_fitted_gp = gp(np.log10(stress_fitted),*gp_params)

    # Maximum Curvature method (mc) # and Gompertz Function fitted curve (gp)

    # 1.calculate the first derivative
    # 2.calculate the second derivative
    # 3.identify maximum curvature point (= preconsolidation pressure)
    
    # 1.calculate the first derivative
    # First Derivative of Gompertz Function (calculate by hand / follow Gregory et al.)
    # https://www.sciencedirect.com/science/article/abs/pii/S0167198705001868?via%3Dihub
    x = np.log10(stress_fitted)
    grad_gp = b*c*np.exp(-np.exp(b*(x-m)) * -np.exp(b*(x-m)))

    # 2.calculate the second derivative
    # Second Derivative of Gompertz Function (calculate by hand / follow Gregory et al.)
    # https://www.sciencedirect.com/science/article/abs/pii/S0167198705001868?via%3Dihub
    grad2_gp = b*b*c*np.exp(-np.exp(b*(x-m))) * np.exp(b*(x-m)) * (np.exp(b*(x-m)) - 1)

    # 3.identify maximum curvature point (= preconsolidation pressure)
    # # https://tutorial.math.lamar.edu/classes/calciii/curvature.aspx
    # calculate the curvature
    k_gp = np.abs(grad2_gp)/((1+grad_gp**2)**(3/2))
    idx_max_k_gp = np.argmax(k_gp)
    # x0_mcp and y0_mcp (i.e. coordinates of maximum curvature point mcp)
    x0_mcp = np.log10(stress_fitted)[idx_max_k_gp]
    y0_mcp = void_fitted_gp[idx_max_k_gp]
    mcp = [np.power(10,x0_mcp), y0_mcp]
    pc_mc = mcp[0]
    inter_x = mcp[0]
    inter_y = mcp[1]

    # err_mc = (pc_mc-pc)/pc*100
    # error calculated as below will penalise over-estimation of pc much more
    err_mc = (pc-pc_mc)/pc_mc*100

    ## plot the graph to illustrate Maximum Curvature Method if printer is set to be True
    if printer==True: 

        if troubleshoot_mode:
            nrows=2
        else:
            nrows=1

        fig, ax = plt.subplots(nrows=nrows, figsize=(11.69, 8.27))   
        fig.suptitle(title, fontsize=16)

        if troubleshoot_mode:
            ax0=ax[0]
            ax1=ax[1]
        else:
            ax0=ax

        # plot mcp = preconsolidation pressure (i.e. preconsolidation pressure obtained from Maximum Curvature method)
        ax0.plot(stress, void, '-s', color='grey', markerfacecolor='none')
        ax0.plot(stress_fitted, void_fitted_gp, ':', color='grey')
        ax0.plot(mcp[0],mcp[1],'or')
        ax0.plot([pc_mc, pc_mc], [min(void), max(void)], '--b')

        # plot recorded preconsolidation pressure pc
        ax0.plot([pc, pc],[min(void),max(void)],'--g')

        if troubleshoot_mode:
            # plot inflexion point and curvature
            ax1.plot(stress_fitted, k_gp, 'r', label='Curvature')
            ax1.set_xscale('log') 
            ax1.legend(loc="lower right")

        ax0.set_xscale('log')    
        ax0.set_xlabel(label_x)
        ax0.set_ylabel(label_y)

        ax0.text(1, 0.99, f"recorded $\sigma_p'$ = {pc:.1f} kPa", 
           ha='right', va='top', transform=ax0.transAxes, color='g')
        ax0.text(1, 0.96, f"calculated $\sigma_p'$ = {pc_mc:.1f} kPa", 
           ha='right', va='top', transform=ax0.transAxes, color='b')
        ax0.text(1, 0.93, f"% difference from calculated value = {err_mc:.1f}%", 
           ha='right', va='top', transform=ax0.transAxes)

        fig.tight_layout()  # otherwise the right y-label is slightly clipped
        fig.savefig(os.path.join(folder_path_output, title + '.pdf'))

        # close figure 
        plt.close()   

    return pc_mc, err_mc



# ### Gompertz Function 

def gp(x,a,b,c,m):
    # https://en.wikipedia.org/wiki/Gompertz_function
    # https://stackoverflow.com/questions/21922340/getting-completely-wrong-fit-from-python-scipy-optimize-curve-fit
    # https://www.sciencedirect.com/science/article/abs/pii/S0167198705001868?via%3Dihub
    return a + c*(np.exp(-np.exp(b*(x-m))))


