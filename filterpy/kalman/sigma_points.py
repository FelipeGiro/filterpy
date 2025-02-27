# -*- coding: utf-8 -*-
# pylint: disable=invalid-name, too-many-instance-attributes

"""Copyright 2015 Roger R Labbe Jr.

FilterPy library.
http://github.com/rlabbe/filterpy

Documentation at:
https://filterpy.readthedocs.org

Supporting book at:
https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python

This is licensed under an MIT license. See the readme.MD file
for more information.
"""

from __future__ import division
import numpy as np
from scipy.linalg import cholesky
from filterpy.common import pretty_str

class MerweScaledSigmaPoints(object):

    """
    Generates sigma points and weights according to Van der Merwe's
    2004 dissertation[1] for the UnscentedKalmanFilter class.. It
    parametizes the sigma points using alpha, beta, kappa terms, and
    is the version seen in most publications.

    Unless you know better, this should be your default choice.

    Parameters
    ----------

    n : int
        Dimensionality of the state. 2n+1 weights will be generated.

    alpha : float
        Determins the spread of the sigma points around the mean.
        Usually a small positive value (1e-3) according to [3].

    beta : float
        Incorporates prior knowledge of the distribution of the mean. For
        Gaussian x beta=2 is optimal, according to [3].

    kappa : float, default=0.0
        Secondary scaling parameter usually set to 0 according to [4],
        or to 3-n according to [5].

    sqrt_method : function(ndarray), default=scipy.linalg.cholesky
        Defines how we compute the square root of a matrix, which has
        no unique answer. Cholesky is the default choice due to its
        speed. Typically your alternative choice will be
        scipy.linalg.sqrtm. Different choices affect how the sigma points
        are arranged relative to the eigenvectors of the covariance matrix.
        Usually this will not matter to you; if so the default cholesky()
        yields maximal performance. As of van der Merwe's dissertation of
        2004 [6] this was not a well reseached area so I have no advice
        to give you.

        If your method returns a triangular matrix it must be upper
        triangular. Do not use numpy.linalg.cholesky - for historical
        reasons it returns a lower triangular matrix. The SciPy version
        does the right thing.

    subtract : callable (x, y), optional
        Function that computes the difference between x and y.
        You will have to supply this if your state variable cannot support
        subtraction, such as angles (359-1 degreees is 2, not 358). x and y
        are state vectors, not scalars.

    Attributes
    ----------

    Wm : np.array
        weight for each sigma point for the mean

    Wc : np.array
        weight for each sigma point for the covariance

    Examples
    --------

    See my book Kalman and Bayesian Filters in Python
    https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python


    References
    ----------

    .. [1] R. Van der Merwe "Sigma-Point Kalman Filters for Probabilitic
           Inference in Dynamic State-Space Models" (Doctoral dissertation)

    """


    def __init__(self, n, alpha, beta, kappa, sqrt_method=None, subtract=None):
        #pylint: disable=too-many-arguments

        self.n = n
        self.alpha = alpha
        self.beta = beta
        self.kappa = kappa
        if sqrt_method is None:
            self.sqrt = cholesky
        else:
            self.sqrt = sqrt_method

        if subtract is None:
            self.subtract = np.subtract
        else:
            self.subtract = subtract

        self._compute_weights()


    def num_sigmas(self):
        """ Number of sigma points for each variable in the state x"""
        return 2*self.n + 1


    def sigma_points(self, x, P):
        """ Computes the sigma points for an unscented Kalman filter
        given the mean (x) and covariance(P) of the filter.
        Returns tuple of the sigma points and weights.

        Works with both scalar and array inputs:
        sigma_points (5, 9, 2) # mean 5, covariance 9
        sigma_points ([5, 2], 9*eye(2), 2) # means 5 and 2, covariance 9I

        Parameters
        ----------

        x : An array-like object of the means of length n
            Can be a scalar if 1D.
            examples: 1, [1,2], np.array([1,2])

        P : scalar, or np.array
           Covariance of the filter. If scalar, is treated as eye(n)*P.

        Returns
        -------

        sigmas : np.array, of size (n, 2n+1)
            Two dimensional array of sigma points. Each column contains all of
            the sigmas for one dimension in the problem space.

            Ordered by Xi_0, Xi_{1..n}, Xi_{n+1..2n}
        """

        if self.n != np.size(x):
            raise ValueError("expected size(x) {}, but size is {}".format(
                self.n, np.size(x)))

        n = self.n

        if np.isscalar(x):
            x = np.asarray([x])

        if  np.isscalar(P):
            P = np.eye(n)*P
        else:
            P = np.atleast_2d(P)

        lambda_ = self.alpha**2 * (n + self.kappa) - n
        U = self.sqrt((lambda_ + n)*P)

        sigmas = np.zeros((2*n+1, n))
        sigmas[0] = x
        for k in range(n):
            # pylint: disable=bad-whitespace
            sigmas[k+1]   = self.subtract(x, -U[k])
            sigmas[n+k+1] = self.subtract(x, U[k])

        return sigmas


    def _compute_weights(self):
        """ Computes the weights for the scaled unscented Kalman filter.

        """

        n = self.n
        lambda_ = self.alpha**2 * (n +self.kappa) - n

        c = .5 / (n + lambda_)
        self.Wc = np.full(2*n + 1, c)
        self.Wm = np.full(2*n + 1, c)
        self.Wc[0] = lambda_ / (n + lambda_) + (1 - self.alpha**2 + self.beta)
        self.Wm[0] = lambda_ / (n + lambda_)



    def __repr__(self):

        return '\n'.join([
            'MerweScaledSigmaPoints object',
            pretty_str('n', self.n),
            pretty_str('alpha', self.alpha),
            pretty_str('beta', self.beta),
            pretty_str('kappa', self.kappa),
            pretty_str('Wm', self.Wm),
            pretty_str('Wc', self.Wc),
            pretty_str('subtract', self.subtract),
            pretty_str('sqrt', self.sqrt)
            ])


class JulierSigmaPoints(object):
    """
    Generates sigma points and weights according to Simon J. Julier
    and Jeffery K. Uhlmann's original paper[1]. It parametizes the sigma
    points using kappa.

    Parameters
    ----------

    n : int
        Dimensionality of the state. 2n+1 weights will be generated.

    kappa : float, default=0.
        Scaling factor that can reduce high order errors. kappa=0 gives
        the standard unscented filter. According to [Julier], if you set
        kappa to 3-dim_x for a Gaussian x you will minimize the fourth
        order errors in x and P.

    sqrt_method : function(ndarray), default=scipy.linalg.cholesky
        Defines how we compute the square root of a matrix, which has
        no unique answer. Cholesky is the default choice due to its
        speed. Typically your alternative choice will be
        scipy.linalg.sqrtm. Different choices affect how the sigma points
        are arranged relative to the eigenvectors of the covariance matrix.
        Usually this will not matter to you; if so the default cholesky()
        yields maximal performance. As of van der Merwe's dissertation of
        2004 [6] this was not a well reseached area so I have no advice
        to give you.

        If your method returns a triangular matrix it must be upper
        triangular. Do not use numpy.linalg.cholesky - for historical
        reasons it returns a lower triangular matrix. The SciPy version
        does the right thing.

    subtract : callable (x, y), optional
        Function that computes the difference between x and y.
        You will have to supply this if your state variable cannot support
        subtraction, such as angles (359-1 degreees is 2, not 358). x and y

    Attributes
    ----------

    Wm : np.array
        weight for each sigma point for the mean

    Wc : np.array
        weight for each sigma point for the covariance

    References
    ----------

    .. [1] Julier, Simon J.; Uhlmann, Jeffrey "A New Extension of the Kalman
        Filter to Nonlinear Systems". Proc. SPIE 3068, Signal Processing,
        Sensor Fusion, and Target Recognition VI, 182 (July 28, 1997)
   """

    def __init__(self, n, kappa=0., sqrt_method=None, subtract=None):

        self.n = n
        self.kappa = kappa
        if sqrt_method is None:
            self.sqrt = cholesky
        else:
            self.sqrt = sqrt_method

        if subtract is None:
            self.subtract = np.subtract
        else:
            self.subtract = subtract

        self._compute_weights()


    def num_sigmas(self):
        """ Number of sigma points for each variable in the state x"""
        return 2*self.n + 1


    def sigma_points(self, x, P):
        r""" Computes the sigma points for an unscented Kalman filter
        given the mean (x) and covariance(P) of the filter.
        kappa is an arbitrary constant. Returns sigma points.

        Works with both scalar and array inputs:
        sigma_points (5, 9, 2) # mean 5, covariance 9
        sigma_points ([5, 2], 9*eye(2), 2) # means 5 and 2, covariance 9I

        Parameters
        ----------

        x : array-like object of the means of length n
            Can be a scalar if 1D.
            examples: 1, [1,2], np.array([1,2])

        P : scalar, or np.array
           Covariance of the filter. If scalar, is treated as eye(n)*P.

        kappa : float
            Scaling factor.

        Returns
        -------

        sigmas : np.array, of size (n, 2n+1)
            2D array of sigma points :math:`\chi`. Each column contains all of
            the sigmas for one dimension in the problem space. They
            are ordered as:

            .. math::
                :nowrap:

                \begin{eqnarray}
                  \chi[0]    = &x \\
                  \chi[1..n] = &x + [\sqrt{(n+\kappa)P}]_k \\
                  \chi[n+1..2n] = &x - [\sqrt{(n+\kappa)P}]_k
                \end{eqnarray}

        """

        if self.n != np.size(x):
            raise ValueError("expected size(x) {}, but size is {}".format(
                self.n, np.size(x)))

        n = self.n

        if np.isscalar(x):
            x = np.asarray([x])

        n = np.size(x)  # dimension of problem

        if np.isscalar(P):
            P = np.eye(n) * P
        else:
            P = np.atleast_2d(P)

        sigmas = np.zeros((2*n+1, n))

        # implements U'*U = (n+kappa)*P. Returns lower triangular matrix.
        # Take transpose so we can access with U[i]
        U = self.sqrt((n + self.kappa) * P)

        sigmas[0] = x
        for k in range(n):
            # pylint: disable=bad-whitespace
            sigmas[k+1]   = self.subtract(x, -U[k])
            sigmas[n+k+1] = self.subtract(x, U[k])
        return sigmas


    def _compute_weights(self):
        """ Computes the weights for the unscented Kalman filter. In this
        formulation the weights for the mean and covariance are the same.
        """

        n = self.n
        k = self.kappa

        self.Wm = np.full(2*n+1, .5 / (n + k))
        self.Wm[0] = k / (n+k)
        self.Wc = self.Wm


    def __repr__(self):

        return '\n'.join([
            'JulierSigmaPoints object',
            pretty_str('n', self.n),
            pretty_str('kappa', self.kappa),
            pretty_str('Wm', self.Wm),
            pretty_str('Wc', self.Wc),
            pretty_str('subtract', self.subtract),
            pretty_str('sqrt', self.sqrt)
            ])


class SimplexSigmaPoints(object):

    """
    Generates sigma points and weights according to the simplex
    method presented in [1].

    Parameters
    ----------

    n : int
        Dimensionality of the state. n+1 weights will be generated.

    sqrt_method : function(ndarray), default=scipy.linalg.cholesky
        Defines how we compute the square root of a matrix, which has
        no unique answer. Cholesky is the default choice due to its
        speed. Typically your alternative choice will be
        scipy.linalg.sqrtm

        If your method returns a triangular matrix it must be upper
        triangular. Do not use numpy.linalg.cholesky - for historical
        reasons it returns a lower triangular matrix. The SciPy version
        does the right thing.

    subtract : callable (x, y), optional
        Function that computes the difference between x and y.
        You will have to supply this if your state variable cannot support
        subtraction, such as angles (359-1 degreees is 2, not 358). x and y
        are state vectors, not scalars.

    Attributes
    ----------

    Wm : np.array
        weight for each sigma point for the mean

    Wc : np.array
        weight for each sigma point for the covariance

    References
    ----------

    .. [1] Phillippe Moireau and Dominique Chapelle "Reduced-Order
           Unscented Kalman Filtering with Application to Parameter
           Identification in Large-Dimensional Systems"
           DOI: 10.1051/cocv/2010006
    """

    def __init__(self, n, alpha=1, sqrt_method=None, subtract=None):
        self.n = n
        self.alpha = alpha
        if sqrt_method is None:
            self.sqrt = cholesky
        else:
            self.sqrt = sqrt_method

        if subtract is None:
            self.subtract = np.subtract
        else:
            self.subtract = subtract

        self._compute_weights()


    def num_sigmas(self):
        """ Number of sigma points for each variable in the state x"""
        return self.n + 1


    def sigma_points(self, x, P):
        """
        Computes the implex sigma points for an unscented Kalman filter
        given the mean (x) and covariance(P) of the filter.
        Returns tuple of the sigma points and weights.

        Works with both scalar and array inputs:
        sigma_points (5, 9, 2) # mean 5, covariance 9
        sigma_points ([5, 2], 9*eye(2), 2) # means 5 and 2, covariance 9I

        Parameters
        ----------

        x : An array-like object of the means of length n
            Can be a scalar if 1D.
            examples: 1, [1,2], np.array([1,2])

        P : scalar, or np.array
           Covariance of the filter. If scalar, is treated as eye(n)*P.

        Returns
        -------

        sigmas : np.array, of size (n, n+1)
            Two dimensional array of sigma points. Each column contains all of
            the sigmas for one dimension in the problem space.

            Ordered by Xi_0, Xi_{1..n}
        """

        if self.n != np.size(x):
            raise ValueError("expected size(x) {}, but size is {}".format(
                self.n, np.size(x)))

        n = self.n

        if np.isscalar(x):
            x = np.asarray([x])
        x = x.reshape(-1, 1)

        if np.isscalar(P):
            P = np.eye(n) * P
        else:
            P = np.atleast_2d(P)

        U = self.sqrt(P)

        lambda_ = n / (n + 1)
        Istar = np.array([[-1/np.sqrt(2*lambda_), 1/np.sqrt(2*lambda_)]])

        for d in range(2, n+1):
            row = np.ones((1, Istar.shape[1] + 1)) * 1. / np.sqrt(lambda_*d*(d + 1)) # pylint: disable=unsubscriptable-object
            row[0, -1] = -d / np.sqrt(lambda_ * d * (d + 1))
            Istar = np.r_[np.c_[Istar, np.zeros((Istar.shape[0]))], row] # pylint: disable=unsubscriptable-object

        I = np.sqrt(n)*Istar
        scaled_unitary = (U.T).dot(I)

        sigmas = self.subtract(x, -scaled_unitary)
        return sigmas.T


    def _compute_weights(self):
        """ Computes the weights for the scaled unscented Kalman filter. """

        n = self.n
        c = 1. / (n + 1)
        self.Wm = np.full(n + 1, c)
        self.Wc = self.Wm


    def __repr__(self):
        return '\n'.join([
            'SimplexSigmaPoints object',
            pretty_str('n', self.n),
            pretty_str('alpha', self.alpha),
            pretty_str('Wm', self.Wm),
            pretty_str('Wc', self.Wc),
            pretty_str('subtract', self.subtract),
            pretty_str('sqrt', self.sqrt)
            ])

class GeneralizedSigmaPoints(object):
    '''
    Generates sigma points and weights according to the generalized unscented
    transformation method presented in [1]. It utilizes the first four 
    statistical moments to generate the sigma points and their weights for 
    most of probability distributions.
    
    
    Parameters
    ----------

    n : int
        Dimensionality of the state. n+1 weights will be generated.
    P : scalar, or np.array
        Covariance of the filter. If scalar, is treated as eye(n)*P.
    S : scalar, or np.array
        third central moment, skewness
    K : scalar, or np.array
        fourth central moment, kurtosis
    positively_constrained : bool
        enable positively constrained sigma points. It recompute the weights 
        and scales parameters in order to avoid negative sigmas points. Useful
        for function that does not accept negative values, although it is only 
        only accurate up to third order.
        It redifines the scale parameter 's[i]' and consequently 's[i+n]' and
        weights.
    k : float
        slack parameter. Where value k=1 ensures that at least one of the 
        sigma points is zero. The sigma points gets futher away from zero as
        k->0.
    x : An array-like object of the means of length n
        used for sigmas points recalculation when 'positively_constrained' is 
        True. 
        
    References
    ----------
    
    .. [1] Donald Ebeigbe et al. "Generalized Unscented Transformation for 
           Probability Distributions"
           arXiv:2104.01958v1 [stat.ME]
    '''
    def __init__(self, n, P, S, K, positively_constrained=False, k=None, x=None):
        self.n = n
        # NOTE: add dimention verification
        
        if x is not None:
            if np.isscalar(x):
                x = np.asarray([x])
            # x = x.reshape(-1, 1)

        if np.isscalar(P):
            P = np.eye(n) * P
        else:
            P = np.atleast_2d(P)
        
        if np.isscalar(S):
            S = np.asarray([S])
        
        if np.isscalar(K):
            K = np.asarray([K])
        
        self.x, self.P, self.S, self.K = x, P, S, K
        
        self.k = k
        self.positively_constrained = positively_constrained
        
        self.s = np.zeros(2*self.n+1)
        
        self._compute_weights()
        if positively_constrained:
            self.sigma_points(x, P)
        
    def num_sigmas(self):
        """ Number of sigma points for each variable in the state x"""
        return 2*self.n + 1
    
    def sigma_points(self, x, P):
        """
        Computes the implex sigma points for an unscented Kalman filter
        given the mean (x) and covariance(P) of the filter.
        Returns tuple of the sigma points and weights.

        Works with both scalar and array inputs:
        sigma_points (5, 9, 2) # mean 5, covariance 9
        sigma_points ([5, 2], 9*eye(2), 2) # means 5 and 2, covariance 9I

        Parameters
        ----------

        x : An array-like object of the means of length n
            Can be a scalar if 1D.
            examples: 1, [1,2], np.array([1,2])

        P : scalar, or np.array
           Covariance of the filter. If scalar, is treated as eye(n)*P.

        Returns
        -------

        sigmas : np.array, of size (n, n+1)
            Two dimensional array of sigma points. Each column contains all of
            the sigmas for one dimension in the problem space.

            Ordered by Xi_0, Xi_{1..n}
        """
              
        if self.n != np.size(x):
            raise ValueError("expected size(x) {}, but size is {}".format(
                self.n, np.size(x)))

        n = self.n

        if np.isscalar(x):
            x = np.asarray([x])
        # x = x.reshape(-1, 1)

        if np.isscalar(P):
            P = np.eye(n) * P
        else:
            P = np.atleast_2d(P)
        
        if x != self.x:
            raise Warning(f"input x is different from previous data. \n-initial: {self.x} \n-input  : {x}")
        if x != self.x:
            raise Warning(f"input P is different from previous data. \n-initial: {self.P} \n-input  : {P}")
            
        sigmas = np.zeros((2*n+1, n))
        for i in range(1, self.n+1):
            i_=i-1
            sigmas[0]   = x
            sigmas[i]   = x - self.s[i  ]*np.sqrt(P[:, i_])
            sigmas[i+n] = x + self.s[i+n]*np.sqrt(P[:, i_])
        
        if self.positively_constrained:
            self._redefine_scale_param(sigmas)
            self._compute_weights(compute_free_parameter=False)
            
            for i in range(1, self.n+1):
                i_=i-1
                sigmas[0]   = x
                sigmas[i]   = x - self.s[i  ]*np.sqrt(P[:, i_])
                sigmas[i+n] = x + self.s[i+n]*np.sqrt(P[:, i_])
        
        return sigmas
    
    def _compute_weights(self, compute_free_parameter=True):
        """ 
        Computes the weights and scale parameters for the scaled unscented 
        Kalman filter. 
        
        Parameters
        ----------
        
        compute_free_parameter : bool
            compute the free parameter s[i] for partially match kurtosis
        """
        
        n = self.n
        
        std = np.sqrt(np.diag(self.P))
            
        # standarized values        
        S_ = self.S/std**3.0
        K_ = self.K/std**4.0
        
        w = np.zeros(2*n+1)
        for i in range(1, self.n+1):
            i_ = i - 1
            # free parameter
            if compute_free_parameter:
                self.s[i] = 0.5*(-S_[i_] + np.sqrt(4*K_[i_] - 3*S_[i_]**2.0))
            
            # weights
            self.s[i+n] = self.s[i] + S_[i_]
            w[i+n] = 1.0/(self.s[i+n]*(self.s[i] + self.s[i+n]))
            w[i] = self.s[i+n]/self.s[i]*w[i+n]
        w[0] = 1 - np.sum(w)
        
        self.Wm = w
        self.Wc = w
        
    
    def _redefine_scale_param(self, sigmas):
        """
        Evaluate and redifine all negative sigma points

        Parameters
        ----------
        sigmas : np.array
            sigma points.

        """
        for i in range(len(sigmas)):
            i_=i-1
            if np.min(sigmas[i]) < 0:
                self.s[i] = self.k*np.min(self.x/np.sqrt(self.P)[:, i_])
        
    def __repr__(self):
        return '\n'.join([
            'GeneralizedSigmaPoints object',
            pretty_str('n', self.n),
            pretty_str('x', self.x),
            pretty_str('P', self.P),
            pretty_str('S', self.S),
            pretty_str('K', self.K),
            pretty_str('s', self.s),
            pretty_str('Positively constrained', self.positively_constrained),
            pretty_str('k', self.k),
            pretty_str('Wm', self.Wm),
            pretty_str('Wc', self.Wc),
            
            ])