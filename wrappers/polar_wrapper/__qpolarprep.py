import numpy as np
from . import __tools as tls
from . import __polarcodec as codec

# ###################################################################
# q1prep:  this function implements the error detection mechanism  
# used within the measurement-based preparation of Q1 code states
# % input arguments
#      n: number of polarization steps. (polar code length N=2^n)
#   zpos: last position frozen in Z basis. must be between 0 and N-1
#   meas: measurement outcomes. np array, which must be either a row
#       : vector (1D) or a matrix. in both cases, the number of elements
#       : must be equal to either (N/2)*n or (N/2)*(n-t_XX), where t_XX
#       : is the time index of the first XX measurement (0 <= t_XX < n),
#       : since leading ZZ measurements (if any) may be skipped.
#       : measurement results are ordered from the left-most time step
#       : (t=0 or t=t_XX), to the right-most one (t=n-1). at each time  
#       : step, the corresponding results are ordered from the top-most 
#       : measurement to the bottom-most measurement.
#       : if 'meas' is a matrix, each row corresponds to the measurement
#       : results at a given time step. hence, it must be of size either
#       : n x (N/2) or (n-t_XX) x (N/2), the later occuring in case that 
#       : the leading ZZ measurements (if any) have been skipped.
#
# the function returns 1 if successful preparation, 0 if not.
# ###################################################################
def q1prep(n, zpos, meas):
	
	N = 2**n          # polar code length
  
	xorz = bin(zpos)  # it tells Pauli XX (xorz=0) or ZZ measurement (xorz=1)
	xorz = xorz[2:]   # discard leading "0b" string 
	if len(xorz) < n: # must be of length n
		xorz = "0"*(n-len(xorz)) + xorz  # add leading zeros
	xorz = xorz[::-1] # reverse -- starts with the lsb
	
	# determine t_XX: time index of first XX measurement
	t_XX = n  # no XX measurements        
	for i in range (0, n):
		if xorz[i] == "0": # XX measurement
			t_XX = i
			break
	
	# check the format of input 'meas' argument (see description above of input arguments)
	if meas.ndim == 1:
		# row vector: check that it contains the correct number of elements
		if meas.size != (N//2)*n and meas.size != (N//2)*(n-t_XX):
			raise TypeError("Incorrect number of entries in input argument 'meas'")
		
	elif meas.ndim == 2:
		# matrix: check that is has the correct numner of columns, equal to N/2
		if np.size(meas, 1) != N//2:
			raise TypeError("Incorrect number of columns in input argument 'meas'")
		
		# check that is has the correct numner of rows, equal to either n or (n-t_XX)
		if np.size(meas, 0) != n and np.size(meas, 0) != (n-t_XX):
			raise TypeError("Incorrect number of rows in input argument 'meas'")
		
		# reshape => matrix to row vector
		meas = meas.reshape(meas.size)

	else:
		raise TypeError("Incorrect argument 'meas' -- must be either a row vector or a matrix")
	
	if t_XX > 0 and meas.size == (N//2)*(n-t_XX):
		# insert leading zeros -- for leading ZZ measurements that have been skipped
		meas = np.insert(meas, 0, np.repeat(0, (N//2)*t_XX))
			
	# success: returned value -- init as true (1)
	success = 1
	
	# qstate_UV__  stores the [U, V] vectors ([Z, X]-basis freezing) of the qpolar states 
	# qstate_UV__ = [U1, V1, U2, V2, ..., Uk, Vk], where k is the number of qstates at the current reccursion level
	# qstate_Ulen = len(U1) = len(U2) = ... = len(Uk) = length of U vectors at current reccursion level
	# qstate_UV__ and qstate_Ulen are updated at each level of reccursion
	# initialization: U1 = ... = UN = [0] and V1 = ... = VN = [], corresponding to all qubits initialized in Z basis
	qstate_UV__ = np.zeros(N, dtype=int)  
	
	t = 0  # time index: indicates which recursion level we are at, and tells when to stop 
	qstate_Ulen = 1  # length of vector U -- of the qstates at the reccursion level t=0 
	meas_indx   = 0  # current index in 'meas' array 
	
	while 0 <= t < n :
		
		# at time t, there are 2**(n-t) qpolar states already prepared, each one of length 2**t
		# we prepare a qstate of length 2**(t+1) from two qstates of length 2**t
		# in total, 2**(n-t-1) qpolar states of length 2**(t+1) will be prepared
		T = 2**t
		
		# measurement outcomes
		m__ = np.zeros((T,), dtype=int)
	
		if xorz[t] == "1": # we do ZZ measurements
		
			for i in range (0, 2**(n-t-1)): 
				# qstate_freeze indexes corresponding to starting positions of the two qpolar states 
				indx1 = 2*i*T       # starting index of the first qstate
				indx2 = (2*i+1)*T   # starting index of the second qstate
				
				# U and V vectors or the two qpolar states that are grouped together 
				U1 = qstate_UV__[indx1:indx1+qstate_Ulen]    # U vector of the first block
				V1 = qstate_UV__[indx1+qstate_Ulen:indx2]    # V vector of the first block
				U2 = qstate_UV__[indx2:indx2+qstate_Ulen]    # U vector of the second block
				V2 = qstate_UV__[indx2+qstate_Ulen:indx2+T]  # V vector of the second block

				Uprime = (U1 + U2)%2  # Uprime = U1 + U2 mod 2 
				Vprime = (V1 + V2)%2  # Vprime = V1 + V2 mod 2
				
				# compute the syndrome of the corresponding measurement outcomes
				m__[:] = meas[meas_indx:meas_indx+T]  # measurement results
				meas_indx = meas_indx+T            # update meas_index value
				codec.polarenc(m__)      # apply the polar encoder (m__ is modified in place!)
				
				if (m__[0:qstate_Ulen] == Uprime).all():  # syndrome is all-zero
					# update [U, V] vectors of the prepared state
					# Unew = [Uprime, Xguess, U2], where Xguess = m__[qstate_Ulen:T], Vnew = Vprime
					qstate_UV__[indx1:indx1+qstate_Ulen]   = Uprime[:]           # Uprime 
					qstate_UV__[indx1+qstate_Ulen:indx2]   = m__[qstate_Ulen:T]  # Xguess
					# qstate_UV__[indx2:indx2+qstate_Ulen] = U2[:]               # U2 -- not needed 
					qstate_UV__[indx2+qstate_Ulen:indx2+T] = Vprime[:]           # Vprime
					
					# qstate_Ulen will be updated after the for loop is completed
					# i.e., after preparing all the 2**(n-t-1) qpolar states of length 2**(t+1) 
		  
				else: # non-zero syndrome => discard
					success = 0
					break # break from the "for i in range (0, 2**(n-t-1))" loop

			if success == 0:
				break # breaking from the "while 0 <= t < n" loop 
			else:
				# update qstate_Ulen value 
				qstate_Ulen = T + qstate_Ulen
				t = t + 1


		else: # xorz[t] == "0": we do XX measurements 
		
			for i in range (0, 2**(n-t-1)): 
				# qstate_freeze indexes corresponding to starting positions of the two qpolar states 
				indx1 = 2*i*T       # starting index of the first qstate
				indx2 = (2*i+1)*T   # starting index of the second qstate
				
				# U and V vectors or the two qpolar states that are grouped together 
				U1 = qstate_UV__[indx1:indx1+qstate_Ulen]    # U vector of the first block
				V1 = qstate_UV__[indx1+qstate_Ulen:indx2]    # V vector of the first block
				U2 = qstate_UV__[indx2:indx2+qstate_Ulen]    # U vector of the second block
				V2 = qstate_UV__[indx2+qstate_Ulen:indx2+T]  # V vector of the second block

				Uprime = (U1 + U2)%2  # Uprime = U1 + U2 mod 2 
				Vprime = (V1 + V2)%2  # Vprime = V1 + V2 mod 2
        
				# compute the syndrome of the corresponding measurement outcomes
				m__[:] = meas[meas_indx:meas_indx+T]  # measurement results
				meas_indx = meas_indx+T            # update meas_index value
				codec.revpolarenc(m__)   # reverse polar encoder (m__ is modified in place!)
				
				if (m__[qstate_Ulen:T] == Vprime).all():  # syndrome is all-zero
					# update [U, V] vectors of the prepared state
					# Unew = Uprime, Vnew = [V1, Zguess, Vprime], where Zguess = m__[0:qstate_Ulen]
					qstate_UV__[indx1:indx1+qstate_Ulen]   = Uprime[:]           # Uprime 
					# qstate_UV__[indx1+qstate_Ulen:indx2] = V1[:]               # V1 -- not needed
					qstate_UV__[indx2:indx2+qstate_Ulen]   = m__[0:qstate_Ulen]  # Zguess
					qstate_UV__[indx2+qstate_Ulen:indx2+T] = Vprime[:]           # Vprime
					
					# qstate_Ulen needs not be updated (remains unchanged)
	
				else: # non-zero syndrome => discard
					success = 0
					break # break from the "for i in range (0, 2**(n-t-1))" loop
					
			if success == 0:
				break # breaking from the "while 0 <= t < n" loop 
			else:
				# qstate_Ulen needs not be updated (remains unchanged)
				t = t + 1

	return success 

